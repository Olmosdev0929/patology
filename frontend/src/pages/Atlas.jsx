import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { BookOpen, ChevronRight, Pencil, Plus } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import Gallery, { LabeledImage } from "../components/Gallery";
import { useToast } from "../components/toast";
import { Badge, Button, Card, Chips, Empty, ErrorBox, Field, Input, Loading, Modal, Segmented, Select, Textarea, cx, useAsync } from "../components/ui";

const SECTIONS = ["definition", "epidemiology", "clinical", "gross", "microscopic", "ihc", "differential", "prognosis"];

function resultColor(result) {
  if (/^\+|мутац|mutats|перестр|qayta|инактив|inaktiv/i.test(result)) return "text-emerald-600 dark:text-emerald-400";
  if (/^[−-]/.test(result)) return "text-rose-600 dark:text-rose-300";
  return "text-amber-600 dark:text-amber-300";
}

function DiseaseCard({ d }) {
  const { L } = useI18n();
  return (
    <Link to={`/atlas/disease/${d.slug}`} className="block">
      <Card interactive className="p-5">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <Badge color="teal">{L(d.organ.name)}{d.icd10 && ` • ${d.icd10}`}</Badge>
            <h3 className="mt-3 text-lg font-bold leading-snug sm:text-xl">{L(d.name)}</h3>
            {L(d.summary) && <p className="mt-2 line-clamp-2 text-sm text-muted">{L(d.summary)}</p>}
          </div>
          <ChevronRight className="mt-1 size-5 shrink-0 text-muted" />
        </div>
        {d.images.length > 0 && (
          <div className="mt-4 grid grid-cols-2 gap-3">
            {d.images.map((img) => <LabeledImage key={img.id} img={img} compact className="aspect-[16/9] rounded-xl border border-line" />)}
          </div>
        )}
      </Card>
    </Link>
  );
}

function NewDiseaseModal({ open, onClose, organs, defaultOrgan, initial, onSaved }) {
  const { t } = useI18n();
  const toast = useToast();
  const navigate = useNavigate();
  const [lang, setLang] = useState("uz");
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState(() => initial
    ? { organ: initial.organ.slug, name_uz: initial.name.uz || "", name_ru: initial.name.ru || "", name_en: initial.name_en || "", icd10: initial.icd10 || "" }
    : { organ: defaultOrgan || organs?.[0]?.slug || "", name_uz: "", name_ru: "", name_en: "", icd10: "" });
  const [sections, setSections] = useState(() => initial?.sections || {});
  const setSec = (k, v) => setSections((s) => ({ ...s, [k]: { ...(s[k] || {}), [lang]: v } }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (initial) {
        // Editing: organ and slug stay; text fields are replaced.
        onSaved(await api(`/atlas/diseases/${initial.slug}`, { method: "PUT", body: {
          name: { uz: f.name_uz, ru: f.name_ru }, name_en: f.name_en || null, icd10: f.icd10 || null,
          sections: Object.fromEntries(Object.entries(sections).filter(([, v]) => v.uz || v.ru)),
        } }));
        onClose();
        return;
      }
      const d = await api("/atlas/diseases", {
        method: "POST",
        body: {
          organ: f.organ || defaultOrgan || organs[0].slug, name: { uz: f.name_uz, ru: f.name_ru },
          name_en: f.name_en || null, icd10: f.icd10 || null,
          sections: Object.fromEntries(Object.entries(sections).filter(([, v]) => v.uz || v.ru)),
        },
      });
      onClose();
      navigate(`/atlas/disease/${d.slug}`);
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={initial ? t("common.edit") : t("atlas.newDisease")} wide>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("atlas.organ")}>
            <Select value={f.organ || defaultOrgan || ""} disabled={Boolean(initial)} onChange={(e) => setF({ ...f, organ: e.target.value })}>
              {organs?.map((o) => <option key={o.slug} value={o.slug}>{o.icon} {o.name[lang] || o.name.uz}</option>)}
            </Select>
          </Field>
          <Field label={t("atlas.icd")}><Input value={f.icd10} onChange={(e) => setF({ ...f, icd10: e.target.value })} placeholder="C50" /></Field>
          <Field label={t("atlas.nameUz")}><Input required={!f.name_ru} value={f.name_uz} onChange={(e) => setF({ ...f, name_uz: e.target.value })} /></Field>
          <Field label={t("atlas.nameRu")}><Input value={f.name_ru} onChange={(e) => setF({ ...f, name_ru: e.target.value })} /></Field>
          <Field label={t("atlas.nameEn")} className="sm:col-span-2"><Input value={f.name_en} onChange={(e) => setF({ ...f, name_en: e.target.value })} /></Field>
        </div>
        <div className="pt-2">
          <div className="mb-2 text-xs font-semibold text-muted">{t("atlas.fillLang")}</div>
          <Segmented value={lang} onChange={setLang} tabs={[{ value: "uz", label: "O'zbekcha" }, { value: "ru", label: "Русский" }]} />
        </div>
        {SECTIONS.map((k) => (
          <Field key={k} label={`${t(`atlas.sections.${k}`)} · ${lang.toUpperCase()}`}>
            <Textarea rows={2} value={sections[k]?.[lang] || ""} onChange={(e) => setSec(k, e.target.value)} />
          </Field>
        ))}
        <Button type="submit" loading={busy} className="w-full">{initial ? t("common.save") : t("atlas.create")}</Button>
      </form>
    </Modal>
  );
}

export function AtlasHome() {
  const { t, L } = useI18n();
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const organ = params.get("organ") || "";
  const [creating, setCreating] = useState(false);
  const organs = useAsync(() => api("/atlas/organs"), []);
  const list = useAsync(() => api(`/atlas/diseases${organ ? `?organ=${organ}` : ""}`), [organ]);

  return (
    <div className="fade-in">
      <Chips
        value={organ}
        onChange={(v) => setParams(v ? { organ: v } : {})}
        items={[{ value: "", label: t("common.all"), icon: "🌐" }, ...(organs.data || []).map((o) => ({ value: o.slug, label: L(o.name), icon: o.icon }))]}
      />
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="text-sm font-semibold text-muted">{t("atlas.total", { n: list.data?.length ?? "…" })}</div>
        {can("atlas.write") && <Button variant="ink" onClick={() => setCreating(true)}><Plus className="size-4" />{t("atlas.newDisease")}</Button>}
      </div>
      {list.loading ? <Loading /> : list.error ? <ErrorBox error={list.error} onRetry={list.reload} /> : list.data.length === 0 ? (
        <Empty icon={BookOpen}>{t("common.empty")}</Empty>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {list.data.map((d) => <DiseaseCard key={d.slug} d={d} />)}
        </div>
      )}
      <p className="mt-6 text-center text-xs text-muted">{t("atlas.disclaimer")}</p>
      {creating && <NewDiseaseModal open onClose={() => setCreating(false)} organs={organs.data} defaultOrgan={organ} />}
    </div>
  );
}

export function AtlasDisease() {
  const { slug } = useParams();
  const { t, L } = useI18n();
  const { can } = useAuth();
  const disease = useAsync(() => api(`/atlas/diseases/${slug}`), [slug]);
  const images = useAsync(() => api(`/images?disease=${slug}`), [slug]);
  const [open, setOpen] = useState(() => new Set(["definition", "gross", "microscopic", "ihc"]));
  const [editing, setEditing] = useState(false);
  const organs = useAsync(() => (can("atlas.write") ? api("/atlas/organs") : Promise.resolve([])), []);

  if (disease.loading) return <Loading />;
  if (disease.error) return <ErrorBox error={disease.error} />;
  const d = disease.data;
  const toggle = (k) => setOpen((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });

  return (
    <div className="fade-in">
      <Link to={`/atlas?organ=${d.organ.slug}`} className="mb-3 inline-flex items-center gap-1 text-sm font-medium text-muted hover:text-fg">← {d.organ.icon} {L(d.organ.name)}</Link>
      <Card className="mb-4 p-5">
        <div className="flex items-start justify-between gap-2">
          <Badge color="teal">{L(d.organ.name)}{d.icd10 && ` • ${d.icd10}`}</Badge>
          {can("atlas.write") && <Button variant="ghost" className="min-h-9 text-xs" onClick={() => setEditing(true)}><Pencil className="size-4" />{t("common.edit")}</Button>}
        </div>
        <h1 className="mt-3 text-2xl font-extrabold leading-tight">{L(d.name)}</h1>
        {d.name_en && <div className="mt-1 text-sm italic text-muted">{d.name_en}</div>}
        <div className="mt-3 text-xs text-muted">{t("atlas.updated")}: <span className="font-mono">{d.updated_at?.slice(0, 10)}</span></div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="space-y-2">
          {SECTIONS.filter((k) => d.sections[k]).map((k) => (
            <Card key={k} className="p-0">
              <button onClick={() => toggle(k)} className="flex w-full items-center justify-between px-4 py-3.5 text-left font-bold">
                {t(`atlas.sections.${k}`)}
                <ChevronRight className={cx("size-4 text-muted transition", open.has(k) && "rotate-90")} />
              </button>
              {open.has(k) && <p className="fade-in px-4 pb-4 text-sm leading-relaxed text-fg/85">{L(d.sections[k])}</p>}
            </Card>
          ))}
          {d.refs && <p className="whitespace-pre-line px-1 pt-2 text-xs text-muted">{t("atlas.refs")}: {d.refs}</p>}
        </div>

        <aside className="space-y-4">
          {d.markers?.length > 0 && (
            <Card>
              <h3 className="mb-2 text-sm font-bold text-primary-ink">{t("atlas.markers")}</h3>
              <table className="w-full text-sm">
                <tbody>
                  {d.markers.map((m) => (
                    <tr key={m.name} className="border-b border-line last:border-0">
                      <td className="py-2 font-mono font-medium">{m.name}</td>
                      <td className={cx("py-2 text-right font-semibold", resultColor(L(m.result)))}>{L(m.result)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
          <Card>
            <h3 className="mb-3 text-sm font-bold text-primary-ink">{t("atlas.gallery")}</h3>
            {images.data && (
              <Gallery images={images.data} setImages={images.setData} target={{ disease: slug }}
                canUpload={can("atlas.write")} canAnnotate={can("atlas.write")} />
            )}
          </Card>
        </aside>
      </div>
      {editing && (
        <NewDiseaseModal open initial={d} organs={organs.data} onClose={() => setEditing(false)} onSaved={(x) => disease.setData(x)} />
      )}
    </div>
  );
}
