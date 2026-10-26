import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Calculator, CheckCircle2, ChevronDown, FileSignature, MessagesSquare, Printer, Send, Tags } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import { confirmDialog, openExternal } from "../lib/telegram";
import Gallery from "../components/Gallery";
import MarkerPicker, { TandemPanel } from "../components/MarkerPicker";
import ScoringModal, { ScoringSummary } from "../components/ScoringModal";
import { useToast } from "../components/toast";
import { AuthImage, Badge, Button, Card, ErrorBox, Field, Loading, StatusBadge, Textarea, cx, useAsync } from "../components/ui";

function ReportEditor({ biopsy, editable, onSaved }) {
  const { t, L } = useI18n();
  const toast = useToast();
  const templates = useAsync(() => api("/atlas/templates"), []);
  const [text, setText] = useState({ macro_text: biopsy.macro_text || "", micro_text: biopsy.micro_text || "", diagnosis: biopsy.diagnosis || "" });
  const [busy, setBusy] = useState(false);
  const dirty = ["macro_text", "micro_text", "diagnosis"].some((k) => (biopsy[k] || "") !== text[k]);

  const insert = (field, id) => {
    const tpl = templates.data?.find((x) => x.id === id);
    if (tpl) setText((s) => ({ ...s, [field]: (s[field] ? s[field] + "\n\n" : "") + L(tpl.text) }));
  };

  const save = async () => {
    setBusy(true);
    try {
      onSaved(await api(`/biopsies/${biopsy.code}`, { method: "PATCH", body: text }));
      toast(t("common.saved"));
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const block = (field, kind, label) => (
    <Field label={
      <span className="flex items-center justify-between gap-2">
        {label}
        {editable && kind && templates.data && (
          <select className="max-w-48 rounded-lg border border-line bg-surface-2 px-2 py-1 text-[11px] normal-case tracking-normal text-fg/85"
            value="" onChange={(e) => insert(field, e.target.value)}>
            <option value="">{t("cases.templates")} ▾</option>
            {templates.data.filter((x) => x.kind === kind && (!x.organ || x.organ === biopsy.organ)).map((x) => (
              <option key={x.id} value={x.id}>{L(x.title)}</option>
            ))}
          </select>
        )}
      </span>
    }>
      <Textarea value={text[field]} readOnly={!editable} onChange={(e) => setText((s) => ({ ...s, [field]: e.target.value }))} rows={field === "diagnosis" ? 3 : 5} />
    </Field>
  );

  return (
    <div className="space-y-3">
      {block("macro_text", "macro", t("cases.macro"))}
      {block("micro_text", "micro", t("cases.micro"))}
      {block("diagnosis", null, t("cases.diagnosis"))}
      {editable && <Button variant="ghost" onClick={save} loading={busy} disabled={!dirty}>{t("common.save")}</Button>}
    </div>
  );
}

function Consilium({ biopsy, images, canPost, onChange }) {
  const { t } = useI18n();
  const toast = useToast();
  const [text, setText] = useState("");
  const [attach, setAttach] = useState([]);
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const toggle = async () => {
    try {
      onChange(await api(`/biopsies/${biopsy.code}/consilium`, { method: "POST", body: { open: !biopsy.consilium_open } }));
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const send = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const c = await api(`/biopsies/${biopsy.code}/comments`, { method: "POST", body: { text, image_ids: attach } });
      onChange({ ...biopsy, consilium_comments: [...biopsy.consilium_comments, c] });
      setText("");
      setAttach([]);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className={cx(biopsy.consilium_open && "border-purple-300 dark:border-purple-500/40")}>
      <button className="flex w-full items-center gap-2 text-left" onClick={() => setExpanded((x) => !x)}>
        <MessagesSquare className="size-5 text-purple-700 dark:text-purple-300" />
        <span className="font-semibold">{t("cases.consilium")}</span>
        <span className="rounded-full bg-surface-2 px-2 font-mono text-xs">{biopsy.consilium_comments.length}</span>
        {biopsy.consilium_open && <Badge color="purple">●</Badge>}
        <ChevronDown className={cx("ml-auto size-4 text-muted transition", expanded && "rotate-180")} />
      </button>
      {expanded && (
        <div className="fade-in mt-3 space-y-3">
          {canPost && biopsy.status !== "reported" && (
            <Button variant={biopsy.consilium_open ? "ghost" : "smart"} className="w-full" onClick={toggle}>
              {biopsy.consilium_open ? t("cases.closeConsilium") : t("cases.openConsilium")}
            </Button>
          )}
          {biopsy.consilium_comments.length === 0 && <p className="text-sm text-muted">{t("cases.noComments")}</p>}
          <ul className="space-y-2">
            {biopsy.consilium_comments.map((c) => (
              <li key={c.id} className="rounded-xl border border-line bg-surface-2 p-3">
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-semibold text-indigo-600 dark:text-indigo-300">{c.user_name}</span>
                  <span className="text-muted">{t(`roles.${c.role}`)}</span>
                  <span className="ml-auto font-mono text-muted">{c.created_at.slice(0, 16).replace("T", " ")}</span>
                </div>
                <p className="mt-1.5 whitespace-pre-wrap text-sm">{c.text}</p>
                {c.image_ids?.length > 0 && (
                  <div className="mt-2 flex gap-1.5">
                    {c.image_ids.map((id) => <AuthImage key={id} src={`/api/images/${id}/file`} className="size-14 rounded-lg object-cover" />)}
                  </div>
                )}
              </li>
            ))}
          </ul>
          {canPost && (
            <div className="space-y-2">
              <Textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} placeholder={t("cases.comment")} />
              {images.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {images.map((img) => (
                    <button key={img.id} onClick={() => setAttach((a) => (a.includes(img.id) ? a.filter((x) => x !== img.id) : [...a, img.id]))}
                      className={cx("overflow-hidden rounded-lg ring-2", attach.includes(img.id) ? "ring-purple-500" : "ring-transparent opacity-60")}>
                      <AuthImage src={img.url} className="size-12 object-cover" />
                    </button>
                  ))}
                </div>
              )}
              <Button variant="smart" className="w-full" onClick={send} loading={busy} disabled={!text.trim()}><Send className="size-4" />{t("cases.send")}</Button>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export default function CaseDetail() {
  const { code } = useParams();
  const { t, lang } = useI18n();
  const { can } = useAuth();
  const toast = useToast();
  const res = useAsync(() => api(`/biopsies/${code}`), [code]);
  const imgs = useAsync(() => api(`/images?biopsy=${code}`), [code]);
  const [scoring, setScoring] = useState(false);
  const [busy, setBusy] = useState(null);
  const [b, setB] = useState(null);

  useEffect(() => { if (res.data) setB(res.data); }, [res.data]);

  if (res.loading || !b) return res.error ? <ErrorBox error={res.error} /> : <Loading />;

  const isPath = can("approve");
  const editablePanel = isPath && b.status === "registered";
  const editableReport = isPath && b.status !== "reported";
  const merge = (next) => setB((cur) => ({ ...cur, ...next }));

  const addMarker = async (name, source) => {
    try {
      const r = await api(`/biopsies/${code}/markers`, { method: "POST", body: { name, source } });
      merge(r.biopsy);
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const removeMarker = async (name) => {
    try {
      merge(await api(`/biopsies/${code}`, { method: "PATCH", body: { selected_markers: b.selected_markers.filter((m) => m.name !== name) } }));
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const printPage = async (kind) => {
    try {
      const { url } = await api(`/biopsies/${code}/print-link`, { method: "POST", body: { kind, lang } });
      // Telegram's webview cannot print: open the signed page in the system browser instead.
      openExternal(new URL(url, window.location.origin).href);
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const approve = async () => {
    if (!(await confirmDialog(t("cases.approveConfirm")))) return;
    setBusy("approve");
    try {
      const r = await api(`/biopsies/${code}/approve`, { method: "POST" });
      merge(r.biopsy);
      toast(t("cases.approvedMsg", { items: r.deducted.map((d) => `${d.name} (${d.stock_left})`).join(", ") }));
    } catch (e) {
      const short = e.detail?.markers;
      toast(short ? t("cases.shortage", { items: short.join(", ") }) : e.message, "error");
    } finally {
      setBusy(null);
    }
  };

  const signOut = async () => {
    if (!(await confirmDialog(t("cases.signOutConfirm")))) return;
    setBusy("report");
    try {
      merge(await api(`/biopsies/${code}/report`, { method: "POST" }));
      toast(t("status.reported"));
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="fade-in">
      <Link to="/cases" className="mb-2 inline-block text-sm text-muted hover:text-fg/85">← {t("cases.title")}</Link>
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <h1 className="font-mono text-2xl font-bold text-primary-ink">{b.code}</h1>
        <StatusBadge status={b.status} />
        {b.consilium_open && <Badge color="purple"><MessagesSquare className="size-3" />{t("cases.consilium")}</Badge>}
        <div className="ml-auto flex gap-2">
          {can("approve") && <Button variant="outline" className="min-h-9 text-xs" onClick={() => printPage("report")}><Printer className="size-4" />{t("cases.printReport")}</Button>}
          <Button variant="outline" className="min-h-9 text-xs" onClick={() => printPage("labels")}><Tags className="size-4" />{t("cases.printLabels")}</Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="space-y-4">
          <Card>
            <div className="grid gap-3 text-sm sm:grid-cols-2">
              <div><div className="text-xs text-muted">{t("cases.patient")}</div><div className="font-medium">{b.patient_name}{b.patient_age != null && `, ${b.patient_age}`}{b.patient_sex && ` · ${b.patient_sex === "F" ? t("cases.female") : t("cases.male")}`}</div></div>
              <div><div className="text-xs text-muted">{t("cases.organ")}</div><div>{t(`organs.${b.organ}`)}</div></div>
              <div className="sm:col-span-2"><div className="text-xs text-muted">{t("cases.suspicion")}</div><div>{b.clinical_suspicion || "—"}</div></div>
              <div><div className="text-xs text-muted">{t("cases.initialTests")}</div><div className="font-mono">{b.initial_tests.join(", ") || "—"}</div></div>
              <div><div className="text-xs text-muted">{t("cases.created")}</div><div className="font-mono">{b.created_at.slice(0, 16).replace("T", " ")}</div></div>
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 font-semibold">{t("cases.panel")}</h2>
            <MarkerPicker markers={b.selected_markers} organ={editablePanel ? b.organ : null} onAdd={addMarker} onRemove={removeMarker} disabled={!editablePanel} />
            {b.status !== "registered" && <p className="mt-3 text-xs text-muted">{t("cases.frozen")}</p>}
            {editablePanel && (
              <>
                <div className="mt-4"><TandemPanel markers={b.selected_markers} organ={b.organ} onAdd={addMarker} /></div>
                <Button className="mt-4 w-full" onClick={approve} loading={busy === "approve"} disabled={!b.selected_markers.length}>
                  <CheckCircle2 className="size-4" />{t("cases.approve")}
                </Button>
              </>
            )}
          </Card>

          <Card>
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="font-semibold">{t("cases.scoring")}</h2>
              {can("scoring") && b.status !== "reported" && (
                <Button variant="smart" className="min-h-9 text-xs" onClick={() => setScoring(true)}><Calculator className="size-4" />{t("cases.openScoring")}</Button>
              )}
            </div>
            {b.scoring_result ? <ScoringSummary result={b.scoring_result} /> : <p className="text-sm text-muted">—</p>}
          </Card>

          <Card>
            <ReportEditor key={b.code} biopsy={b} editable={editableReport} onSaved={merge} />
            {isPath && b.status === "approved" && (
              <Button className="mt-4 w-full" onClick={signOut} loading={busy === "report"} disabled={!b.diagnosis?.trim()}>
                <FileSignature className="size-4" />{t("cases.signOut")}
              </Button>
            )}
          </Card>

          <Card>
            <h2 className="mb-3 font-semibold">{t("cases.images")}</h2>
            {imgs.data && (
              <Gallery images={imgs.data} setImages={(fn) => imgs.setData(fn(imgs.data))} target={{ biopsy: code }}
                canUpload={b.status !== "reported"} canAnnotate={isPath} />
            )}
          </Card>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          {(can("consilium") || b.consilium_comments.length > 0) && (
            <Consilium biopsy={b} images={imgs.data || []} canPost={can("consilium")} onChange={merge} />
          )}
        </aside>
      </div>

      {scoring && <ScoringModal open onClose={() => setScoring(false)} code={code} initial={b.scoring_result} onSaved={merge} />}
    </div>
  );
}
