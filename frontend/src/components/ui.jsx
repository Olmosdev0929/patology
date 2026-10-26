import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { fetchImageUrl } from "../lib/api";
import { useI18n } from "../lib/i18n";

export function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

export function Card({ className, children, interactive, ...props }) {
  return (
    <div
      className={cx(
        "rounded-2xl border border-line bg-surface p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition",
        interactive && "hover:border-primary/40 hover:shadow-md",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/** Soft pills (light) / translucent pills (dark). */
const TONE = {
  teal: "bg-primary-soft text-primary-ink border-primary/20",
  rose: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/15 dark:text-rose-300 dark:border-rose-500/30",
  purple: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-500/15 dark:text-purple-300 dark:border-purple-500/30",
  amber: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:border-amber-500/30",
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:border-emerald-500/30",
  sky: "bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-500/15 dark:text-sky-300 dark:border-sky-500/30",
  indigo: "bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:border-indigo-500/30",
  slate: "bg-surface-2 text-muted border-line",
};

export function Badge({ color = "slate", className, children }) {
  return (
    <span className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-md border px-2 py-0.5 text-xs font-semibold", TONE[color], className)}>
      {children}
    </span>
  );
}

/** Solid labels drawn over images (Makroskopik / Mikroskopik / IHC Marker). */
const KIND_SOLID = { macro: "bg-rose-500", micro: "bg-purple-500", ihc: "bg-amber-500" };
export function KindLabel({ kind }) {
  const { t } = useI18n();
  return <span className={cx("shrink-0 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-semibold text-white shadow", KIND_SOLID[kind] || "bg-slate-500")}>{t(`img.${kind}`)}</span>;
}
export function StainLabel({ children }) {
  return children ? <span className="whitespace-nowrap rounded-md bg-slate-800/85 px-2 py-0.5 text-xs font-medium text-white shadow">{children}</span> : null;
}

const TAG_COLOR = { expiring: "rose", slow: "purple", fast: "emerald", low_stock: "amber", out_of_stock: "rose" };

export function InventoryTags({ tags = [] }) {
  const { t } = useI18n();
  return tags.map((tag) => <Badge key={tag} color={TAG_COLOR[tag]}>{t(`tags.${tag}`)}</Badge>);
}

const STATUS_COLOR = { registered: "amber", approved: "indigo", reported: "emerald" };

export function StatusBadge({ status }) {
  const { t } = useI18n();
  return <Badge color={STATUS_COLOR[status]}>{t(`status.${status}`)}</Badge>;
}

const BTN = {
  primary: "bg-primary text-white hover:bg-primary-strong dark:text-slate-950",
  ink: "bg-ink text-ink-fg hover:opacity-90",
  smart: "bg-purple-600 text-white hover:bg-purple-500",
  ghost: "bg-surface-2 text-fg hover:bg-line",
  soft: "border border-primary/25 bg-primary-soft text-primary-ink hover:border-primary/50",
  danger: "bg-rose-600 text-white hover:bg-rose-500",
  outline: "border border-line bg-surface text-fg hover:border-primary/40",
};

export function Button({ variant = "primary", className, loading, children, disabled, ...props }) {
  return (
    <button
      className={cx(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-50",
        BTN[variant], className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Field({ label, children, className }) {
  return (
    <label className={cx("block", className)}>
      {label && <span className="mb-1 block text-xs font-semibold text-muted">{label}</span>}
      {children}
    </label>
  );
}

const INPUT = "w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-base text-fg placeholder:text-muted/70 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15 sm:text-sm";

export function Input(props) {
  return <input {...props} className={cx(INPUT, props.className)} />;
}

export function Textarea(props) {
  return <textarea rows={4} {...props} className={cx(INPUT, "resize-y", props.className)} />;
}

export function Select({ children, ...props }) {
  return <select {...props} className={cx(INPUT, props.className)}>{children}</select>;
}

export function Spinner({ className }) {
  return <Loader2 className={cx("size-5 animate-spin text-muted", className)} />;
}

export function Loading() {
  const { t } = useI18n();
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted">
      <Spinner /> {t("common.loading")}
    </div>
  );
}

export function Empty({ children, icon: Icon }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-line bg-surface px-4 py-10 text-center text-sm text-muted">
      {Icon && <Icon className="size-8 opacity-60" />}
      {children}
    </div>
  );
}

export function ErrorBox({ error, onRetry }) {
  const { t } = useI18n();
  return (
    <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
      {t("common.error")}: {String(error?.message || error)}
      {onRetry && <button className="ml-3 underline" onClick={onRetry}>{t("common.retry")}</button>}
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 backdrop-blur-sm sm:items-center sm:p-4" onClick={onClose}>
      <div
        className={cx("fade-in max-h-[92vh] w-full overflow-y-auto rounded-t-3xl border border-line bg-surface p-5 safe-bottom shadow-2xl sm:rounded-3xl", wide ? "sm:max-w-3xl" : "sm:max-w-lg")}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-lg font-bold">{title}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-muted hover:bg-surface-2 hover:text-fg" aria-label="close">
            <X className="size-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** Segmented control (IGX Ombor Qoldig'i / Aqlli Tandem / Sarf Statistikasi). */
export function Segmented({ tabs, value, onChange }) {
  return (
    <div className="scrollbar-none mb-4 flex gap-1 overflow-x-auto rounded-2xl bg-surface-2 p-1">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={cx(
            "flex min-h-10 min-w-fit flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-xl px-3 text-sm font-semibold transition",
            value === tab.value ? "bg-surface text-fg shadow-sm" : "text-muted hover:text-fg",
          )}
        >
          {tab.icon && <span aria-hidden>{tab.icon}</span>}
          {tab.label}
          {tab.count != null && <span className="font-mono text-xs text-muted">{tab.count}</span>}
        </button>
      ))}
    </div>
  );
}

/** Horizontal filter chips (Barchasi / Ko'krak bezi / ...). */
export function Chips({ items, value, onChange }) {
  return (
    <div className="scrollbar-none -mx-4 mb-4 flex gap-2 overflow-x-auto px-4 pb-1">
      {items.map((it) => (
        <button
          key={it.value}
          onClick={() => onChange(it.value)}
          className={cx(
            "flex min-h-10 shrink-0 items-center gap-2 rounded-xl border px-3.5 text-sm font-semibold transition",
            value === it.value ? "border-primary bg-primary text-white dark:text-slate-950" : "border-line bg-surface text-fg hover:border-primary/40",
          )}
        >
          {it.icon && <span aria-hidden>{it.icon}</span>}
          {it.label}
          {it.count != null && <span className={cx("font-mono text-xs", value === it.value ? "opacity-80" : "text-muted")}>{it.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function SectionTitle({ children, actions }) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <div className="text-sm font-semibold text-muted">{children}</div>
      {actions}
    </div>
  );
}

/** <img> for endpoints that need the Authorization header. */
export function AuthImage({ src, alt = "", className, ...props }) {
  const [url, setUrl] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let alive = true;
    let objectUrl;
    fetchImageUrl(src)
      .then((u) => { objectUrl = u; if (alive) setUrl(u); })
      .catch(() => alive && setFailed(true));
    return () => { alive = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [src]);
  if (failed) return <div className={cx("grid place-items-center bg-surface-2 text-xs text-muted", className)}>✕</div>;
  if (!url) return <div className={cx("animate-pulse bg-surface-2", className)} />;
  return <img src={url} alt={alt} className={className} {...props} />;
}

export function Toast({ message, kind = "success", onDone }) {
  useEffect(() => {
    if (!message) return;
    const id = setTimeout(onDone, 3500);
    return () => clearTimeout(id);
  }, [message, onDone]);
  if (!message) return null;
  const color = kind === "error" ? "bg-rose-600" : "bg-slate-900 dark:bg-slate-100 dark:text-slate-900";
  return (
    <div className={cx("fade-in fixed inset-x-4 bottom-24 z-[60] mx-auto max-w-md rounded-2xl px-4 py-3 text-sm font-medium text-white shadow-xl", color)}>
      {message}
    </div>
  );
}

export function useAsync(fn, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    fn().then(
      (data) => alive && setState({ data, error: null, loading: false }),
      (error) => alive && setState({ data: null, error, loading: false }),
    );
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return {
    ...state,
    reload: () => setTick((x) => x + 1),
    setData: (next) => setState((s) => ({ ...s, data: typeof next === "function" ? next(s.data) : next })),
  };
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-extrabold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/** Tabs with icons/counts rendered as the segmented control. */
export function Tabs({ tabs, value, onChange }) {
  return (
    <Segmented
      value={value}
      onChange={onChange}
      tabs={tabs.map((tab) => ({ ...tab, icon: tab.icon ? <tab.icon className="size-4" /> : null }))}
    />
  );
}
