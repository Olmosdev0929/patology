import { useEffect, useState } from "react";
import { Plus, Sparkles, X } from "lucide-react";
import { api } from "../lib/api";
import { useI18n } from "../lib/i18n";
import { Badge, Button, Input, InventoryTags, Spinner, cx } from "./ui";

export const ROUTINE = {
  breast: ["ER", "PR", "HER2", "Ki-67", "CK5/6"],
  lung: ["TTF-1", "Napsin A", "p40", "CK7"],
  colon: ["CK20", "CDX2", "CK7"],
  stomach: ["CD117", "Ki-67"],
  liver: ["CK7", "CK20"],
  kidney: ["PAX8", "CK7"],
  prostate: ["NKX3.1", "p63"],
  thyroid: ["TTF-1", "PAX8"],
  skin: ["S100", "SOX10", "HMB45"],
  lymph: ["CD20", "CD3", "CD30", "Ki-67"],
  cervix: ["p40", "Ki-67"],
  other: ["CK7", "CK20"],
};

const SOURCE_COLOR = { routine: "slate", tandem: "purple", custom: "amber" };

/** Live Smart Tandem suggestions for the current panel. */
export function TandemPanel({ markers, organ, onAdd, disabled }) {
  const { t, L } = useI18n();
  const [items, setItems] = useState(null);
  const names = markers.map((m) => m.name).join("|");

  useEffect(() => {
    if (!names) return setItems([]);
    let alive = true;
    setItems(null);
    api("/tandem/suggest", { method: "POST", body: { markers: names.split("|"), organ } })
      .then((x) => alive && setItems(x))
      .catch(() => alive && setItems([]));
    return () => { alive = false; };
  }, [names, organ]);

  return (
    <div className="rounded-2xl border border-purple-200 bg-purple-50/60 p-4 dark:border-purple-500/30 dark:bg-purple-500/5">
      <div className="mb-1 flex items-center gap-2 text-sm font-bold text-purple-700 dark:text-purple-300">
        <Sparkles className="size-4" />{t("cases.tandem")}
      </div>
      <p className="mb-3 text-xs text-muted">{t("cases.tandemHint")}</p>
      {items === null ? <Spinner /> : items.length === 0 ? (
        <p className="text-xs text-muted">{t("cases.noTandem")}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((s) => (
            <li key={s.name} className="rounded-xl border border-line bg-surface p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono font-bold">{s.name}</span>
                {s.clone && <span className="font-mono text-xs text-muted">({s.clone})</span>}
                <InventoryTags tags={s.tags.filter((x) => x === "expiring" || x === "slow")} />
                <span className="ml-auto font-mono text-xs text-muted">
                  {t("inv.tests", { n: s.stock })}{s.days_to_expiry != null && ` · ${s.days_to_expiry} ${t("common.days")}`}
                </span>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed">{L(s.reason)}</p>
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-[11px] text-muted">← {s.triggers.join(", ")}</span>
                {onAdd && (
                  <Button variant="smart" className="min-h-9 px-3 text-xs" disabled={disabled} onClick={() => onAdd(s.name, "tandem")}>
                    <Plus className="size-3.5" />{t("cases.add")}
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Selected markers + inventory search + free-text custom marker. */
export default function MarkerPicker({ markers, onAdd, onRemove, disabled, organ }) {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [options, setOptions] = useState([]);

  useEffect(() => {
    if (!q.trim()) return setOptions([]);
    const ctrl = new AbortController();
    const id = setTimeout(() => {
      api(`/inventory?q=${encodeURIComponent(q.trim())}`, { signal: ctrl.signal }).then((x) => setOptions(x.slice(0, 8))).catch(() => {});
    }, 200);
    return () => { clearTimeout(id); ctrl.abort(); };
  }, [q]);

  const chosen = new Set(markers.map((m) => m.name.toLowerCase()));
  const exact = options.some((o) => o.name.toLowerCase() === q.trim().toLowerCase());
  const add = (name, source) => { onAdd(name, source); setQ(""); };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {markers.length === 0 && <span className="text-sm text-muted">{t("cases.noMarkers")}</span>}
        {markers.map((m) => (
          <span key={m.name} className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 py-1 pl-3 pr-1 text-sm">
            <span className="font-mono font-semibold">{m.name}</span>
            <Badge color={SOURCE_COLOR[m.source]} className="text-[10px]">{t(`cases.source.${m.source}`)}</Badge>
            {!disabled && (
              <button onClick={() => onRemove(m.name)} className="rounded-lg p-1 text-muted hover:bg-line hover:text-rose-600" aria-label={t("cases.remove")}>
                <X className="size-3.5" />
              </button>
            )}
          </span>
        ))}
      </div>

      {organ && !disabled && (
        <div className="flex flex-wrap gap-1.5">
          {(ROUTINE[organ] || ROUTINE.other).filter((n) => !chosen.has(n.toLowerCase())).map((n) => (
            <button key={n} onClick={() => add(n, "routine")} className="min-h-9 rounded-lg border border-dashed border-line px-2.5 font-mono text-xs font-semibold text-muted hover:border-primary hover:text-primary-ink">
              + {n}
            </button>
          ))}
        </div>
      )}

      {!disabled && (
        <div className="relative">
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("cases.addPh")} />
          {q.trim() && (
            <div className="absolute inset-x-0 top-full z-20 mt-1 overflow-hidden rounded-xl border border-line bg-surface shadow-xl">
              {options.filter((o) => !chosen.has(o.name.toLowerCase())).map((o) => (
                <button key={o.id} onClick={() => add(o.name, "routine")} className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm hover:bg-surface-2">
                  <span className="font-mono font-semibold">{o.name}</span>
                  <span className="text-xs text-muted">{o.clone}</span>
                  <span className={cx("ml-auto font-mono text-xs", o.stock > 0 ? "text-muted" : "text-rose-600")}>{o.stock}</span>
                </button>
              ))}
              {!exact && (
                <button onClick={() => add(q.trim(), "custom")} className="flex w-full items-center gap-2 border-t border-line px-3 py-2.5 text-left text-sm font-medium text-amber-700 hover:bg-surface-2 dark:text-amber-300">
                  <Plus className="size-4" />{t("cases.newCustom", { name: q.trim() })}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
