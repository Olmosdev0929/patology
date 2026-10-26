/**
 * Resumable chunked upload for large files (books of hundreds of MB).
 *
 * The file is sent in slices (File.slice never loads the whole file into memory). Each slice is
 * retried with backoff; if the page is closed, the upload id is remembered in localStorage and the
 * next attempt with the same file continues from the byte the server already has.
 */
import { ApiError, api, getToken } from "./api";

const KEY = "pathouz.uploads";

function fileKey(file) {
  return `${file.name}|${file.size}|${file.lastModified}`;
}

function remembered() {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}

function remember(file, id) {
  try {
    const all = remembered();
    if (id) all[fileKey(file)] = id; else delete all[fileKey(file)];
    localStorage.setItem(KEY, JSON.stringify(all));
  } catch {}
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function sha256Hex(blob) {
  if (!globalThis.crypto?.subtle) return null; // non-secure context: server skips the check
  const hash = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
  return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** PUT one slice with XMLHttpRequest so we get byte-level progress. */
function putChunk(url, blob, checksum, onProgress, signal) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", "application/octet-stream");
    const token = getToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    if (checksum) xhr.setRequestHeader("X-Chunk-SHA256", checksum);
    xhr.upload.onprogress = (e) => onProgress(e.loaded);
    xhr.onload = () => {
      let data = null;
      try { data = JSON.parse(xhr.responseText); } catch {}
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new ApiError(xhr.status, data?.detail ?? xhr.statusText));
    };
    const aborted = () => new DOMException("aborted", "AbortError");
    // xhr.abort() also fires onerror in some browsers: report it as a pause, not a network failure.
    xhr.onerror = () => reject(signal?.aborted ? aborted() : new ApiError(0, "network"));
    xhr.onabort = () => reject(aborted());
    xhr.ontimeout = () => reject(new ApiError(0, "timeout"));
    xhr.timeout = 5 * 60 * 1000;
    if (signal?.aborted) return reject(aborted());
    signal?.addEventListener("abort", () => xhr.abort(), { once: true });
    xhr.send(blob);
  });
}

/**
 * Upload `file`; returns the upload id once the server has every byte.
 * onProgress({sent, total, speed}) is called frequently. Abort with `signal` (the upload can be resumed later).
 */
export async function uploadFile(file, { onProgress = () => {}, signal } = {}) {
  let session = null;
  const knownId = remembered()[fileKey(file)];
  if (knownId) {
    try { session = await api(`/uploads/${knownId}`); } catch { remember(file, null); }
  }
  if (!session) {
    session = await api("/uploads", { method: "POST", body: { filename: file.name, size: file.size } });
    remember(file, session.id);
  }

  const chunkSize = Math.min(session.chunk_size, 8 * 1024 * 1024);
  let offset = session.received;
  const started = performance.now();
  const startOffset = offset;
  let failures = 0;

  while (offset < file.size) {
    if (signal?.aborted) throw new DOMException("aborted", "AbortError");
    const end = Math.min(file.size, offset + chunkSize);
    try {
      const slice = file.slice(offset, end);
      // Per-chunk checksum: the server rejects a chunk that arrived damaged instead of storing it.
      const checksum = await sha256Hex(slice);
      const res = await putChunk(`/api/uploads/${session.id}?offset=${offset}`, slice, checksum, (loaded) => {
        const sent = offset + loaded;
        const secs = (performance.now() - started) / 1000;
        onProgress({ sent, total: file.size, speed: secs > 0 ? (sent - startOffset) / secs : 0 });
      }, signal);
      offset = res.received;
      failures = 0;
    } catch (e) {
      if (e.name === "AbortError" || signal?.aborted) throw new DOMException("aborted", "AbortError");
      if (e.status === 409 && e.detail?.received != null) { offset = e.detail.received; continue; } // resync
      const retryable = !e.status || e.status >= 500 || [408, 422, 429].includes(e.status); // 422 = checksum
      if (!retryable) throw e;
      failures += 1;
      if (failures > 8) throw e;
      await sleep(Math.min(30000, 1000 * 2 ** failures));                                      // network blip
      if (signal?.aborted) throw new DOMException("aborted", "AbortError");
      try { offset = (await api(`/uploads/${session.id}`)).received; } catch {}
    }
  }
  onProgress({ sent: file.size, total: file.size, speed: 0 });
  return session.id;
}

export function forgetUpload(file) {
  remember(file, null);
}

export function formatBytes(n) {
  if (n == null) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1; }
  return `${n.toFixed(i >= 2 ? 1 : 0)} ${units[i]}`;
}
