import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Activity, HardDrive, ShieldCheck, Users } from "lucide-react";
import { formatBytes } from "../lib/upload";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import { useToast } from "../components/toast";
import { Badge, Button, Card, ErrorBox, Loading, PageHeader, Select, Tabs, cx, useAsync } from "../components/ui";

const ROLES = ["super_admin", "pathologist", "technician", "resident"];

function Staff() {
  const { t } = useI18n();
  const { user: me } = useAuth();
  const toast = useToast();
  const users = useAsync(() => api("/users"), []);

  const update = async (u, patch) => {
    try {
      const next = await api(`/users/${u.id}`, { method: "PATCH", body: patch });
      users.setData(users.data.map((x) => (x.id === u.id ? next : x)));
      toast(t("common.saved"));
    } catch (e) {
      toast(e.message, "error");
    }
  };

  if (users.loading) return <Loading />;
  if (users.error) return <ErrorBox error={users.error} />;
  return (
    <Card className="divide-y divide-line p-0">
      {users.data.map((u) => (
        <div key={u.id} className={cx("flex flex-wrap items-center gap-3 px-4 py-3", !u.is_active && "opacity-50")}>
          <div className="min-w-0 flex-1">
            <div className="truncate font-medium">{u.name} {u.id === me.id && <Badge color="indigo">you</Badge>}</div>
            <div className="font-mono text-xs text-muted">{u.username ? `@${u.username}` : `tg:${u.telegram_id}`}</div>
          </div>
          <Select className="w-auto min-w-44" value={u.role} disabled={u.id === me.id} onChange={(e) => update(u, { role: e.target.value })}>
            {ROLES.map((r) => <option key={r} value={r}>{t(`roles.${r}`)}</option>)}
          </Select>
          <Button variant={u.is_active ? "ghost" : "primary"} className="min-h-10 text-xs" disabled={u.id === me.id} onClick={() => update(u, { is_active: !u.is_active })}>
            {u.is_active ? "⏸" : "▶"} {t("admin.active")}
          </Button>
        </div>
      ))}
    </Card>
  );
}

function Kpi() {
  const { t } = useI18n();
  const kpi = useAsync(() => api("/kpi"), []);
  if (kpi.loading) return <Loading />;
  if (kpi.error) return <ErrorBox error={kpi.error} />;
  const max = Math.max(1, ...kpi.data.staff.map((s) => s.cases_done));
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        {Object.entries(kpi.data.cases).map(([k, v]) => (
          <Card key={k}><div className="font-mono text-2xl font-bold">{v}</div><div className="text-xs text-muted">{t(`status.${k}`)}</div></Card>
        ))}
      </div>
      <Card className="overflow-x-auto p-0">
        <table className="w-full min-w-[520px] text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-muted">
            <tr className="border-b border-line">
              <th className="px-4 py-3 font-medium">{t("admin.staff")}</th>
              <th className="px-4 py-3 font-medium">{t("admin.casesDone")}</th>
              <th className="px-4 py-3 text-right font-medium">{t("admin.panels")}</th>
              <th className="px-4 py-3 text-right font-medium">{t("admin.saved")}</th>
            </tr>
          </thead>
          <tbody>
            {kpi.data.staff.map((s) => (
              <tr key={s.id} className="border-b border-line last:border-0">
                <td className="px-4 py-3">{s.name}<div className="text-xs text-muted">{t(`roles.${s.role}`)}</div></td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${(s.cases_done / max) * 100}%` }} />
                    </div>
                    <span className="w-8 text-right font-mono">{s.cases_done}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-mono">{s.panels_approved}</td>
                <td className="px-4 py-3 text-right font-mono text-purple-700 dark:text-purple-300">{s.markers_saved}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function Audit() {
  const { t } = useI18n();
  const toast = useToast();
  const [rows, setRows] = useState([]);
  const first = useAsync(() => api("/audit?limit=50").then((r) => { setRows(r); return r; }), []);
  const [check, setCheck] = useState(null);

  const more = async () => {
    const next = await api(`/audit?limit=50&before_id=${rows[rows.length - 1].id}`);
    setRows((r) => [...r, ...next]);
  };
  const verify = async () => {
    try { setCheck(await api("/audit/verify")); } catch (e) { toast(e.message, "error"); }
  };

  if (first.loading) return <Loading />;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="smart" onClick={verify}><ShieldCheck className="size-4" />{t("admin.verify")}</Button>
        {check && (check.ok
          ? <Badge color="emerald">{t("admin.chainOk", { n: check.checked })}</Badge>
          : <Badge color="rose">{t("admin.chainBroken", { id: check.broken_at })}</Badge>)}
      </div>
      <Card className="divide-y divide-line p-0">
        {rows.map((r) => (
          <div key={r.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-4 py-2.5 text-sm">
            <span className="font-mono text-xs text-muted">{r.created_at.slice(0, 19).replace("T", " ")}</span>
            <span className="font-medium text-indigo-600 dark:text-indigo-300">{r.user_name}</span>
            <span className="min-w-0 flex-1">{t(`audit.${r.action}`, r.details || {})}</span>
            <span className="font-mono text-[10px] text-muted" title="sha256">{r.hash}</span>
          </div>
        ))}
      </Card>
      {rows.length >= 50 && rows.length % 50 === 0 && <Button variant="ghost" onClick={more}>…</Button>}
    </div>
  );
}

function Storage() {
  const { t } = useI18n();
  const st = useAsync(() => api("/storage"), []);
  if (st.loading) return <Loading />;
  if (st.error) return <ErrorBox error={st.error} />;
  const s = st.data;
  const used = s.total - s.free;
  const parts = [["books", s.books, "bg-primary"], ["images", s.images, "bg-purple-500"], ["pending", s.pending_uploads, "bg-amber-500"]];
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-end justify-between gap-2">
          <div><div className="text-xs font-semibold text-muted">{t("storage.free")}</div><div className="font-mono text-3xl font-extrabold text-primary-ink">{formatBytes(s.free)}</div></div>
          <div className="text-right font-mono text-sm text-muted">{formatBytes(used)} / {formatBytes(s.total)}</div>
        </div>
        <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={t("storage.title")}>
          {parts.map(([k, v, c]) => <div key={k} className={c} style={{ width: `${(v / s.total) * 100}%`, minWidth: v ? 3 : 0 }} title={`${t(`storage.${k}`)}: ${formatBytes(v)}`} />)}
        </div>
        <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
          {parts.map(([k, v, c]) => (
            <li key={k} className="flex items-center gap-2"><span className={cx("size-2.5 rounded-full", c)} />{t(`storage.${k}`)}<span className="ml-auto font-mono text-muted">{formatBytes(v)}</span></li>
          ))}
        </ul>
      </Card>
      <div className="grid grid-cols-2 gap-3">
        <Card><div className="text-xs font-semibold text-muted">{t("storage.count")}</div><div className="font-mono text-2xl font-bold">{s.book_count}</div></Card>
        <Card><div className="text-xs font-semibold text-muted">{t("storage.max")}</div><div className="font-mono text-2xl font-bold">{s.max_book_mb} MB</div></Card>
      </div>
      <p className="text-xs text-muted">{t("storage.note")}</p>
    </div>
  );
}

export default function Admin() {
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "staff";
  return (
    <div className="fade-in">
      <PageHeader title={t("admin.title")} />
      <Tabs value={tab} onChange={(v) => setParams({ tab: v })} tabs={[
        { value: "staff", label: t("admin.staff"), icon: Users },
        { value: "kpi", label: t("admin.kpi"), icon: Activity },
        { value: "audit", label: t("admin.audit"), icon: ShieldCheck },
        { value: "storage", label: t("storage.title"), icon: HardDrive },
      ]} />
      {tab === "staff" && <Staff />}
      {tab === "kpi" && <Kpi />}
      {tab === "audit" && <Audit />}
      {tab === "storage" && <Storage />}
    </div>
  );
}
