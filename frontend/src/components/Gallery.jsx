import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ImagePlus, MapPin, Minus, Plus, Trash2, Upload } from "lucide-react";
import { api } from "../lib/api";
import { useI18n } from "../lib/i18n";
import { AuthImage, Button, Empty, Field, Input, KindLabel, Modal, Select, StainLabel, Textarea, cx } from "./ui";
import { useToast } from "./toast";

/** Numbered pins over an image; coordinates are 0..1 fractions so they survive any size. */
export function Pins({ pins, active, onSelect, small }) {
  const { L } = useI18n();
  return pins.map((p, i) => (
    <button
      key={i}
      type="button"
      onClick={(e) => { if (onSelect) { e.stopPropagation(); onSelect(i); } }}
      title={L(p.label)}
      className={cx(
        "absolute grid -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-[3px] bg-white font-bold text-slate-900 shadow-md transition",
        small ? "size-7 text-xs" : "size-8 text-sm",
        active === i ? "scale-125 border-purple-500" : "border-primary",
      )}
      style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%` }}
    >
      {i + 1}
    </button>
  ));
}

/** Image with the kind/stain labels in the corner, as on the atlas and gallery cards. */
export function LabeledImage({ img, className, pins, compact }) {
  return (
    <div className={cx("relative overflow-hidden bg-surface-2", className)}>
      <AuthImage src={img.url} className="absolute inset-0 size-full object-cover" />
      <div className="absolute inset-x-2.5 top-2.5 flex gap-1.5 overflow-hidden">
        <KindLabel kind={img.kind} />
        {/* small previews on phones only have room for the kind label */}
        <span className={cx("min-w-0 truncate", compact && "hidden sm:block")}><StainLabel>{img.stain}</StainLabel></span>
      </div>
      {pins && <Pins pins={img.pins || []} small />}
    </div>
  );
}

export function Lightbox({ image, onClose, editable, onSaved }) {
  const { t, L } = useI18n();
  const toast = useToast();
  const [zoom, setZoom] = useState(1);
  const [pins, setPins] = useState(image.pins || []);
  const [active, setActive] = useState(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const boxRef = useRef(null);

  const addPin = (e) => {
    if (!editing) return;
    const rect = boxRef.current.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    const y = Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height));
    setPins((ps) => [...ps, { x: +x.toFixed(4), y: +y.toFixed(4), label: { uz: "", ru: "" } }]);
    setActive(pins.length);
  };

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api(`/images/${image.id}/pins`, { method: "PUT", body: { pins } });
      onSaved?.({ ...image, ...updated });
      setEditing(false);
      toast(t("common.saved"));
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setSaving(false);
    }
  };

  const setLabel = (i, lang, value) => setPins((ps) => ps.map((q, j) => (j === i ? { ...q, label: { ...q.label, [lang]: value } } : q)));

  return (
    <Modal open onClose={onClose} title={L(image.caption) || image.stain || `#${image.id}`} wide>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <KindLabel kind={image.kind} />
        <StainLabel>{image.stain}</StainLabel>
        <div className="ml-auto flex items-center gap-1">
          <Button variant="ghost" className="min-h-9 px-2" onClick={() => setZoom((z) => Math.max(1, z - 0.5))} aria-label="zoom out"><Minus className="size-4" /></Button>
          <span className="w-12 text-center font-mono text-xs text-muted">{zoom.toFixed(1)}×</span>
          <Button variant="ghost" className="min-h-9 px-2" onClick={() => setZoom((z) => Math.min(5, z + 0.5))} aria-label="zoom in"><Plus className="size-4" /></Button>
        </div>
      </div>
      <div className="max-h-[60vh] overflow-auto rounded-2xl border border-line bg-surface-2">
        <div ref={boxRef} className={cx("relative mx-auto", editing && "cursor-crosshair")} style={{ width: `${zoom * 100}%` }} onClick={addPin}>
          <AuthImage src={image.url} className="block w-full select-none" draggable={false} />
          <Pins pins={pins} active={active} onSelect={setActive} />
        </div>
      </div>
      {editing && <p className="mt-2 text-xs font-medium text-purple-600 dark:text-purple-300">{t("img.addPin")}</p>}
      {L(image.description) && <p className="mt-3 text-sm text-muted">{L(image.description)}</p>}
      {pins.length > 0 && (
        <ol className="mt-3 space-y-1.5">
          {pins.map((p, i) => (
            <li key={i} onClick={() => setActive(i)} className={cx("flex items-center gap-2 rounded-xl p-2", active === i && "bg-surface-2")}>
              <span className="grid size-7 shrink-0 place-items-center rounded-full border-[3px] border-primary bg-white text-xs font-bold text-slate-900">{i + 1}</span>
              {editing ? (
                <>
                  <Input placeholder="UZ" value={p.label.uz || ""} onChange={(e) => setLabel(i, "uz", e.target.value)} />
                  <Input placeholder="RU" value={p.label.ru || ""} onChange={(e) => setLabel(i, "ru", e.target.value)} />
                  <button className="p-2 text-rose-500" onClick={() => setPins((ps) => ps.filter((_, j) => j !== i))} aria-label="remove"><Trash2 className="size-4" /></button>
                </>
              ) : (
                <span className="text-sm">{L(p.label) || "—"}</span>
              )}
            </li>
          ))}
        </ol>
      )}
      {image.credit && <p className="mt-3 text-xs text-muted">© {image.credit}</p>}
      {editable && (
        <div className="mt-4 flex justify-end gap-2">
          {editing ? (
            <>
              <Button variant="ghost" onClick={() => { setPins(image.pins || []); setEditing(false); }}>{t("common.cancel")}</Button>
              <Button onClick={save} loading={saving}>{t("common.save")}</Button>
            </>
          ) : (
            <Button variant="smart" onClick={() => setEditing(true)}><MapPin className="size-4" />{t("img.pins")}</Button>
          )}
        </div>
      )}
    </Modal>
  );
}

export function UploadModal({ open, onClose, target, onUploaded }) {
  const { t } = useI18n();
  const toast = useToast();
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    if (target?.disease) form.set("disease_slug", target.disease);
    if (target?.biopsy) form.set("biopsy_code", target.biopsy);
    setBusy(true);
    try {
      onUploaded(await api("/upload-image", { method: "POST", form }));
      onClose();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={t("cases.uploadImage")}>
      <form onSubmit={submit} className="space-y-3">
        <Field label={t("img.file")}><Input type="file" name="file" accept="image/jpeg,image/png,image/webp" required /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("img.kind")}>
            <Select name="kind" defaultValue="micro">
              {["macro", "micro", "ihc"].map((k) => <option key={k} value={k}>{t(`img.${k}`)}</option>)}
            </Select>
          </Field>
          <Field label={t("img.stain")}><Input name="stain" placeholder="H&E ×200, IHC DAB ×400…" /></Field>
        </div>
        <Field label={t("img.captionUz")}><Input name="caption_uz" /></Field>
        <Field label={t("img.captionRu")}><Input name="caption_ru" /></Field>
        <Field label={t("img.descUz")}><Textarea rows={2} name="description_uz" /></Field>
        <Field label={t("img.descRu")}><Textarea rows={2} name="description_ru" /></Field>
        <Field label={t("img.credit")}><Input name="credit" placeholder="Dr. …, CC BY 4.0" /></Field>
        <Button type="submit" loading={busy} className="w-full"><Upload className="size-4" />{t("cases.uploadImage")}</Button>
      </form>
    </Modal>
  );
}

/** Card used by the gallery page: image with pins, disease name, title, description. */
export function ImageCard({ img, onOpen }) {
  const { L } = useI18n();
  return (
    // A div with button semantics: the card contains a real link to the disease, and links can't nest in <button>.
    <div
      role="button"
      tabIndex={0}
      onClick={() => onOpen(img)}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onOpen(img))}
      className="group cursor-pointer overflow-hidden rounded-2xl border border-line bg-surface text-left shadow-sm transition hover:border-primary/40 hover:shadow-md focus-visible:outline-2 focus-visible:outline-primary"
    >
      <LabeledImage img={img} pins className="aspect-[4/3] w-full" />
      <div className="space-y-1 p-4">
        {img.disease && (
          <Link to={`/atlas/disease/${img.disease.slug}`} onClick={(e) => e.stopPropagation()} className="block text-xs font-bold uppercase leading-snug tracking-wide text-primary-ink hover:underline">
            {L(img.disease.name)}
          </Link>
        )}
        <div className="font-bold leading-snug">{L(img.caption) || img.stain}</div>
        {L(img.description) && <p className="line-clamp-2 text-sm text-muted">{L(img.description)}</p>}
      </div>
    </div>
  );
}

/** Compact grid used inside disease and case pages. */
export default function Gallery({ images, setImages, target, canUpload, canAnnotate }) {
  const { t, L } = useI18n();
  const [open, setOpen] = useState(null);
  const [uploading, setUploading] = useState(false);

  return (
    <div>
      {images.length === 0 ? (
        <Empty icon={ImagePlus}>{t("atlas.noImages")}</Empty>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {images.map((img) => (
            <button key={img.id} onClick={() => setOpen(img)} className="overflow-hidden rounded-xl border border-line text-left transition hover:border-primary/40">
              <LabeledImage img={img} pins className="aspect-[4/3] w-full" />
              <div className="line-clamp-1 px-2 py-1.5 text-xs font-medium">{L(img.caption) || img.stain}</div>
            </button>
          ))}
        </div>
      )}
      {canUpload && <Button variant="ghost" className="mt-3" onClick={() => setUploading(true)}><ImagePlus className="size-4" />{t("cases.uploadImage")}</Button>}
      <UploadModal open={uploading} onClose={() => setUploading(false)} target={target} onUploaded={(img) => setImages((xs) => [img, ...xs])} />
      {open && (
        <Lightbox image={open} editable={canAnnotate} onClose={() => setOpen(null)}
          onSaved={(img) => { setImages((xs) => xs.map((x) => (x.id === img.id ? img : x))); setOpen(img); }} />
      )}
    </div>
  );
}
