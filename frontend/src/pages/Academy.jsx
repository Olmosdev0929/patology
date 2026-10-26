import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { BookOpen, Brain, CheckCircle2, ChevronRight, Eye, EyeOff, Layers, Pause, Play, Plus, Trash2, Upload, Volume2, XCircle } from "lucide-react";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import { useI18n } from "../lib/i18n";
import { confirmDialog, haptic, openExternal } from "../lib/telegram";
import { forgetUpload, formatBytes, uploadFile } from "../lib/upload";
import { useToast } from "../components/toast";
import { Badge, Button, Card, Empty, Field, Input, Loading, Modal, Segmented, Textarea, cx, useAsync } from "../components/ui";

// ---------------------------------------------------------------- speech

function speak(text, onEnd) {
  const synth = window.speechSynthesis;
  if (!synth) return onEnd?.();
  synth.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  u.rate = 0.92;
  const voice = synth.getVoices().find((v) => v.lang?.startsWith("en"));
  if (voice) u.voice = voice;
  u.onend = () => onEnd?.();
  u.onerror = () => onEnd?.();
  synth.speak(u);
}

// ---------------------------------------------------------------- reader

function Reader({ bookId, onBack }) {
  const { t, L, lang } = useI18n();
  const toast = useToast();
  const book = useAsync(() => (bookId ? api(`/books/${bookId}?limit=200`) : Promise.resolve(null)), [bookId]);
  const [active, setActive] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [hide, setHide] = useState(false);
  const [both, setBoth] = useState(false);
  const [term, setTerm] = useState(null);
  const playRef = useRef(false);
  const rowRefs = useRef({});

  useEffect(() => () => { playRef.current = false; window.speechSynthesis?.cancel(); }, []);

  const sentences = book.data?.sentences || [];

  const playFrom = (index) => {
    if (index >= sentences.length || !playRef.current) { setPlaying(false); playRef.current = false; return; }
    setActive(sentences[index].id);
    rowRefs.current[sentences[index].id]?.scrollIntoView({ behavior: "smooth", block: "center" });
    speak(sentences[index].en, () => playFrom(index + 1));
  };

  const togglePlay = () => {
    if (playing) {
      playRef.current = false;
      window.speechSynthesis?.cancel();
      setPlaying(false);
      return;
    }
    playRef.current = true;
    setPlaying(true);
    const start = Math.max(0, sentences.findIndex((s) => s.id === active));
    playFrom(start);
  };

  const toCard = async (body) => {
    try {
      await api("/anki", { method: "POST", body: { deck: book.data?.title?.slice(0, 100) || "Reader", ...body } });
      haptic("success");
      toast(t("academy.cardAdded"));
    } catch (e) {
      toast(e.message, "error");
    }
  };

  if (book.loading) return <Loading />;
  if (!book.data) return <Empty icon={BookOpen}>{t("common.empty")}</Empty>;

  let chapter = null;
  return (
    <div>
      <button onClick={onBack} className="mb-3 text-sm font-medium text-muted hover:text-fg">← {t("academy.backToBooks")}</button>
      {book.data.category && <Badge color="sky">{book.data.category}</Badge>}
      <h1 className="mb-1 mt-2 text-xl font-extrabold leading-tight">{book.data.title}</h1>
      {book.data.author && <p className="mb-4 text-sm text-muted">{book.data.author}</p>}
      <div className="mb-4 flex flex-wrap items-end gap-2">
        <Button variant="smart" onClick={togglePlay}>{playing ? <Pause className="size-4" /> : <Play className="size-4" />}{t("academy.listen")}</Button>
        <Button variant="ghost" onClick={() => setHide((x) => !x)} aria-pressed={hide}>{hide ? <EyeOff className="size-4" /> : <Eye className="size-4" />}{t("academy.showTranslation")}</Button>
        <Button variant={both ? "smart" : "ghost"} onClick={() => setBoth((x) => !x)} className="font-mono">UZ+RU</Button>
      </div>
      {book.data && <p className="mb-3 text-xs text-muted">{book.data.source} · {t("academy.license")}: {book.data.license}</p>}

      <div className="space-y-2">
        {sentences.map((s) => {
          const head = s.chapter !== chapter ? (chapter = s.chapter) : null;
          const isActive = active === s.id;
          return (
            <div key={s.id}>
              {head && <h3 className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">{head}</h3>}
              <div
                ref={(el) => { rowRefs.current[s.id] = el; }}
                onClick={() => setActive(s.id)}
                className={cx("grid gap-3 rounded-2xl border p-4 transition md:grid-cols-2", isActive ? "border-purple-400 dark:border-purple-500/60 bg-purple-50 dark:bg-purple-500/10 shadow-[0_0_24px_-10px] shadow-purple-500/60" : "border-line bg-surface")}
              >
                <div>
                  <div className="mb-1 flex items-center gap-2 font-mono text-[10px] text-muted">EN · #{s.position + 1}</div>
                  <p className="leading-relaxed text-fg">{s.en}</p>
                </div>
                <div className={cx("transition", hide && !isActive && "blur-sm select-none")}>
                  {(both ? ["uz", "ru"] : [lang]).map((lng) => (
                    <div key={lng} className="mb-2 last:mb-0">
                      <div className="mb-1 font-mono text-[10px] uppercase text-muted">{lng}</div>
                      <p className="leading-relaxed text-fg/85">{s[lng]}</p>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap items-center gap-1.5 md:col-span-2">
                  {s.terms.map((tm) => (
                    <button key={tm.term} onClick={(e) => { e.stopPropagation(); setTerm(tm); }}
                      className="rounded-lg border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10 px-2 py-1 text-xs text-indigo-600 dark:text-indigo-300 hover:bg-indigo-500/20">
                      {tm.term}
                    </button>
                  ))}
                  <span className="ml-auto flex gap-1">
                    <Button variant="ghost" className="min-h-9 px-3 text-xs" onClick={(e) => { e.stopPropagation(); setActive(s.id); speak(s.en); }}><Volume2 className="size-4" /></Button>
                    <Button variant="smart" className="min-h-9 px-3 text-xs" onClick={(e) => { e.stopPropagation(); toCard({ sentence_id: s.id }); }}><Layers className="size-4" />{t("academy.toCard")}</Button>
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <Modal open={Boolean(term)} onClose={() => setTerm(null)} title={term?.term}>
        {term && (
          <div className="space-y-3">
            <Button variant="ghost" onClick={() => speak(term.term)}><Volume2 className="size-4" />{t("academy.listen")}</Button>
            <div className="rounded-xl bg-surface-2 p-3"><span className="font-mono text-xs text-muted">UZ</span><p>{term.uz}</p></div>
            <div className="rounded-xl bg-surface-2 p-3"><span className="font-mono text-xs text-muted">RU</span><p>{term.ru}</p></div>
            <Button variant="smart" className="w-full" onClick={() => {
              toCard({ front_en: term.term, front_uz: term.term, front_ru: term.term, back_uz: term.uz, back_ru: term.ru });
              setTerm(null);
            }}><Layers className="size-4" />{t("academy.toCard")}</Button>
          </div>
        )}
      </Modal>
    </div>
  );
}

// ---------------------------------------------------------------- anki

// Mirrors backend SM-2 to preview the next interval on each button.
const GRADES = { again: 1, hard: 3, good: 4, easy: 5 };
function previewInterval(card, answer) {
  const q = GRADES[answer];
  const ef = Math.max(1.3, card.easiness + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)));
  if (q < 3) return 1;
  let i = card.reps === 0 ? 1 : card.reps === 1 ? 6 : Math.round(card.interval * ef);
  if (answer === "easy") i = Math.max(i, Math.round(i * 1.3));
  return Math.max(1, i);
}

function NewCardModal({ open, onClose, onCreated }) {
  const { t } = useI18n();
  const toast = useToast();
  const [f, setF] = useState({ deck: "General", front_uz: "", front_ru: "", back_uz: "", back_ru: "" });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    try {
      onCreated(await api("/anki", { method: "POST", body: f }));
      setF({ ...f, front_uz: "", front_ru: "", back_uz: "", back_ru: "" });
      onClose();
    } catch (err) {
      toast(err.message, "error");
    }
  };
  return (
    <Modal open={open} onClose={onClose} title={t("academy.newCard")}>
      <form onSubmit={submit} className="space-y-3">
        <Field label={t("academy.deck")}><Input value={f.deck} onChange={set("deck")} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={`${t("academy.front")} · UZ`}><Textarea rows={2} value={f.front_uz} onChange={set("front_uz")} /></Field>
          <Field label={`${t("academy.front")} · RU`}><Textarea rows={2} value={f.front_ru} onChange={set("front_ru")} /></Field>
          <Field label={`${t("academy.backSide")} · UZ`}><Textarea rows={2} value={f.back_uz} onChange={set("back_uz")} /></Field>
          <Field label={`${t("academy.backSide")} · RU`}><Textarea rows={2} value={f.back_ru} onChange={set("back_ru")} /></Field>
        </div>
        <Button type="submit" className="w-full" disabled={!f.front_uz && !f.front_ru}><Plus className="size-4" />{t("common.add")}</Button>
      </form>
    </Modal>
  );
}

function Anki() {
  const { t, lang } = useI18n();
  const toast = useToast();
  const stats = useAsync(() => api("/anki/stats"), []);
  const due = useAsync(() => api("/anki?due=true"), []);
  const [flipped, setFlipped] = useState(false);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const card = due.data?.[0];

  const answer = async (a) => {
    setBusy(true);
    try {
      await api(`/anki/${card.id}/review`, { method: "POST", body: { answer: a } });
      haptic(a === "again" ? "warning" : "light");
      setFlipped(false);
      // "Again" cards come back tomorrow per SM-2; drop the reviewed card from today's queue.
      due.setData(due.data.slice(1));
      stats.reload();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const front = card && (card.front_en || card[`front_${lang}`] || card.front_uz || card.front_ru);
  const back = card && (card[`back_${lang}`] || card.back_uz || card.back_ru);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Badge color="purple">{t("academy.due", { n: stats.data?.due ?? "…" })}</Badge>
        <Badge>{t("academy.total", { n: stats.data?.total ?? "…" })}</Badge>
        <Badge color="emerald">{t("academy.mature", { n: stats.data?.mature ?? "…" })}</Badge>
        <Button variant="ghost" className="ml-auto min-h-9 text-xs" onClick={() => setCreating(true)}><Plus className="size-4" />{t("academy.newCard")}</Button>
      </div>

      {due.loading ? <Loading /> : !card ? <Empty icon={Brain}>{t("academy.noDue")}</Empty> : (
        <div className="mx-auto max-w-xl">
          <button onClick={() => setFlipped(true)} className="block w-full text-left">
            <Card className="min-h-64 border-purple-200 dark:border-purple-500/30 bg-gradient-to-br from-surface to-purple-50 dark:to-purple-950/40 p-6">
              <div className="mb-3 flex items-center gap-2 text-xs text-muted">
                <span className="font-mono">{card.deck}</span>
                <span className="ml-auto font-mono">EF {card.easiness.toFixed(2)} · {card.interval}d</span>
              </div>
              <p className="text-lg leading-relaxed">{front}</p>
              {card.front_en && (
                <button onClick={(e) => { e.stopPropagation(); speak(card.front_en); }} className="mt-2 text-purple-700 dark:text-purple-300" aria-label={t("academy.listen")}>
                  <Volume2 className="size-5" />
                </button>
              )}
              {flipped && (
                <div className="fade-in mt-5 border-t border-line pt-5">
                  <p className="leading-relaxed text-emerald-700 dark:text-emerald-300">{back || "—"}</p>
                </div>
              )}
            </Card>
          </button>
          {!flipped ? (
            <Button variant="smart" className="mt-4 w-full" onClick={() => setFlipped(true)}>{t("academy.showAnswer")}</Button>
          ) : (
            <div className="mt-4 grid grid-cols-4 gap-2">
              {[["again", "danger"], ["hard", "ghost"], ["good", "primary"], ["easy", "smart"]].map(([a, v]) => (
                <Button key={a} variant={v} className="flex-col gap-0 px-1 text-xs" disabled={busy} onClick={() => answer(a)}>
                  <span>{t(`academy.${a}`)}</span>
                  <span className="font-mono text-[10px] opacity-75">{previewInterval(card, a)}d</span>
                </Button>
              ))}
            </div>
          )}
        </div>
      )}
      <NewCardModal open={creating} onClose={() => setCreating(false)} onCreated={(c) => { due.setData([...(due.data || []), c]); stats.reload(); }} />
    </div>
  );
}

// ---------------------------------------------------------------- quiz

function Quiz() {
  const { t, L } = useI18n();
  const toast = useToast();
  const quiz = useAsync(() => api("/quiz/daily"), []);
  const [results, setResults] = useState({});
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!quiz.data) return;
    const prior = {};
    for (const [id, a] of Object.entries(quiz.data.answered || {})) prior[id] = { chosen: a.chosen, correct: a.correct };
    setResults(prior);
    const firstOpen = quiz.data.questions.findIndex((q) => !prior[q.id]);
    setIndex(firstOpen === -1 ? quiz.data.questions.length : firstOpen);
  }, [quiz.data]);

  const questions = quiz.data?.questions || [];
  const correctCount = useMemo(() => Object.values(results).filter((r) => r.correct).length, [results]);

  if (quiz.loading) return <Loading />;
  if (!questions.length) return <Empty>{t("common.empty")}</Empty>;

  if (index >= questions.length) {
    return (
      <Card className="mx-auto max-w-xl text-center">
        <CheckCircle2 className="mx-auto size-10 text-primary-ink" />
        <p className="mt-2 font-semibold">{t("academy.done")}</p>
        <p className="mt-1 font-mono text-2xl text-primary-ink">{t("academy.score", { c: correctCount, n: questions.length })}</p>
        <Button variant="ghost" className="mt-4" onClick={() => setIndex(0)}>{t("common.back")}</Button>
      </Card>
    );
  }

  const q = questions[index];
  const r = results[q.id];

  const choose = async (i) => {
    if (r) return;
    try {
      const res = await api(`/quiz/${q.id}/answer`, { method: "POST", body: { chosen: i } });
      haptic(res.correct ? "success" : "error");
      setResults((x) => ({ ...x, [q.id]: { chosen: i, correct: res.correct, correct_index: res.correct_index, explanation: res.explanation } }));
    } catch (e) {
      toast(e.message, "error");
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex items-center gap-1.5">
        {questions.map((x, i) => (
          <button key={x.id} onClick={() => setIndex(i)} className={cx("h-1.5 flex-1 rounded-full", results[x.id] ? (results[x.id].correct ? "bg-primary" : "bg-rose-500") : i === index ? "bg-indigo-400" : "bg-surface-2")} aria-label={`${i + 1}`} />
        ))}
      </div>
      <Card>
        <div className="mb-2 flex items-center gap-2">
          <Badge color="indigo" className="font-mono">{index + 1}/{questions.length}</Badge>
          {q.organ && <Badge>{t(`organs.${q.organ}`)}</Badge>}
        </div>
        <p className="leading-relaxed">{L(q.case_text)}</p>
        <div className="mt-4 space-y-2">
          {q.options.map((o, i) => {
            const isCorrect = r && (r.correct_index ?? (r.correct ? r.chosen : -1)) === i;
            const isWrongPick = r && r.chosen === i && !r.correct;
            return (
              <button key={i} disabled={Boolean(r)} onClick={() => choose(i)}
                className={cx("flex min-h-12 w-full items-center gap-3 rounded-xl border px-4 py-2 text-left text-sm transition",
                  isCorrect ? "border-emerald-300 dark:border-emerald-500/50 bg-emerald-50 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-200"
                    : isWrongPick ? "border-rose-300 dark:border-rose-500/50 bg-rose-50 dark:bg-rose-500/15 text-rose-800 dark:text-rose-200"
                    : "border-line bg-surface-2 hover:border-primary/50")}>
                <span className="font-mono text-xs text-muted">{String.fromCharCode(65 + i)}</span>
                <span className="flex-1">{L(o)}</span>
                {isCorrect && <CheckCircle2 className="size-5 text-primary-ink" />}
                {isWrongPick && <XCircle className="size-5 text-rose-600 dark:text-rose-400" />}
              </button>
            );
          })}
        </div>
        {r && (
          <div className="fade-in mt-4 rounded-xl border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10 p-4">
            <div className={cx("font-semibold", r.correct ? "text-primary-ink" : "text-rose-600 dark:text-rose-300")}>{r.correct ? t("academy.correct") : t("academy.wrong")}</div>
            {r.explanation && <p className="mt-1 text-sm text-fg/85"><b>{t("academy.explanation")}:</b> {L(r.explanation)}</p>}
            <Button className="mt-3 w-full" onClick={() => setIndex((x) => x + 1)}>{t("academy.next")}</Button>
          </div>
        )}
      </Card>
    </div>
  );
}

const CATEGORY_COLOR = { "Xalqaro Tasnif": "sky", "IGX Qo'llanma": "sky", "Grossing Protokol": "sky" };

function Books({ onOpen }) {
  const { t } = useI18n();
  const { can } = useAuth();
  const toast = useToast();
  const books = useAsync(() => api("/books"), []);
  const [adding, setAdding] = useState(null); // "pdf" | "text"

  // Refresh while any book is still being indexed so the status badge moves.
  useEffect(() => {
    if (!books.data?.some((b) => b.text_status === "queued" || b.text_status === "processing")) return;
    const id = setTimeout(books.reload, 4000);
    return () => clearTimeout(id);
  }, [books.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const remove = async (b) => {
    if (!(await confirmDialog(t("academy.deleteConfirm")))) return;
    try { await api(`/books/${b.id}`, { method: "DELETE" }); books.reload(); } catch (e) { toast(e.message, "error"); }
  };

  if (books.loading) return <Loading />;
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold text-muted">{t("academy.booksTitle", { n: books.data?.length || 0 })}</div>
        {can("admin") && (
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => setAdding("text")}><Plus className="size-4" />{t("academy.parallel")}</Button>
            <Button onClick={() => setAdding("pdf")}><Upload className="size-4" />{t("academy.uploadPdf")}</Button>
          </div>
        )}
      </div>
      {!books.data?.length ? <Empty icon={BookOpen}>{t("common.empty")}</Empty> : (
        <div className="grid gap-3 lg:grid-cols-2">
          {books.data.map((b) => (
            <Card key={b.id} interactive className="cursor-pointer p-5" onClick={() => onOpen(b.id)}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex flex-wrap gap-1.5">
                  {b.category && <Badge color={CATEGORY_COLOR[b.category] || "sky"}>{b.category}</Badge>}
                  {b.has_file && <Badge color="rose">{t("academy.pdf")} · {formatBytes(b.file_size)}</Badge>}
                </div>
                <span className="text-right text-xs text-muted">
                  {b.pages ? t("academy.pages", { n: b.pages }) : ""}
                  {!b.has_file && <>{b.pages ? " • " : ""}{t("academy.sentencesShort", { n: b.sentences })}</>}
                </span>
              </div>
              <h3 className="mt-3 text-lg font-bold leading-snug">{b.title}</h3>
              {b.author && <p className="mt-1 text-sm text-muted">{b.author}</p>}
              {b.has_file && b.text_status !== "ready" && (
                <p className={cx("mt-2 text-xs", b.text_status === "failed" ? "text-rose-600 dark:text-rose-300" : "text-amber-700 dark:text-amber-300")}>
                  {t(`academy.textStatus.${b.text_status}`, { done: b.text_pages_done, total: b.pages || "…" })}
                </p>
              )}
              {b.has_file && b.pages && b.progress_page ? (
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-2">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, (b.progress_page / b.pages) * 100)}%` }} />
                </div>
              ) : null}
              <div className="mt-3 flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1 text-sm font-bold text-primary-ink">
                  {b.progress_page ? t("academy.continueAt", { p: b.progress_page }) : t("academy.read", { n: b.chapters || 1 })}
                  <ChevronRight className="size-4" />
                </span>
                {can("admin") && (
                  <span className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                    {b.has_file && b.text_status === "failed" && (
                      <button className="rounded-lg px-2 py-1 text-xs text-muted hover:bg-surface-2"
                        onClick={() => api(`/books/${b.id}/reindex`, { method: "POST" }).then(books.reload)}>{t("academy.reindex")}</button>
                    )}
                    <button className="rounded-lg p-1.5 text-muted hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/10" aria-label={t("academy.deleteBook")} onClick={() => remove(b)}>
                      <Trash2 className="size-4" />
                    </button>
                  </span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
      {adding === "text" && <ImportBookModal onClose={() => setAdding(null)} onDone={books.reload} />}
      {adding === "pdf" && <UploadBookModal onClose={() => setAdding(null)} onDone={books.reload} />}
    </div>
  );
}

function UploadBookModal({ onClose, onDone }) {
  const { t } = useI18n();
  const toast = useToast();
  const health = useAsync(() => api("/health"), []);
  const [file, setFile] = useState(null);
  const [f, setF] = useState({ title: "", category: "", author: "", license: "" });
  const [state, setState] = useState("idle"); // idle | uploading | paused | finishing
  const [prog, setProg] = useState(null);
  const ctrl = useRef(null);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const maxMb = health.data?.max_book_mb || 2048;

  useEffect(() => () => ctrl.current?.abort(), []);

  const pick = (e) => {
    const chosen = e.target.files?.[0];
    if (!chosen) return;
    if (chosen.size > maxMb * 1024 * 1024) { toast(`> ${maxMb} MB`, "error"); return; }
    setFile(chosen);
    if (!f.title) setF((x) => ({ ...x, title: chosen.name.replace(/\.pdf$/i, "") }));
  };

  const start = async (e) => {
    e?.preventDefault();
    if (!file) return;
    ctrl.current = new AbortController();
    setState("uploading");
    try {
      const uploadId = await uploadFile(file, { onProgress: setProg, signal: ctrl.current.signal });
      setState("finishing");
      await api("/books/from-upload", { method: "POST", body: {
        upload_id: uploadId, title: f.title, category: f.category || null, author: f.author || null, license: f.license,
      } });
      forgetUpload(file);
      toast(t("academy.uploaded"));
      onDone();
      onClose();
    } catch (err) {
      if (err.name === "AbortError") { setState("paused"); return; }
      if (err.detail?.error === "duplicate") { forgetUpload(file); toast(t("academy.duplicate"), "error"); }
      else toast(err.message, "error");
      setState("paused");
    }
  };

  const pct = prog ? Math.floor((prog.sent / prog.total) * 100) : 0;
  const eta = prog?.speed ? Math.max(0, Math.round((prog.total - prog.sent) / prog.speed)) : null;
  const busy = state === "uploading" || state === "finishing";

  return (
    <Modal open onClose={() => { ctrl.current?.abort(); onClose(); }} title={t("academy.uploadPdf")}>
      <form onSubmit={start} className="space-y-3">
        <Field label={t("academy.chooseFile", { mb: maxMb })}>
          <Input type="file" accept="application/pdf,.pdf" onChange={pick} disabled={busy} required={!file} />
        </Field>
        {file && <p className="text-xs text-muted">{file.name} · {formatBytes(file.size)}</p>}
        <Field label="Title"><Input required value={f.title} onChange={set("title")} disabled={busy} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("academy.category")}><Input value={f.category} onChange={set("category")} placeholder="Xalqaro Tasnif" disabled={busy} /></Field>
          <Field label={t("academy.author")}><Input value={f.author} onChange={set("author")} disabled={busy} /></Field>
        </div>
        <Field label={t("academy.license")}><Input required value={f.license} onChange={set("license")} placeholder="Muassasa litsenziyasi / CC BY 4.0" disabled={busy} /></Field>
        <p className="text-xs font-semibold text-amber-700 dark:text-amber-300">{t("academy.rights")}</p>

        {state !== "idle" && (
          <div className="rounded-xl bg-surface-2 p-3">
            <div className="mb-1.5 flex justify-between text-xs font-semibold">
              <span>{state === "finishing" ? t("academy.finishing") : `${pct}%`}</span>
              {prog && state === "uploading" && (
                <span className="font-mono text-muted">
                  {t("academy.uploadingStat", { sent: formatBytes(prog.sent), total: formatBytes(prog.total), speed: formatBytes(prog.speed), eta: eta != null ? `${Math.floor(eta / 60)}:${String(eta % 60).padStart(2, "0")}` : "…" })}
                </span>
              )}
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-line" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
              <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${state === "finishing" ? 100 : pct}%` }} />
            </div>
          </div>
        )}
        <p className="text-xs text-muted">{t("academy.resumeHint")}</p>

        {/* Distinct keys: React must not morph the pause button into the submit button mid-click,
            or the same tap would immediately restart the upload. */}
        {state === "uploading" ? (
          <Button key="pause" type="button" variant="ghost" className="w-full" onClick={(e) => { e.preventDefault(); ctrl.current?.abort(); }}>
            <Pause className="size-4" />{t("academy.pause")}
          </Button>
        ) : (
          <Button key="start" type="submit" className="w-full" loading={state === "finishing"} disabled={!file}>
            <Upload className="size-4" />{state === "paused" ? t("academy.resume") : t("academy.uploadPdf")}
          </Button>
        )}
      </form>
    </Modal>
  );
}

function ImportBookModal({ onClose, onDone }) {
  const { t } = useI18n();
  const toast = useToast();
  const [f, setF] = useState({ title: "", category: "", author: "", pages: "", license: "", lines: "" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    let chapter = null;
    const sentences = [];
    for (const raw of f.lines.split("\n")) {
      const line = raw.trim();
      if (!line) continue;
      if (line.startsWith("#")) { chapter = line.replace(/^#+\s*/, ""); continue; }
      const [en, uz = "", ru = ""] = line.split("|").map((x) => x.trim());
      if (en) sentences.push({ en, uz, ru, chapter });
    }
    setBusy(true);
    try {
      await api("/books/import", { method: "POST", body: {
        title: f.title, category: f.category || null, author: f.author || null,
        pages: f.pages ? Number(f.pages) : null, license: f.license, sentences,
      } });
      onDone();
      onClose();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open onClose={onClose} title={t("academy.addBook")} wide>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Title" className="sm:col-span-2"><Input required value={f.title} onChange={set("title")} /></Field>
          <Field label={t("academy.category")}><Input value={f.category} onChange={set("category")} placeholder="IGX Qo'llanma" /></Field>
          <Field label={t("academy.author")}><Input value={f.author} onChange={set("author")} /></Field>
          <Field label="#"><Input type="number" min={1} value={f.pages} onChange={set("pages")} placeholder={t("academy.pages", { n: "…" })} /></Field>
          <Field label={t("academy.license")}><Input required value={f.license} onChange={set("license")} placeholder="CC BY 4.0 / ruxsat" /></Field>
        </div>
        <Field label={t("academy.bookLines")}>
          <Textarea rows={8} required value={f.lines} onChange={set("lines")} className="font-mono text-xs" placeholder={"# Breast\nER is a nuclear marker. | ER yadro markeri. | ER — ядерный маркер."} />
        </Field>
        <p className="text-xs text-muted">{t("academy.bookLinesHint")}</p>
        <p className="text-xs font-semibold text-amber-700 dark:text-amber-300">{t("academy.rights")}</p>
        <Button type="submit" loading={busy} className="w-full">{t("common.save")}</Button>
      </form>
    </Modal>
  );
}

function youtubeId(url) {
  const m = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{6,})/);
  return m?.[1] || null;
}

function Media({ kind }) {
  const { t, L } = useI18n();
  const { can } = useAuth();
  const toast = useToast();
  const list = useAsync(() => api(`/media?kind=${kind}`), [kind]);
  const [adding, setAdding] = useState(false);
  const [playing, setPlaying] = useState(null);
  const [f, setF] = useState({ title_uz: "", title_ru: "", url: "", author: "" });

  const add = async (e) => {
    e.preventDefault();
    try {
      const m = await api("/media", { method: "POST", body: { kind, url: f.url, author: f.author || null, title: { uz: f.title_uz, ru: f.title_ru } } });
      list.setData((xs) => [m, ...(xs || [])]);
      setAdding(false);
      setF({ title_uz: "", title_ru: "", url: "", author: "" });
    } catch (err) {
      toast(err.message, "error");
    }
  };

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold text-muted">{t(kind === "video" ? "academy.videosTitle" : "academy.slidesTitle", { n: list.data?.length || 0 })}</div>
        {can("atlas.write") && <Button onClick={() => setAdding(true)}><Plus className="size-4" />{t("academy.addMedia")}</Button>}
      </div>
      {list.loading ? <Loading /> : !list.data?.length ? <Empty icon={kind === "video" ? Play : BookOpen}>{t("academy.noMedia")}</Empty> : (
        <div className="grid gap-3 sm:grid-cols-2">
          {list.data.map((m) => {
            const yt = youtubeId(m.url);
            return (
              <Card key={m.id} className="overflow-hidden p-0">
                {kind === "video" && yt && (playing === m.id ? (
                  <iframe className="aspect-video w-full" src={`https://www.youtube-nocookie.com/embed/${yt}?autoplay=1`} title={L(m.title)} allow="autoplay; encrypted-media; picture-in-picture" allowFullScreen />
                ) : (
                  <button onClick={() => setPlaying(m.id)} className="relative block aspect-video w-full bg-slate-900">
                    <img src={`https://i.ytimg.com/vi/${yt}/hqdefault.jpg`} alt="" className="size-full object-cover opacity-90" loading="lazy" />
                    <span className="absolute inset-0 grid place-items-center"><span className="grid size-14 place-items-center rounded-full bg-white/90 text-slate-900 shadow-lg"><Play className="size-6" /></span></span>
                  </button>
                ))}
                <div className="p-4">
                  <div className="font-bold leading-snug">{L(m.title)}</div>
                  {m.author && <div className="mt-0.5 text-sm text-muted">{m.author}</div>}
                  {!(kind === "video" && yt) && (
                    <Button variant="soft" className="mt-3" onClick={() => openExternal(m.url)}>{t("academy.open")} ↗</Button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
      <Modal open={adding} onClose={() => setAdding(false)} title={t("academy.addMedia")}>
        <form onSubmit={add} className="space-y-3">
          <Field label={t("academy.mediaUrl")}><Input required type="url" pattern="https://.*" value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} /></Field>
          <Field label={t("academy.titleUz")}><Input required={!f.title_ru} value={f.title_uz} onChange={(e) => setF({ ...f, title_uz: e.target.value })} /></Field>
          <Field label={t("academy.titleRu")}><Input value={f.title_ru} onChange={(e) => setF({ ...f, title_ru: e.target.value })} /></Field>
          <Field label={t("academy.author")}><Input value={f.author} onChange={(e) => setF({ ...f, author: e.target.value })} /></Field>
          <Button type="submit" className="w-full">{t("common.save")}</Button>
        </form>
      </Modal>
    </div>
  );
}

function QuizAdmin({ onAdded }) {
  const { t } = useI18n();
  const { can } = useAuth();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const blank = { organ: "", case_uz: "", case_ru: "", options: [["", ""], ["", ""], ["", ""], ["", ""]], correct: 0, expl_uz: "", expl_ru: "" };
  const [f, setF] = useState(blank);
  if (!can("atlas.write")) return null;

  const setOpt = (i, j, v) => setF((x) => ({ ...x, options: x.options.map((o, k) => (k === i ? (j ? [o[0], v] : [v, o[1]]) : o)) }));
  const submit = async (e) => {
    e.preventDefault();
    const options = f.options.filter(([uz, ru]) => uz || ru);
    try {
      await api("/quiz", { method: "POST", body: {
        organ: f.organ || null, case_text: { uz: f.case_uz, ru: f.case_ru },
        options: options.map(([uz, ru]) => ({ uz, ru })), correct: Number(f.correct),
        explanation: { uz: f.expl_uz, ru: f.expl_ru },
      } });
      toast(t("quizAdmin.saved"));
      setF(blank);
      setOpen(false);
      onAdded?.();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  return (
    <>
      <div className="mb-3 flex justify-end">
        <Button variant="ghost" onClick={() => setOpen(true)}><Plus className="size-4" />{t("quizAdmin.add")}</Button>
      </div>
      <Modal open={open} onClose={() => setOpen(false)} title={t("quizAdmin.add")} wide>
        <form onSubmit={submit} className="space-y-3">
          <Field label={t("quizAdmin.caseUz")}><Textarea rows={3} required={!f.case_ru} value={f.case_uz} onChange={(e) => setF({ ...f, case_uz: e.target.value })} /></Field>
          <Field label={t("quizAdmin.caseRu")}><Textarea rows={3} value={f.case_ru} onChange={(e) => setF({ ...f, case_ru: e.target.value })} /></Field>
          {f.options.map(([uz, ru], i) => (
            <div key={i} className="grid grid-cols-[auto_1fr_1fr] items-center gap-2">
              <input type="radio" name="correct" checked={Number(f.correct) === i} onChange={() => setF({ ...f, correct: i })} aria-label={`${t("quizAdmin.correct")} ${i + 1}`} className="size-5 accent-teal-600" />
              <Input placeholder={`${t("quizAdmin.option")} ${String.fromCharCode(65 + i)} · UZ`} required={i < 2 && !ru} value={uz} onChange={(e) => setOpt(i, 0, e.target.value)} />
              <Input placeholder="RU" value={ru} onChange={(e) => setOpt(i, 1, e.target.value)} />
            </div>
          ))}
          <p className="text-xs text-muted">● {t("quizAdmin.correct")}</p>
          <Field label={t("quizAdmin.explUz")}><Textarea rows={2} value={f.expl_uz} onChange={(e) => setF({ ...f, expl_uz: e.target.value })} /></Field>
          <Field label={t("quizAdmin.explRu")}><Textarea rows={2} value={f.expl_ru} onChange={(e) => setF({ ...f, expl_ru: e.target.value })} /></Field>
          <Button type="submit" className="w-full">{t("common.save")}</Button>
        </form>
      </Modal>
    </>
  );
}

const PdfReader = lazy(() => import("../components/PdfReader"));

/** Opens a PDF book in the pdf.js reader, a sentence book in the parallel reader. */
function BookView({ bookId, onBack }) {
  const meta = useAsync(() => api(`/books/${bookId}?limit=1`), [bookId]);
  if (meta.loading) return <Loading />;
  if (meta.error) return <Empty>{String(meta.error.message)}</Empty>;
  if (meta.data.has_file && !meta.data.total) {
    return <Suspense fallback={<Loading />}><PdfReader book={meta.data} onBack={onBack} /></Suspense>;
  }
  return <Reader bookId={bookId} onBack={onBack} />;
}

export default function Academy() {
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "books";
  const bookId = params.get("book");
  return (
    <div className="fade-in">
      <Segmented
        value={tab}
        onChange={(v) => setParams({ tab: v })}
        tabs={[
          { value: "books", label: t("academy.tabBooks"), icon: "📘" },
          { value: "slides", label: t("academy.tabSlides"), icon: "🖥️" },
          { value: "videos", label: t("academy.tabVideos"), icon: "🎬" },
          { value: "anki", label: t("academy.tabAnki"), icon: "🧠" },
          { value: "quiz", label: t("academy.tabQuiz"), icon: "✅" },
        ]}
      />
      {tab === "books" && (bookId
        ? <BookView bookId={Number(bookId)} onBack={() => setParams({ tab: "books" })} />
        : <Books onOpen={(id) => setParams({ tab: "books", book: String(id) })} />)}
      {tab === "slides" && <Media kind="slide" />}
      {tab === "videos" && <Media kind="video" />}
      {tab === "anki" && <Anki />}
      {tab === "quiz" && <><QuizAdmin /><Quiz /></>}
    </div>
  );
}
