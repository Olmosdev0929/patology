/** Telegram WebApp SDK helpers (all no-ops in a normal browser). */
export const tg = window.Telegram?.WebApp?.initData ? window.Telegram.WebApp : null;

export function initTelegram() {
  if (!tg) return;
  tg.ready();
  tg.expand();
}

export function haptic(kind = "light") {
  try {
    if (kind === "success" || kind === "error" || kind === "warning") tg?.HapticFeedback?.notificationOccurred(kind);
    else tg?.HapticFeedback?.impactOccurred(kind);
  } catch {}
}

export function confirmDialog(message) {
  if (tg?.showConfirm) return new Promise((resolve) => tg.showConfirm(message, resolve));
  return Promise.resolve(window.confirm(message));
}

export function openExternal(url) {
  if (tg) tg.openLink(url);
  else window.open(url, "_blank", "noopener");
}
