import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { BadgeCheck, FlaskConical, PackagePlus, Plus, ShieldAlert } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import { ROUTINE, TandemPanel } from "../components/MarkerPicker";
import { useToast } from "../components/toast";
import { Badge, Button, Card, Chips, Empty, ErrorBox, Field, Input, InventoryTags, Loading, Modal, Segmented, Select, Spinner, cx, useAsync } from "../components/ui";

const TONE = {
  expiring: { pill: "rose", bar: "bg-rose-500", num: "text-rose-600 dark:text-rose-300" },
  out_of_stock: { pill: "rose", bar: "bg-rose-500", num: "text-rose-600 dark:text-rose-300" },
  low_stock: { pill: "amber", bar: "bg-amber-500", num: "text-amber-600 dark:text-amber-300" },
  slow: { pill: "purple", bar: "bg-purple-500", num: "text-purple-700 dark:text-purple-300" },
  fast: { pill: "emerald", bar: "bg-emerald-500", num: "text-primary-ink" },
  none: { pill: "slate", bar: "bg-primary", num: "text-primary-ink" },
};
const PRIORITY = ["expiring", "out_of_stock", "low_stock", "slow", "fast"];
const mainTag = (tags) => PRIORITY.find((p) => tags.includes(p)) || "none";

function useLocalization() {
  const { t } = useI18n();
  return (loc) => (loc || "").split("/").map((x) => (t(`inv.loc.${x}`).startsWith("inv.") ? x : t(`inv.loc.${x}`))).join(" / ");
}

// ---------------------------------------------------------------- modals

function ReceiveModal({ open, onClose, markers, initialMarker, initialQty = 25, onDone }) {
  const { t } = useI18n();
  const toast = useToast();
  const [markerId, setMarkerId] = useState(initialMarker || "");
  const [newName, setNewName] = useState("");
  const [lot, setLot] = useState({ lot_number: "", expiry_date: "", quantity: initialQty });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      let id = markerId;
      if (!id && newName.trim()) id = (await api("/inventory", { method: "POST", body: { name: newName.trim() } })).id;
      if (!id) throw new Error(t("inv.chooseMarker"));
      onDone(await api(`/inventory/${id}/lots`, { method: "POST", body: { ...lot, quantity: Number(lot.quantity) } }));
      toast(t("common.saved"));
      onClose();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={t("inv.receive")}>
      <form onSubmit={submit} className="space-y-3">
        <Field label={t("inv.chooseMarker")}>
          <Select value={markerId} onChange={(e) => setMarkerId(e.target.value)}>
            <option value="">—</option>
            {markers.map((m) => <option key={m.id} value={m.id}>{m.name}{m.clone ? ` (${m.clone})` : ""}</option>)}
          </Select>
        </Field>
        {!markerId && <Field label={t("inv.newName")}><Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="TRPS1" /></Field>}
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("inv.lot")} className="col-span-2"><Input required value={lot.lot_number} onChange={(e) => setLot({ ...lot, lot_number: e.target.value })} /></Field>
          <Field label={t("inv.expiry")}><Input required type="date" value={lot.expiry_date} onChange={(e) => setLot({ ...lot, expiry_date: e.target.value })} /></Field>
          <Field label={t("inv.qty")}><Input required type="number" min={1} value={lot.quantity} onChange={(e) => setLot({ ...lot, quantity: e.target.value })} /></Field>
        </div>
        <p className="text-xs text-muted">{t("inv.fefoNote")}</p>
        <Button type="submit" loading={busy} className="w-full"><PackagePlus className="size-4" />{t("inv.receive")}</Button>
      </form>
    </Modal>
  );
}

function MarkerModal({ id, onClose, onChanged }) {
  const { t, L } = useI18n();
  const { can } = useAuth();
  const toast = useToast();
  const loc = useLocalization();
  const res = useAsync(() => api(`/inventory/${id}`), [id]);
  const [busy, setBusy] = useState(null);
  const m = res.data;
  const write = can("inventory.write");

  const run = async (key, fn) => {
    setBusy(key);
    try {
      const updated = await fn();
      res.setData(updated);
      onChanged(updated);
      toast(t("common.saved"));
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(null);
    }
  };

  const p = m?.lab_passport || {};
  return (
    <Modal open onClose={onClose} title={m ? <span className="font-mono">{m.name} <span className="text-sm text-muted">{m.clone && `(${m.clone})`}</span></span> : "…"} wide>
      {!m ? <Spinner /> : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2"><InventoryTags tags={m.tags} /></div>
          {L(m.description) && <p className="text-sm">{L(m.description)}</p>}
          <div className="grid grid-cols-3 gap-2 text-center">
            {[[m.stock, t("inv.stock")], [m.expiry_date || "—", t("inv.expiry")], [m.used_30d, t("inv.used30")]].map(([v, k]) => (
              <div key={k} className="rounded-xl bg-surface-2 p-3"><div className="font-mono text-lg font-bold">{v}</div><div className="text-xs text-muted">{k}</div></div>
            ))}
          </div>

          <div className="rounded-2xl border border-line p-4">
            <div className="mb-3 flex items-center gap-2">
              <h3 className="text-sm font-bold text-primary-ink">{t("inv.passport")}</h3>
              <span className="ml-auto">
                {m.passport_verified
                  ? <Badge color="emerald"><BadgeCheck className="size-3" />{t("inv.verified")}</Badge>
                  : <Badge color="amber"><ShieldAlert className="size-3" />{t("inv.notVerified")}</Badge>}
              </span>
            </div>
            <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
              {[
                [t("inv.buffer"), p.retrieval_buffer],
                [t("inv.retrievalTime"), p.retrieval_time_min != null && `${p.retrieval_time_min} ${t("inv.min")}`],
                [t("inv.dilution"), p.dilution],
                [t("inv.incubation"), p.incubation_min != null && `${p.incubation_min} ${t("inv.min")}`],
                [t("inv.control"), p.control_tissue],
                [t("inv.localization"), loc(m.localization) || null],
              ].map(([k, v]) => (
                <div key={k}><dt className="text-xs text-muted">{k}</dt><dd className="font-mono font-medium">{v || "—"}</dd></div>
              ))}
            </dl>
            {p.notes && <p className="mt-3 text-xs text-muted">{t("inv.notes")}: {p.notes}</p>}
            {write && (
              <Button variant="soft" className="mt-3 w-full" loading={busy === "verify"} onClick={() => run("verify", () => api(`/inventory/${id}/passport/verify`, { method: "POST" }))}>
                <BadgeCheck className="size-4" />{t("inv.verify")}
              </Button>
            )}
          </div>

          {m.tandem_with?.length > 0 && (
            <div className="rounded-2xl border border-purple-200 bg-purple-50/60 p-4 text-sm dark:border-purple-500/30 dark:bg-purple-500/5">
              <div className="mb-1 text-xs font-bold text-purple-700 dark:text-purple-300">🔗 {t("inv.tandemWith")}: <span className="font-mono">{m.tandem_with.join(", ")}</span></div>
              <p>{L(m.reason)}</p>
            </div>
          )}

          <div>
            <h3 className="mb-1 text-sm font-bold">{t("inv.lots")}</h3>
            <p className="mb-2 text-xs text-muted">{t("inv.fefoNote")}</p>
            <div className="divide-y divide-line rounded-xl border border-line">
              {m.lots.length === 0 && <div className="p-3 text-sm text-muted">{t("common.empty")}</div>}
              {m.lots.map((l) => {
                const expired = new Date(l.expiry_date) < new Date(new Date().toDateString());
                return (
                  <div key={l.id} className="flex items-center gap-3 p-3 text-sm">
                    <span className="font-mono font-medium">{l.lot_number}</span>
                    <span className={cx("font-mono text-xs", expired ? "text-rose-600" : "text-muted")}>{l.expiry_date}{expired && ` · ${t("inv.expired")}`}</span>
                    <span className="ml-auto font-mono">{l.quantity}/{l.received_quantity}</span>
                    {write && l.quantity > 0 && expired && (
                      <Button variant="danger" className="min-h-8 px-2 text-xs" loading={busy === `w${l.id}`}
                        onClick={() => run(`w${l.id}`, () => api(`/inventory/${id}/adjust`, { method: "POST", body: { lot_id: l.id, delta: -l.quantity, reason: "write_off" } }))}>
                        {t("inv.writeOff")}
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}

// ---------------------------------------------------------------- tabs

function StatCard({ tone, title, value, hint, active, onClick }) {
  const styles = {
    rose: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300",
    purple: "border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-500/30 dark:bg-purple-500/10 dark:text-purple-300",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300",
  };
  const dot = { rose: "bg-rose-500", purple: "bg-purple-500", emerald: "bg-emerald-500" };
  return (
    <button onClick={onClick} aria-pressed={active}
      className={cx("rounded-2xl border p-3.5 text-left transition sm:p-4", styles[tone], active ? "ring-2 ring-current ring-offset-2 ring-offset-bg" : "hover:shadow-md")}>
      <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide"><span className={cx("size-2.5 rounded-full", dot[tone])} />{title}</div>
      <div className="mt-1.5 text-2xl font-extrabold">{value}</div>
      <div className="mt-0.5 text-xs opacity-80">{hint}</div>
    </button>
  );
}

function MarkerRow({ m, canWrite, onOpen, onQuick }) {
  const { t } = useI18n();
  const loc = useLocalization();
  const tag = mainTag(m.tags);
  const tone = TONE[tag];
  const pct = m.capacity ? Math.min(100, Math.round((m.stock / m.capacity) * 100)) : m.stock ? 100 : 0;
  return (
    <Card interactive className="cursor-pointer p-5" onClick={onOpen}>
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-lg font-bold">{m.name}</span>
            {m.clone && <span className="font-mono text-xs text-muted">({m.clone})</span>}
            {tag !== "none" && <Badge color={tone.pill}>{t(`inv.tagShort.${tag}`)}</Badge>}
          </div>
          <div className="mt-1 text-sm text-muted">
            {m.localization && <>{t("inv.staining")}: <b className="font-semibold text-fg">{loc(m.localization)}</b></>}
            {m.lab_passport?.control_tissue && <> • {t("inv.controlShort")}: {m.lab_passport.control_tissue}</>}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className={cx("text-xl font-extrabold", m.stock === 0 ? "text-rose-600 dark:text-rose-300" : tone.num)}>{t("inv.tests", { n: m.stock })}</div>
          <div className="mt-1 text-xs text-muted">{t("inv.usedTimes", { n: m.used_30d })}</div>
        </div>
      </div>
      <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-surface-2" role="meter" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className={cx("h-full rounded-full transition-all", tone.bar)} style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <span className={cx("text-sm", m.days_to_expiry != null && m.days_to_expiry < 60 ? "font-semibold text-rose-600 dark:text-rose-300" : "text-muted")}>
          {m.days_to_expiry != null ? t("inv.expiresIn", { n: m.days_to_expiry }) : "—"}
        </span>
        {canWrite && (
          <button onClick={(e) => { e.stopPropagation(); onQuick(); }} className="min-h-9 rounded-lg bg-surface-2 px-3 text-sm font-semibold hover:bg-line">
            {t("inv.quickIn", { n: 25 })}
          </button>
        )}
      </div>
    </Card>
  );
}

function StockTab({ list, summary, onOpen }) {
  const { t } = useI18n();
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const tag = params.get("tag") || "";
  const [receive, setReceive] = useState(null);
  const write = can("inventory.write");

  // FEFO alerts first, then the busiest markers.
  const items = (list.data || [])
    .filter((m) => !tag || m.tags.includes(tag))
    .sort((a, b) => (b.tags.includes("expiring") - a.tags.includes("expiring")) || (b.used_30d - a.used_30d) || a.name.localeCompare(b.name));
  const toggleTag = (v) => setParams((p) => { const n = new URLSearchParams(p); tag === v ? n.delete("tag") : n.set("tag", v); return n; });
  const s = summary.data;
  const refresh = () => { list.reload(); summary.reload(); };

  return (
    <>
      <div className="mb-5 grid grid-cols-3 gap-2 sm:gap-3">
        <StatCard tone="rose" title={t("inv.cardExpiring")} value={t("inv.count", { n: s?.expiring ?? "…" })} hint={t("inv.cardExpiringHint")} active={tag === "expiring"} onClick={() => toggleTag("expiring")} />
        <StatCard tone="purple" title={t("inv.cardSlow")} value={t("inv.count", { n: s?.slow ?? "…" })} hint={t("inv.cardSlowHint")} active={tag === "slow"} onClick={() => toggleTag("slow")} />
        <StatCard tone="emerald" title={t("inv.cardFast")} value={t("inv.count", { n: s?.fast ?? "…" })} hint={t("inv.cardFastHint")} active={tag === "fast"} onClick={() => toggleTag("fast")} />
      </div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold text-muted">{t("inv.showing", { what: tag ? t(`inv.tagShort.${tag}`) : t("inv.allMarkers") })} · {items.length}</div>
        {write && <Button onClick={() => setReceive({ marker: "" , qty: 25 })}><Plus className="size-4" />{t("inv.addVial")}</Button>}
      </div>
      {list.loading ? <Loading /> : list.error ? <ErrorBox error={list.error} onRetry={list.reload} /> : items.length === 0 ? (
        <Empty icon={FlaskConical}>{t("common.empty")}</Empty>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {items.map((m) => <MarkerRow key={m.id} m={m} canWrite={write} onOpen={() => onOpen(m.id)} onQuick={() => setReceive({ marker: String(m.id), qty: 25 })} />)}
        </div>
      )}
      {receive && (
        <ReceiveModal open onClose={() => setReceive(null)} markers={list.data || []} initialMarker={receive.marker} initialQty={receive.qty} onDone={refresh} />
      )}
    </>
  );
}

function TandemTab({ markers }) {
  const { t, L } = useI18n();
  const [organ, setOrgan] = useState("breast");
  const [selected, setSelected] = useState(["ER", "PR", "HER2", "Ki-67"]);
  const routine = ROUTINE[organ] || ROUTINE.other;
  const toggle = (n) => setSelected((s) => (s.includes(n) ? s.filter((x) => x !== n) : [...s, n]));
  const pairs = (markers || []).filter((m) => m.tandem_with?.length);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">{t("inv.tandemPick")}</p>
      <Chips value={organ} onChange={(o) => { setOrgan(o); setSelected(ROUTINE[o] || []); }}
        items={Object.keys(ROUTINE).map((o) => ({ value: o, label: t(`organs.${o}`) }))} />
      <div className="flex flex-wrap gap-2">
        {routine.map((n) => (
          <button key={n} onClick={() => toggle(n)} aria-pressed={selected.includes(n)}
            className={cx("min-h-10 rounded-xl border px-3 font-mono text-sm font-semibold transition", selected.includes(n) ? "border-primary bg-primary-soft text-primary-ink" : "border-line bg-surface text-muted")}>
            {n}
          </button>
        ))}
      </div>
      <TandemPanel markers={selected.map((name) => ({ name, source: "routine" }))} organ={organ} />
      <Card>
        <h3 className="mb-3 text-sm font-bold">{t("inv.pairs")}</h3>
        <div className="divide-y divide-line">
          {pairs.map((m) => (
            <div key={m.id} className="py-2.5 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-muted">{m.tandem_with.join(" · ")}</span>
                <span className="text-muted">→</span>
                <span className="font-mono font-bold text-purple-700 dark:text-purple-300">{m.name}</span>
                <span className="ml-auto flex gap-1"><InventoryTags tags={m.tags.filter((x) => x === "expiring" || x === "slow")} /></span>
              </div>
              <p className="mt-0.5 text-xs text-muted">{L(m.reason)}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function DailyBars({ daily }) {
  const { t } = useI18n();
  const [hover, setHover] = useState(null);
  const max = Math.max(1, ...daily.map((d) => d.count));
  const ticks = [max, Math.round(max / 2), 0];
  return (
    <div>
      <div className="relative flex h-44 gap-2">
        <div className="flex w-6 flex-col justify-between pb-5 text-right font-mono text-[10px] text-muted">
          {ticks.map((v) => <span key={v}>{v}</span>)}
        </div>
        <div className="relative flex-1">
          <div className="absolute inset-x-0 top-0 bottom-5 flex flex-col justify-between">
            {ticks.map((v) => <div key={v} className="border-t border-dashed border-line" />)}
          </div>
          <div className="absolute inset-x-0 top-0 bottom-5 flex items-end gap-[2px]">
            {daily.map((d, i) => (
              <div key={d.date} className="relative flex h-full flex-1 items-end"
                onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} onClick={() => setHover(i)}>
                <div className={cx("w-full rounded-t-[4px] transition", hover === i ? "bg-primary-strong" : "bg-primary")} style={{ height: `${(d.count / max) * 100}%`, minHeight: d.count ? 2 : 0 }} />
                {hover === i && (
                  <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg bg-slate-900 px-2 py-1 text-xs text-white shadow-lg">
                    <div className="font-mono">{d.date}</div>
                    <div className="font-semibold">{d.count} {t("inv.testsShort")}</div>
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="absolute inset-x-0 bottom-0 flex justify-between font-mono text-[10px] text-muted">
            <span>{daily[0]?.date.slice(5)}</span><span>{daily[daily.length - 1]?.date.slice(5)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatsTab() {
  const { t } = useI18n();
  const stats = useAsync(() => api("/inventory/stats"), []);
  const [view, setView] = useState("chart");
  if (stats.loading) return <Loading />;
  if (stats.error) return <ErrorBox error={stats.error} onRetry={stats.reload} />;
  const s = stats.data;
  const maxTop = Math.max(1, ...s.top.map((x) => x.count));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Card><div className="text-xs font-semibold text-muted">{t("inv.statsTotal")}</div><div className="mt-1 font-mono text-3xl font-extrabold text-primary-ink">{s.total_tests}</div></Card>
        <Card><div className="text-xs font-semibold text-muted">{t("inv.statsExpired")}</div><div className={cx("mt-1 font-mono text-3xl font-extrabold", s.expired_tests_on_shelf ? "text-rose-600 dark:text-rose-300" : "")}>{s.expired_tests_on_shelf}</div></Card>
      </div>

      <Card>
        <div className="mb-3 flex items-center justify-between gap-2">
          <h3 className="text-sm font-bold">{t("inv.statsDaily")}</h3>
          <div className="flex rounded-lg bg-surface-2 p-0.5 text-xs font-semibold">
            {["chart", "table"].map((v) => (
              <button key={v} onClick={() => setView(v)} className={cx("rounded-md px-2 py-1", view === v ? "bg-surface shadow-sm" : "text-muted")}>{t(`inv.${v}`)}</button>
            ))}
          </div>
        </div>
        {view === "chart" ? <DailyBars daily={s.daily} /> : (
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-muted"><th className="py-1">{t("inv.date")}</th><th className="py-1 text-right">{t("inv.testsShort")}</th></tr></thead>
              <tbody>{[...s.daily].reverse().map((d) => <tr key={d.date} className="border-t border-line"><td className="py-1 font-mono">{d.date}</td><td className="py-1 text-right font-mono">{d.count}</td></tr>)}</tbody>
            </table>
          </div>
        )}
      </Card>

      <Card>
        <h3 className="mb-3 text-sm font-bold">{t("inv.statsTop")}</h3>
        <div className="space-y-2">
          {s.top.map((x) => (
            <div key={x.name} className="flex items-center gap-3 text-sm" title={`${x.name}: ${x.count}`}>
              <span className="w-24 shrink-0 truncate font-mono font-semibold">{x.name}</span>
              <div className="h-3 flex-1 rounded-full bg-surface-2">
                <div className="h-full rounded-full bg-primary" style={{ width: `${(x.count / maxTop) * 100}%` }} />
              </div>
              <span className="w-8 text-right font-mono text-muted">{x.count}</span>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-sm font-bold">{t("inv.statsCoverage")}</h3>
          <div className="divide-y divide-line text-sm">
            {s.coverage.slice(0, 12).map((c) => (
              <div key={c.name} className="flex items-center justify-between py-2">
                <span className="font-mono font-medium">{c.name}</span>
                <span className={cx("font-mono", c.days_of_supply != null && c.days_of_supply < 30 ? "font-bold text-amber-600 dark:text-amber-300" : "text-muted")}>
                  {c.days_of_supply != null ? t("inv.daysSupply", { n: c.days_of_supply }) : t("inv.noUse")}
                </span>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <h3 className="mb-3 text-sm font-bold">{t("inv.statsIdle")}</h3>
          {s.idle.length ? (
            <div className="flex flex-wrap gap-2">{s.idle.map((n) => <Badge key={n} color="purple" className="font-mono">{n}</Badge>)}</div>
          ) : <p className="text-sm text-muted">—</p>}
        </Card>
      </div>
    </div>
  );
}

export default function Inventory() {
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "stock";
  const openId = params.get("marker");
  const summary = useAsync(() => api("/inventory/summary"), []);
  const list = useAsync(() => api("/inventory"), []);

  const setOpen = (id) => setParams((p) => { const n = new URLSearchParams(p); id ? n.set("marker", id) : n.delete("marker"); return n; });
  const onChanged = (m) => {
    list.setData((xs) => (xs || []).map((x) => (x.id === m.id ? { ...x, ...m } : x)));
    summary.reload();
  };
  const markers = useMemo(() => list.data || [], [list.data]);

  return (
    <div className="fade-in">
      <Segmented
        value={tab}
        onChange={(v) => setParams({ tab: v })}
        tabs={[
          { value: "stock", label: t("inv.tabStock"), icon: "📦" },
          { value: "tandem", label: t("inv.tabTandem"), icon: "🔗" },
          { value: "stats", label: t("inv.tabStats"), icon: "📊" },
        ]}
      />
      {tab === "stock" && <StockTab list={list} summary={summary} onOpen={setOpen} />}
      {tab === "tandem" && <TandemTab markers={markers} />}
      {tab === "stats" && <StatsTab />}
      {openId && <MarkerModal id={openId} onClose={() => setOpen(null)} onChanged={onChanged} />}
    </div>
  );
}
