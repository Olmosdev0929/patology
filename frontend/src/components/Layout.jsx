import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Bot, BookOpen, ClipboardList, Image as ImageIcon, LogOut, Microscope, Moon, Package, Presentation, Search, ShieldCheck, Sun, Terminal } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import { useTheme } from "../lib/theme";
import { openExternal, tg } from "../lib/telegram";
import { Modal, cx, useAsync } from "./ui";

export const NAV = [
  { to: "/cases", key: "cases", icon: ClipboardList, cap: "cases" },
  { to: "/inventory", key: "inventory", icon: Package, cap: "inventory" },
  { to: "/atlas", key: "atlas", icon: BookOpen },
  { to: "/academy", key: "academy", icon: Presentation },
  { to: "/gallery", key: "gallery", icon: ImageIcon },
];

function LangSwitch() {
  const { lang, setLang } = useI18n();
  const { user } = useAuth();
  const choose = (next) => {
    setLang(next);
    // Persist on the server too so bot notifications follow the same language.
    if (user) api("/me", { method: "PATCH", body: { language: next } }).catch(() => {});
  };
  return (
    <div className="flex rounded-xl border border-line bg-surface-2 p-0.5 text-xs font-bold">
      {[["uz", "O'Z"], ["ru", "РУ"]].map(([code, label]) => (
        <button key={code} onClick={() => choose(code)} aria-pressed={lang === code}
          className={cx("min-h-8 rounded-lg px-2 transition", lang === code ? "bg-surface text-primary-ink shadow-sm" : "text-muted")}>
          {label}
        </button>
      ))}
    </div>
  );
}

function IconButton({ children, label, className, ...props }) {
  return (
    <button aria-label={label} title={label} className={cx("grid size-9 shrink-0 sm:size-10 place-items-center rounded-xl bg-surface-2 text-fg transition hover:bg-line", className)} {...props}>
      {children}
    </button>
  );
}

function GlobalSearch() {
  const { t, L } = useI18n();
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const location = useLocation();

  useEffect(() => { setOpen(false); setQ(""); }, [location.pathname]);
  useEffect(() => {
    if (q.trim().length < 2) return setRes(null);
    const ctrl = new AbortController();
    const id = setTimeout(() => {
      api(`/search?q=${encodeURIComponent(q.trim())}`, { signal: ctrl.signal }).then((r) => { setRes(r); setOpen(true); }).catch(() => {});
    }, 220);
    return () => { clearTimeout(id); ctrl.abort(); };
  }, [q]);
  useEffect(() => {
    const close = (e) => { if (!box.current?.contains(e.target)) setOpen(false); };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  const empty = res && !res.diseases.length && !res.markers.length && !res.biopsies.length;
  const Group = ({ title, children }) => (
    <div className="py-1">
      <div className="px-3 pb-1 pt-2 text-[11px] font-bold uppercase tracking-wide text-muted">{title}</div>
      {children}
    </div>
  );
  const Row = ({ to, children }) => (
    <Link to={to} className="flex items-center gap-2 px-3 py-2.5 text-sm hover:bg-surface-2">{children}</Link>
  );

  return (
    <div ref={box} className="relative">
      <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted" />
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => res && setOpen(true)}
        type="search"
        placeholder={t("app.searchPh")}
        className="w-full rounded-2xl border border-transparent bg-surface-2 py-3 pl-10 pr-3 text-base text-fg outline-none placeholder:text-muted/80 focus:border-primary/40 focus:bg-surface sm:text-sm"
      />
      {open && res && (
        <div className="fade-in absolute inset-x-0 top-full z-40 mt-2 max-h-[60vh] overflow-y-auto rounded-2xl border border-line bg-surface shadow-xl">
          {empty && <div className="p-4 text-sm text-muted">{t("search.none")}</div>}
          {res.diseases.length > 0 && (
            <Group title={t("search.diseases")}>
              {res.diseases.map((d) => (
                <Row key={d.slug} to={`/atlas/disease/${d.slug}`}>
                  <span>{d.organ.icon}</span>
                  <span className="min-w-0 flex-1 truncate font-medium">{L(d.name)}</span>
                  {d.icd10 && <span className="font-mono text-xs text-muted">{d.icd10}</span>}
                </Row>
              ))}
            </Group>
          )}
          {res.markers.length > 0 && (
            <Group title={t("search.markers")}>
              {res.markers.map((m) => (
                <Row key={m.id} to={`/inventory?marker=${m.id}`}>
                  <span className="font-mono font-semibold">{m.name}</span>
                  <span className="font-mono text-xs text-muted">{m.clone}</span>
                  <span className="ml-auto font-mono text-xs text-primary-ink">{t("inv.tests", { n: m.stock })}</span>
                </Row>
              ))}
            </Group>
          )}
          {res.biopsies.length > 0 && (
            <Group title={t("search.biopsies")}>
              {res.biopsies.map((b) => (
                <Row key={b.code} to={`/cases/${b.code}`}>
                  <span className="font-mono font-semibold text-primary-ink">{b.code}</span>
                  <span className="min-w-0 flex-1 truncate">{b.patient_name}</span>
                  <span className="text-xs text-muted">{t(`organs.${b.organ}`)}</span>
                </Row>
              ))}
            </Group>
          )}
        </div>
      )}
    </div>
  );
}

function BotModal({ open, onClose, botUrl }) {
  const { t } = useI18n();
  return (
    <Modal open={open} onClose={onClose} title={t("header.botTitle")}>
      <ul className="space-y-2">
        {t("header.botCommands").map(([cmd, desc]) => (
          <li key={cmd} className="flex items-start gap-3 rounded-xl bg-surface-2 p-3">
            <code className="rounded-md bg-surface px-2 py-0.5 font-mono text-sm font-semibold text-primary-ink">{cmd}</code>
            <span className="text-sm">{desc}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-sm text-muted">{t("header.botNote")}</p>
      {botUrl && (
        <button onClick={() => openExternal(botUrl)} className="mt-4 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary text-sm font-semibold text-white dark:text-slate-950">
          <Bot className="size-4" />{t("header.bot")}
        </button>
      )}
    </Modal>
  );
}

export default function Layout() {
  const { t } = useI18n();
  const { user, can, logout } = useAuth();
  const { dark, toggle } = useTheme();
  const [botOpen, setBotOpen] = useState(false);
  const health = useAsync(() => api("/health"), []);
  const pending = useAsync(() => (can("cases") ? api("/biopsies?status=registered&limit=500") : Promise.resolve([])), [user?.role]);
  const location = useLocation();

  useEffect(() => { if (location.pathname.startsWith("/cases")) pending.reload(); }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const botUrl = health.data?.bot_username ? `https://t.me/${health.data.bot_username}` : null;
  const items = NAV.filter((n) => !n.cap || can(n.cap));
  const pendingCount = pending.data?.length || 0;

  return (
    <div className="min-h-screen">
      <header className="safe-top sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto max-w-5xl px-4 pb-3 pt-3">
          <div className="flex items-center gap-3">
            <Link to="/atlas" className="grid size-10 shrink-0 place-items-center rounded-2xl bg-primary text-white shadow-sm sm:size-12 dark:text-slate-950">
              <Microscope className="size-5 sm:size-6" />
            </Link>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-lg font-extrabold tracking-tight">PathoUz</span>
                <span className="hidden whitespace-nowrap rounded-md border border-primary/30 bg-primary-soft px-1.5 py-0.5 text-[11px] font-bold text-primary-ink sm:inline">{t("app.badge")}</span>
              </div>
              <div className="truncate text-xs text-muted">{t("app.subtitle")}</div>
            </div>
            <div className="flex shrink-0 items-center gap-1 sm:gap-1.5">
              <button onClick={() => setBotOpen(true)} className="hidden min-h-10 items-center gap-1.5 rounded-xl border border-primary/25 bg-primary-soft px-3 text-sm font-semibold text-primary-ink sm:flex">
                <Terminal className="size-4" />{t("header.botCode")}
              </button>
              <button onClick={() => (botUrl ? openExternal(botUrl) : setBotOpen(true))} className="relative hidden min-h-10 items-center gap-1.5 rounded-xl border border-sky-200 bg-sky-50 px-3 text-sm font-semibold text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-300 sm:flex">
                <Bot className="size-4" />{t("header.bot")}
                {health.data?.bot && <span className="absolute -right-1 -top-1 size-2.5 rounded-full bg-rose-400 ring-2 ring-surface" />}
              </button>
              <IconButton label={t("header.botCode")} className="sm:hidden" onClick={() => setBotOpen(true)}><Bot className="size-5" /></IconButton>
              <LangSwitch />
              <IconButton label={t("header.theme")} onClick={toggle}>{dark ? <Sun className="size-5" /> : <Moon className="size-5" />}</IconButton>
              {can("admin") && (
                <NavLink to="/admin" aria-label={t("nav.admin")} title={t("nav.admin")}
                  className={({ isActive }) => cx("grid size-9 place-items-center rounded-xl sm:size-10", isActive ? "bg-primary text-white dark:text-slate-950" : "bg-surface-2 hover:bg-line")}>
                  <ShieldCheck className="size-5" />
                </NavLink>
              )}
              {!tg && <IconButton label={t("common.logout")} onClick={logout}><LogOut className="size-4" /></IconButton>}
            </div>
          </div>
          <div className="mt-3"><GlobalSearch /></div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-28 pt-5">
        <Outlet />
      </main>

      <nav className="safe-bottom fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl gap-1 px-2 pt-1.5">
          {items.map(({ to, key, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => cx(
                "relative flex min-h-14 flex-1 flex-col items-center justify-center gap-1 rounded-2xl text-[11px] font-semibold transition",
                isActive ? "bg-primary-soft text-primary-ink" : "text-muted hover:text-fg",
              )}
            >
              <span className="relative">
                <Icon className="size-5" />
                {key === "cases" && pendingCount > 0 && (
                  <span className="absolute -right-3 -top-2 grid min-w-5 place-items-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">{pendingCount}</span>
                )}
              </span>
              {t(`nav.${key}`)}
            </NavLink>
          ))}
        </div>
      </nav>

      <BotModal open={botOpen} onClose={() => setBotOpen(false)} botUrl={botUrl} />
    </div>
  );
}
