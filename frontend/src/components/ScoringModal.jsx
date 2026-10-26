import { useMemo, useState } from "react";
import { Calculator } from "lucide-react";
import { api } from "../lib/api";
import { useI18n } from "../lib/i18n";
import { useToast } from "./toast";
import { Badge, Button, Card, Field, Input, Modal, Select, cx } from "./ui";

// Mirrors backend/app/services/scoring.py for an instant preview; the server result is what gets stored.
export function allredPS(p) {
  if (p <= 0) return 0;
  if (p < 1) return 1;
  if (p <= 10) return 2;
  if (p <= 33) return 3;
  if (p <= 66) return 4;
  return 5;
}

export function allred(percent, intensity) {
  const ps = allredPS(percent);
  const total = ps ? ps + intensity : 0;
  const category = percent < 1 || intensity === 0 ? "negative" : percent <= 10 ? "low_positive" : "positive";
  return { ps, total, category };
}

const PATTERN_SCORE = {
  none: 0, faint_incomplete_le10: 0, faint_incomplete_gt10: 1,
  weak_moderate_complete: 2, intense_complete_le10: 2, intense_complete_gt10: 3,
};

export function her2Status(pattern, ish) {
  const score = PATTERN_SCORE[pattern];
  if (score === 3) return { score, status: "positive" };
  if (score === 2) return { score, status: ish === "none" ? "equivocal" : ish === "amp" ? "positive" : "low" };
  if (score === 1) return { score, status: "low" };
  return { score, status: pattern === "faint_incomplete_le10" ? "ultralow" : "zero" };
}

export function subtype({ er, pr, her2, ki67, cutoff }) {
  if (her2 === "equivocal") return "pending_her2";
  const hr = er >= 1 || pr >= 1;
  const h = her2 === "positive";
  const high = ki67 >= cutoff;
  if (hr && h) return "luminal_b_her2_pos";
  if (hr) return er >= 1 && pr >= 20 && !high ? "luminal_a" : "luminal_b_her2_neg";
  if (h) return "her2_enriched";
  return "triple_negative";
}

const CAT_COLOR = { positive: "emerald", low_positive: "amber", negative: "rose" };
const HER2_COLOR = { positive: "emerald", equivocal: "amber", low: "indigo", ultralow: "slate", zero: "slate" };

function AllredBlock({ label, value, onChange }) {
  const { t } = useI18n();
  const r = allred(value.percent, value.intensity);
  return (
    <Card className="bg-surface-2">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono font-semibold">{label}</span>
        <Badge color={CAT_COLOR[r.category]}>{t(`scoring.cat.${r.category}`)}</Badge>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label={t("scoring.percent")}>
          <Input type="number" min={0} max={100} step="0.5" inputMode="decimal" value={value.percent}
            onChange={(e) => onChange({ ...value, percent: Math.min(100, Math.max(0, Number(e.target.value) || 0)) })} />
        </Field>
        <Field label={t("scoring.intensity")}>
          <Select value={value.intensity} onChange={(e) => onChange({ ...value, intensity: Number(e.target.value) })}>
            {t("scoring.int").map((label, i) => <option key={i} value={i}>{label}</option>)}
          </Select>
        </Field>
      </div>
      <div className="mt-3 flex gap-4 font-mono text-sm">
        <span className="text-muted">PS <b className="text-fg">{r.ps}</b></span>
        <span className="text-muted">IS <b className="text-fg">{value.intensity}</b></span>
        <span className="ml-auto text-muted">{t("scoring.total")} <b className="text-lg text-primary-ink">{r.total}</b>/8</span>
      </div>
    </Card>
  );
}

export function ScoringSummary({ result }) {
  const { t } = useI18n();
  if (!result) return null;
  return (
    <div className="flex flex-wrap gap-2 font-mono text-xs">
      {result.er && <Badge color={CAT_COLOR[result.er.category]}>ER {result.er.percent}% · Allred {result.er.total}</Badge>}
      {result.pr && <Badge color={CAT_COLOR[result.pr.category]}>PR {result.pr.percent}% · Allred {result.pr.total}</Badge>}
      {result.her2 && <Badge color={HER2_COLOR[result.her2.status]}>HER2 {result.her2.label} · {t(`scoring.her2Status.${result.her2.status}`)}</Badge>}
      {result.ki67 && <Badge color="indigo">Ki-67 {result.ki67.percent}%</Badge>}
      {result.subtype && <Badge color="purple">{t(`scoring.subtypes.${result.subtype}`)}</Badge>}
    </div>
  );
}

export default function ScoringModal({ open, onClose, code, initial, onSaved }) {
  const { t } = useI18n();
  const toast = useToast();
  const [er, setEr] = useState({ percent: initial?.er?.percent ?? 0, intensity: initial?.er?.intensity_score ?? 0 });
  const [pr, setPr] = useState({ percent: initial?.pr?.percent ?? 0, intensity: initial?.pr?.intensity_score ?? 0 });
  const [pattern, setPattern] = useState("none");
  const [ish, setIsh] = useState("none");
  const [ki67, setKi67] = useState(initial?.ki67?.percent ?? 0);
  const [cutoff, setCutoff] = useState(initial?.ki67?.cutoff ?? 20);
  const [busy, setBusy] = useState(false);

  const h = her2Status(pattern, ish);
  const sub = useMemo(() => subtype({
    er: er.intensity ? er.percent : 0, pr: pr.intensity ? pr.percent : 0, her2: h.status, ki67, cutoff,
  }), [er, pr, h.status, ki67, cutoff]);

  const save = async () => {
    setBusy(true);
    try {
      const body = {
        er, pr, ki67: Number(ki67), ki67_cutoff: Number(cutoff),
        her2: { pattern, ish_amplified: h.score === 2 && ish !== "none" ? ish === "amp" : null },
      };
      onSaved(await api(`/biopsies/${code}/scoring`, { method: "PUT", body }));
      toast(t("common.saved"));
      onClose();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={<span className="flex items-center gap-2"><Calculator className="size-5 text-indigo-600 dark:text-indigo-400" />{t("scoring.title")}</span>} wide>
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">{t("scoring.allred")}</h3>
        <div className="grid gap-3 md:grid-cols-2">
          <AllredBlock label="ER" value={er} onChange={setEr} />
          <AllredBlock label="PR" value={pr} onChange={setPr} />
        </div>

        <h3 className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">{t("scoring.her2")}</h3>
        <Card className="bg-surface-2">
          <div className="grid gap-3 md:grid-cols-[1fr_200px]">
            <Field label={t("scoring.pattern")}>
              <Select value={pattern} onChange={(e) => setPattern(e.target.value)}>
                {Object.keys(PATTERN_SCORE).map((p) => <option key={p} value={p}>{t(`scoring.patterns.${p}`)}</option>)}
              </Select>
            </Field>
            <Field label={t("scoring.ish")}>
              <Select value={ish} onChange={(e) => setIsh(e.target.value)} disabled={h.score !== 2}>
                {["none", "amp", "noamp"].map((o) => <option key={o} value={o}>{t(`scoring.ishOpt.${o}`)}</option>)}
              </Select>
            </Field>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <span className="font-mono text-2xl font-bold text-primary-ink">{h.score ? `${h.score}+` : "0"}</span>
            <Badge color={HER2_COLOR[h.status]}>{t(`scoring.her2Status.${h.status}`)}</Badge>
          </div>
        </Card>

        <h3 className="text-sm font-semibold text-indigo-600 dark:text-indigo-300">{t("scoring.ki67")}</h3>
        <Card className="bg-surface-2">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Ki-67, %">
              <Input type="number" min={0} max={100} inputMode="decimal" value={ki67} onChange={(e) => setKi67(Math.min(100, Math.max(0, Number(e.target.value) || 0)))} />
            </Field>
            <Field label={t("scoring.cutoff")}>
              <Input type="number" min={1} max={99} inputMode="decimal" value={cutoff} onChange={(e) => setCutoff(Number(e.target.value) || 20)} />
            </Field>
          </div>
          <input type="range" min={0} max={100} value={ki67} onChange={(e) => setKi67(Number(e.target.value))} className="mt-3 w-full accent-teal-600" aria-label="Ki-67" />
          <div className={cx("mt-1 text-sm font-medium", ki67 >= cutoff ? "text-amber-600 dark:text-amber-300" : "text-primary-ink")}>
            {ki67 >= cutoff ? t("scoring.high") : t("scoring.low")}
          </div>
        </Card>

        <div className="rounded-2xl border border-purple-200 dark:border-purple-500/30 bg-purple-50 dark:bg-purple-500/10 p-4">
          <div className="text-xs uppercase tracking-wide text-purple-700 dark:text-purple-300">{t("scoring.subtype")}</div>
          <div className="mt-1 text-xl font-bold">{t(`scoring.subtypes.${sub}`)}</div>
        </div>
        <p className="text-xs text-muted">{t("scoring.note")}</p>
        <Button onClick={save} loading={busy} className="w-full">{t("scoring.save")}</Button>
      </div>
    </Modal>
  );
}
