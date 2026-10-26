/** Thin fetch wrapper that attaches the session token and normalises errors. */

let token = null;
try { token = sessionStorage.getItem("pathouz.token"); } catch {}

export function setToken(value) {
  token = value;
  try {
    if (value) sessionStorage.setItem("pathouz.token", value);
    else sessionStorage.removeItem("pathouz.token");
  } catch {}
}

export function getToken() {
  return token;
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : detail?.error || `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export async function api(path, { method = "GET", body, form, signal } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(`/api${path}`, { method, headers, body: payload, signal });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401) onUnauthorized();
    throw new ApiError(res.status, data?.detail ?? res.statusText);
  }
  return data;
}

/** Fetch an authenticated image and return an object URL (img tags cannot send headers). */
export async function fetchImageUrl(url) {
  const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  return URL.createObjectURL(await res.blob());
}
