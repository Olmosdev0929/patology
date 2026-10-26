import { useEffect, useState } from "react";
import { Send } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import { Button, Card } from "../components/ui";

export default function Login() {
  const { t, lang, setLang } = useI18n();
  const { devLogin, error } = useAuth();
  const [dev, setDev] = useState(false);
  const [botUrl, setBotUrl] = useState("https://t.me/");

  useEffect(() => {
    api("/health").then((h) => {
      setDev(Boolean(h?.dev));
      if (h?.bot_username) setBotUrl(`https://t.me/${h.bot_username}`);
    }).catch(() => {});
  }, []);

  return (
    <div className="grid min-h-screen place-items-center p-4">
      <Card className="w-full max-w-sm text-center">
        <div className="mx-auto mb-4 grid size-16 place-items-center rounded-2xl bg-gradient-to-br from-teal-500 to-teal-700 text-3xl">🔬</div>
        <h1 className="text-xl font-bold">{t("login.title")}</h1>
        <p className="mt-1 text-xs text-muted">{t("app.tagline")}</p>
        <p className="mt-4 text-sm text-fg/85">{t("login.telegram")}</p>
        {error && <p className="mt-3 rounded-xl bg-rose-50 dark:bg-rose-500/10 p-2 text-sm text-rose-600 dark:text-rose-300">{t("login.failed")}: {error}</p>}
        <div className="mt-4 flex justify-center gap-2">
          <Button variant="outline" onClick={() => setLang(lang === "uz" ? "ru" : "uz")} className="font-mono">
            {lang === "uz" ? "РУ" : "O'Z"}
          </Button>
          <Button variant="smart" onClick={() => window.open(botUrl, "_blank", "noopener")}>
            <Send className="size-4" />{t("login.openBot")}
          </Button>
        </div>
        {dev && (
          <div className="mt-6 border-t border-line pt-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-amber-600 dark:text-amber-300">{t("login.dev")}</p>
            <div className="grid grid-cols-2 gap-2">
              {["super_admin", "pathologist", "technician", "resident"].map((role) => (
                <Button key={role} variant="ghost" className="text-xs" onClick={() => devLogin(role)}>{t(`roles.${role}`)}</Button>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
