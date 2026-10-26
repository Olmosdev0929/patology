import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { MessagesSquare, Plus, Search, TestTubes } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import MarkerPicker, { TandemPanel } from "../components/MarkerPicker";
import { useToast } from "../components/toast";
import { Button, Card, Empty, ErrorBox, Field, Input, Loading, Modal, PageHeader, Select, StatusBadge, Tabs, Textarea, useAsync } from "../components/ui";

const ORGANS = ["breast", "lung", "colon", "stomach", "liver", "kidney", "prostate", "thyroid", "skin", "lymph", "cervix", "other"];

function NewCaseModal({ open, onClose }) {
  const { t } = useI18n();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({ patient_name: "", patient_age: "", patient_sex: "", organ: "breast", clinical_suspicion: "", initial_tests: "H&E" });
  const [markers, setMarkers] = useState([]);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const addMarker = (name, source) => setMarkers((ms) => (ms.some((m) => m.name.toLowerCase() === name.toLowerCase()) ? ms : [...ms, { name, source }]));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const b = await api("/biopsies", {
        method: "POST",
        body: {
          ...form,
          patient_age: form.patient_age ? Number(form.patient_age) : null,
          patient_sex: form.patient_sex || null,
          initial_tests: form.initial_tests.split(",").map((s) => s.trim()).filter(Boolean),
          selected_markers: markers,
        },
      });
      toast(`${b.code} ✓`);
      onClose();
      navigate(`/cases/${b.code}`);
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={t("cases.new")} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_100px_120px]">
          <Field label={t("cases.patient")}><Input required minLength={2} value={form.patient_name} onChange={set("patient_name")} autoComplete="off" /></Field>
          <Field label={t("cases.age")}><Input type="number" min={0} max={130} inputMode="numeric" value={form.patient_age} onChange={set("patient_age")} /></Field>
          <Field label={t("cases.sex")}>
            <Select value={form.patient_sex} onChange={set("patient_sex")}>
              <option value="">—</option>
              <option value="F">{t("cases.female")}</option>
              <option value="M">{t("cases.male")}</option>
            </Select>
          </Field>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("cases.organ")}>
            <Select value={form.organ} onChange={set("organ")}>
              {ORGANS.map((o) => <option key={o} value={o}>{t(`organs.${o}`)}</option>)}
            </Select>
          </Field>
          <Field label={t("cases.initialTests")}><Input value={form.initial_tests} onChange={set("initial_tests")} /></Field>
        </div>
        <Field label={t("cases.suspicion")}><Textarea rows={2} value={form.clinical_suspicion} onChange={set("clinical_suspicion")} /></Field>

        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">{t("cases.panel")}</div>
          <MarkerPicker markers={markers} organ={form.organ} onAdd={addMarker} onRemove={(n) => setMarkers((ms) => ms.filter((m) => m.name !== n))} />
        </div>
        {markers.length > 0 && <TandemPanel markers={markers} organ={form.organ} onAdd={addMarker} />}

        <Button type="submit" loading={busy} className="w-full">{t("cases.register")}</Button>
      </form>
    </Modal>
  );
}

export default function Cases() {
  const { t } = useI18n();
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const status = params.get("status") || "";
  const consilium = params.get("consilium") === "1";
  const [q, setQ] = useState("");

  const query = new URLSearchParams();
  if (status) query.set("status", status);
  if (consilium) query.set("consilium", "true");
  if (q.trim()) query.set("q", q.trim());
  const list = useAsync(() => api(`/biopsies?${query}`), [query.toString()]);

  const setFilter = (value) => setParams(value === "consilium" ? { consilium: "1" } : value ? { status: value } : {});
  const active = consilium ? "consilium" : status;

  return (
    <div className="fade-in">
      <PageHeader
        title={t("cases.title")}
        actions={<Button onClick={() => setParams({ ...Object.fromEntries(params), new: "1" })}><Plus className="size-4" />{t("cases.new")}</Button>}
      />
      <div className="relative mb-3">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("cases.searchPh")} className="pl-9" type="search" />
      </div>
      <Tabs
        value={active}
        onChange={setFilter}
        tabs={[
          { value: "", label: t("common.all") },
          { value: "registered", label: t("status.registered") },
          { value: "approved", label: t("status.approved") },
          { value: "reported", label: t("status.reported") },
          ...(can("consilium") ? [{ value: "consilium", label: t("cases.consilium"), icon: MessagesSquare }] : []),
        ]}
      />
      {list.loading ? <Loading /> : list.error ? <ErrorBox error={list.error} onRetry={list.reload} /> : list.data.length === 0 ? (
        <Empty icon={TestTubes}>{t("common.empty")}</Empty>
      ) : (
        <div className="grid gap-2 md:grid-cols-2">
          {list.data.map((b) => (
            <Link key={b.code} to={`/cases/${b.code}`}>
              <Card interactive className="h-full">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-primary-ink">{b.code}</span>
                  {b.consilium_open && <MessagesSquare className="size-4 text-purple-700 dark:text-purple-300" />}
                  <span className="ml-auto"><StatusBadge status={b.status} /></span>
                </div>
                <div className="mt-2 truncate text-sm">{b.patient_name}{b.patient_age != null && `, ${b.patient_age}`}</div>
                <div className="mt-0.5 truncate text-xs text-muted">{t(`organs.${b.organ}`)} · {b.clinical_suspicion || "—"}</div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {b.selected_markers.map((m) => (
                    <span key={m.name} className={`rounded-md px-1.5 py-0.5 font-mono text-[11px] ${m.source === "tandem" ? "bg-purple-500/20 text-purple-700 dark:text-purple-300" : m.source === "custom" ? "bg-amber-500/20 text-amber-600 dark:text-amber-300" : "bg-surface-2 text-fg/85"}`}>
                      {m.name}
                    </span>
                  ))}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
      <NewCaseModal open={params.get("new") === "1"} onClose={() => { params.delete("new"); setParams(params); }} />
    </div>
  );
}
