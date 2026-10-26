/**
 * In-app PDF reader for large books. pdf.js fetches the file with HTTP Range requests, so only the
 * pages being viewed are downloaded — a 900-page, 400 MB book opens in seconds.
 * Loaded lazily (React.lazy) so pdf.js never weighs down the main bundle.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist/build/pdf.min.mjs";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { ChevronLeft, ChevronRight, Layers, Maximize2, Minus, Plus, Search } from "lucide-react";
import { api, getToken } from "../lib/api";
import { useI18n } from "../lib/i18n";
import { haptic } from "../lib/telegram";
import { useToast } from "./toast";
import { Badge, Button, Field, Input, Modal, Spinner, Textarea, cx } from "./ui";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export default function PdfReader({ book, onBack }) {
  const { t } = useI18n();
  const toast = useToast();
  const canvasRef = useRef(null);
  const boxRef = useRef(null);
  const renderTask = useRef(null);
  const [doc, setDoc] = useState(null);
  const [loadPct, setLoadPct] = useState(0);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(book.progress_page || 1);
  const [pageInput, setPageInput] = useState(String(book.progress_page || 1));
  const [scale, setScale] = useState(null); // null = fit width
  const [rendering, setRendering] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState(null);
  const [card, setCard] = useState(null);

  // Open the document (range-based, no full download)
  useEffect(() => {
    const task = pdfjs.getDocument({
      url: book.file_url,
      httpHeaders: { Authorization: `Bearer ${getToken()}` },
      rangeChunkSize: 1024 * 1024,
      disableAutoFetch: true,   // do not prefetch the rest of the book in the background
      disableStream: true,      // rely on Range requests only
    });
    task.onProgress = ({ loaded, total }) => total && setLoadPct(Math.round((loaded / total) * 100));
    task.promise.then(setDoc, (e) => setError(e?.message || String(e)));
    return () => { task.destroy(); };
  }, [book.file_url]);

  const render = useCallback(async () => {
    if (!doc || !canvasRef.current) return;
    renderTask.current?.cancel();
    setRendering(true);
    try {
      const p = await doc.getPage(page);
      const base = p.getViewport({ scale: 1 });
      const width = boxRef.current?.clientWidth || 600;
      const s = scale ?? width / base.width;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const vp = p.getViewport({ scale: s * dpr });
      const canvas = canvasRef.current;
      canvas.width = vp.width;
      canvas.height = vp.height;
      canvas.style.width = `${vp.width / dpr}px`;
      canvas.style.height = `${vp.height / dpr}px`;
      renderTask.current = p.render({ canvasContext: canvas.getContext("2d"), viewport: vp });
      await renderTask.current.promise;
    } catch (e) {
      if (e?.name !== "RenderingCancelledException") setError(e?.message || String(e));
    } finally {
      setRendering(false);
    }
  }, [doc, page, scale]);

  useEffect(() => { render(); }, [render]);
  useEffect(() => {
    const onResize = () => scale == null && render();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [render, scale]);

  // Remember the page (debounced) so the reader reopens where the user stopped
  useEffect(() => {
    setPageInput(String(page));
    const id = setTimeout(() => api(`/books/${book.id}/progress`, { method: "PUT", body: { page } }).catch(() => {}), 800);
    return () => clearTimeout(id);
  }, [page, book.id]);

  const total = doc?.numPages || book.pages || 0;
  const go = (n) => { if (total) setPage(Math.min(total, Math.max(1, n))); };

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      if (e.key === "ArrowRight") go(page + 1);
      if (e.key === "ArrowLeft") go(page - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const search = async (e) => {
    e.preventDefault();
    if (q.trim().length < 2) return;
    try { setHits(await api(`/books/${book.id}/search?q=${encodeURIComponent(q.trim())}`)); } catch (err) { toast(err.message, "error"); }
  };

  const saveCard = async (e) => {
    e.preventDefault();
    try {
      await api("/anki", { method: "POST", body: {
        deck: book.title.slice(0, 100), front_uz: card.front, front_ru: card.front,
        back_uz: `${card.back}\n— ${book.title}, ${page}`, back_ru: `${card.back}\n— ${book.title}, ${page}`,
      } });
      haptic("success");
      toast(t("academy.cardAdded"));
      setCard(null);
    } catch (err) {
      toast(err.message, "error");
    }
  };

  return (
    <div>
      <button onClick={onBack} className="mb-3 text-sm font-medium text-muted hover:text-fg">← {t("academy.backToBooks")}</button>
      <h1 className="text-xl font-extrabold leading-tight">{book.title}</h1>
      {book.author && <p className="text-sm text-muted">{book.author}</p>}

      <div className="mt-3 rounded-2xl border border-line bg-surface px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="ghost" className="min-h-9 px-2" onClick={() => go(page - 1)} disabled={page <= 1} aria-label="prev"><ChevronLeft className="size-5" /></Button>
          <form onSubmit={(e) => { e.preventDefault(); go(Number(pageInput) || 1); }} className="flex items-center gap-1 font-mono text-sm">
            <input value={pageInput} onChange={(e) => setPageInput(e.target.value.replace(/\D/g, ""))} inputMode="numeric"
              className="w-14 rounded-lg border border-line bg-surface px-2 py-1 text-center" aria-label={t("academy.page")} />
            <span className="text-muted">/ {total || "…"}</span>
          </form>
          <Button variant="ghost" className="min-h-9 px-2" onClick={() => go(page + 1)} disabled={!total || page >= total} aria-label="next"><ChevronRight className="size-5" /></Button>
          <div className="ml-auto flex items-center gap-1">
            <Button variant="ghost" className="min-h-9 px-2" onClick={() => setScale((s) => Math.max(0.5, (s ?? 1) - 0.25))} aria-label="zoom out"><Minus className="size-4" /></Button>
            <Button variant="ghost" className="min-h-9 px-2" onClick={() => setScale(null)} aria-label="fit"><Maximize2 className="size-4" /></Button>
            <Button variant="ghost" className="min-h-9 px-2" onClick={() => setScale((s) => Math.min(4, (s ?? 1) + 0.25))} aria-label="zoom in"><Plus className="size-4" /></Button>
            <Button variant={searchOpen ? "soft" : "ghost"} className="min-h-9 px-2" onClick={() => setSearchOpen((x) => !x)} aria-label={t("common.search")}><Search className="size-4" /></Button>
            <Button variant="smart" className="min-h-9 px-2.5 text-xs" onClick={() => setCard({ front: "", back: "" })}><Layers className="size-4" /><span className="hidden sm:inline">{t("academy.toCard")}</span></Button>
          </div>
        </div>
        {total > 0 && (
          <input type="range" min={1} max={total} value={page} onChange={(e) => setPage(Number(e.target.value))} className="mt-2 w-full accent-teal-600" aria-label={t("academy.page")} />
        )}
      </div>

      {searchOpen && (
        <div className="mt-3 rounded-2xl border border-line bg-surface p-3">
          {book.text_status !== "ready" && (
            <p className="mb-2 text-xs text-amber-700 dark:text-amber-300">
              {t(`academy.textStatus.${book.text_status}`, { done: book.text_pages_done, total: book.pages || "…" })}
            </p>
          )}
          <form onSubmit={search} className="flex gap-2">
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("academy.searchInBook")} />
            <Button type="submit">{t("common.search")}</Button>
          </form>
          {hits && (
            <ul className="mt-2 max-h-64 divide-y divide-line overflow-y-auto">
              {hits.length === 0 && <li className="py-2 text-sm text-muted">{t("search.none")}</li>}
              {hits.map((h) => (
                <li key={h.page}>
                  <button onClick={() => { go(h.page); setSearchOpen(false); }} className="w-full py-2 text-left text-sm hover:bg-surface-2">
                    <Badge color="teal" className="mr-2 font-mono">{h.page}</Badge>{h.snippet}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div ref={boxRef} className="mt-3 overflow-auto rounded-2xl border border-line bg-surface-2">
        {error ? (
          <p className="p-6 text-sm text-rose-600">{t("common.error")}: {error}</p>
        ) : !doc ? (
          <div className="flex flex-col items-center gap-2 p-10 text-sm text-muted"><Spinner />{loadPct ? `${loadPct}%` : t("common.loading")}</div>
        ) : (
          <div className="relative flex justify-center">
            <canvas ref={canvasRef} className={cx("block bg-white transition-opacity", rendering && "opacity-60")} />
          </div>
        )}
      </div>
      <p className="mt-2 text-center text-xs text-muted">{book.license && `${t("academy.license")}: ${book.license}`}</p>

      <Modal open={Boolean(card)} onClose={() => setCard(null)} title={`${t("academy.newCard")} · ${t("academy.page")} ${page}`}>
        {card && (
          <form onSubmit={saveCard} className="space-y-3">
            <Field label={t("academy.front")}><Textarea rows={2} required value={card.front} onChange={(e) => setCard({ ...card, front: e.target.value })} /></Field>
            <Field label={t("academy.backSide")}><Textarea rows={3} value={card.back} onChange={(e) => setCard({ ...card, back: e.target.value })} /></Field>
            <Button type="submit" className="w-full">{t("common.save")}</Button>
          </form>
        )}
      </Modal>
    </div>
  );
}
