"""PDF text extraction worker, run as a short-lived subprocess with a memory cap.

    python -m app.services.pdftext count   FILE
    python -m app.services.pdftext extract FILE START STOP     # JSON lines: {"page": n, "text": "..."}

Running out-of-process keeps the web server safe: a hostile or broken PDF can at most kill this
worker. The reader is given an open file handle (pypdf otherwise copies the whole file into RAM)
and each worker handles one window of pages, so memory stays flat even for 1000+ page books.
"""
import json
import sys


def _reader(f):
    from pypdf import PdfReader

    return PdfReader(f, strict=False)


def optimize_for_web(path: str) -> dict:
    """Append an incremental update that re-emits every page-tree object at the end of the file.

    pdf.js validates a document by walking the page tree to the last page. When page dicts are
    scattered between large image streams (very common), that walk touches every byte range and a
    400 MB book is downloaded in full before the first page shows. After this update, the newest
    copies of all page-tree objects sit together at the end, so the walk needs only the tail.
    The original bytes are untouched (a standard PDF incremental update); on any problem the file is
    truncated back to its original length.
    """
    from io import BytesIO

    from pypdf.generic import IndirectObject

    with open(path, "rb") as f:
        reader = _reader(f)
        trailer = reader.trailer
        if "/Encrypt" in trailer:
            return {"changed": False, "reason": "encrypted"}
        if "/PathoUzWeb" in trailer:
            return {"changed": False, "reason": "already optimized"}
        f.seek(0, 2)
        original_size = f.tell()
        f.seek(max(0, original_size - 4096))
        tail = f.read()
        idx = tail.rfind(b"startxref")
        if idx < 0:
            return {"changed": False, "reason": "no startxref"}
        prev = int(tail[idx + 9:].split()[0])

        # Collect every node of the page tree (intermediate /Pages and leaf /Page dicts).
        refs, stack, seen = [], [trailer["/Root"].get_object().raw_get("/Pages")], set()
        while stack:
            ref = stack.pop()
            if not isinstance(ref, IndirectObject) or (ref.idnum, ref.generation) in seen:
                continue
            seen.add((ref.idnum, ref.generation))
            node = ref.get_object()
            refs.append((ref.idnum, ref.generation, node))
            kids = node.raw_get("/Kids") if "/Kids" in node else None
            if isinstance(kids, IndirectObject):
                kids = kids.get_object()
            if kids:
                stack.extend(reversed(list(kids)))
        if len(refs) < 50:
            return {"changed": False, "reason": "small"}

        body, offsets = BytesIO(), {}
        body.write(b"\n")
        for num, gen, node in refs:
            offsets[num] = (original_size + body.tell(), gen)
            body.write(f"{num} {gen} obj\n".encode())
            node.write_to_stream(body)
            body.write(b"\nendobj\n")

    xref_at = original_size + body.tell()
    body.write(b"xref\n0 1\n0000000000 65535 f \n")  # conventional free-list head
    nums = sorted(offsets)
    run = [nums[0]]
    for n in nums[1:] + [None]:
        if n is not None and n == run[-1] + 1:
            run.append(n)
            continue
        body.write(f"{run[0]} {len(run)}\n".encode())
        for m in run:
            off, gen = offsets[m]
            body.write(f"{off:010d} {gen:05d} n \n".encode())
        if n is not None:
            run = [n]
    extra = "".join(
        f" {key} {trailer.raw_get(key).idnum} {trailer.raw_get(key).generation} R"
        for key in ("/Root", "/Info") if key in trailer and isinstance(trailer.raw_get(key), IndirectObject)
    )
    ids = ""
    if "/ID" in trailer:
        buf = BytesIO()
        trailer["/ID"].write_to_stream(buf)
        ids = " /ID " + buf.getvalue().decode("latin-1")
    size = max(int(trailer["/Size"]), max(nums) + 1)
    body.write(f"trailer\n<< /Size {size}{extra}{ids} /Prev {prev} /PathoUzWeb true >>\nstartxref\n{xref_at}\n%%EOF\n".encode("latin-1"))

    pages_before = len(_reader(open(path, "rb")).pages)
    with open(path, "ab") as out:
        out.write(body.getvalue())
    try:
        with open(path, "rb") as f:
            if len(_reader(f).pages) != pages_before:
                raise ValueError("page count changed")
    except Exception:
        with open(path, "r+b") as out:
            out.truncate(original_size)
        return {"changed": False, "reason": "verification failed"}
    return {"changed": True, "objects": len(refs), "size": original_size + len(body.getvalue())}


def main(argv: list[str]) -> int:
    cmd, path = argv[0], argv[1]
    if cmd == "optimize":
        try:
            print(json.dumps(optimize_for_web(path)))
        except Exception as e:  # never fail the pipeline because of the optimisation step
            print(json.dumps({"changed": False, "reason": f"error: {e}"[:200]}))
        return 0
    with open(path, "rb") as f:
        reader = _reader(f)
        if cmd == "count":
            print(len(reader.pages))
            return 0
        start, stop = int(argv[2]), int(argv[3])
        out = sys.stdout
        for i in range(start, min(stop, len(reader.pages))):
            try:
                text = reader.pages[i].extract_text() or ""
            except Exception:  # one broken page must not lose the rest of the window
                text = ""
            out.write(json.dumps({"page": i + 1, "text": text.replace("\x00", " ").strip()}, ensure_ascii=False) + "\n")
        out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
