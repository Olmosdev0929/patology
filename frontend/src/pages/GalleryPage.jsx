import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Image as ImageIcon } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import { ImageCard, Lightbox } from "../components/Gallery";
import { Chips, Empty, ErrorBox, Loading, useAsync } from "../components/ui";

export default function GalleryPage() {
  const { t } = useI18n();
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const kind = params.get("kind") || "";
  const all = useAsync(() => api("/images"), []);
  const [open, setOpen] = useState(null);

  const items = (all.data || []).filter((i) => !kind || i.kind === kind);
  const count = (k) => (all.data || []).filter((i) => i.kind === k).length;

  return (
    <div className="fade-in">
      <h1 className="text-lg font-extrabold">{t("gallery.title", { n: all.data?.length ?? "…" })}</h1>
      <p className="mb-4 text-sm text-muted">{t("gallery.subtitle")}</p>
      <Chips
        value={kind}
        onChange={(v) => setParams(v ? { kind: v } : {})}
        items={[
          { value: "", label: t("common.all") },
          { value: "macro", label: t("img.macro"), icon: "🫀", count: count("macro") },
          { value: "micro", label: t("img.micro"), icon: "🔬", count: count("micro") },
          { value: "ihc", label: t("img.ihc"), icon: "🧬", count: count("ihc") },
        ]}
      />
      {all.loading ? <Loading /> : all.error ? <ErrorBox error={all.error} onRetry={all.reload} /> : items.length === 0 ? (
        <Empty icon={ImageIcon}>{t("atlas.noImages")}</Empty>
      ) : (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          {items.map((img) => <ImageCard key={img.id} img={img} onOpen={setOpen} />)}
        </div>
      )}
      {open && (
        <Lightbox image={open} editable={can("atlas.write")} onClose={() => setOpen(null)}
          onSaved={(img) => { all.setData((xs) => xs.map((x) => (x.id === img.id ? { ...x, ...img } : x))); setOpen(img); }} />
      )}
    </div>
  );
}
