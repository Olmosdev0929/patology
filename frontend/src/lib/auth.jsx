import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken, setUnauthorizedHandler } from "./api";
import { tg } from "./telegram";
import { useI18n } from "./i18n";

const AuthContext = createContext(null);

/** What each role may see/do in the UI. The API enforces the same rules server-side. */
const CAPS = {
  super_admin: ["cases", "cases.write", "approve", "scoring", "consilium", "inventory", "inventory.write", "atlas.write", "admin"],
  pathologist: ["cases", "cases.write", "approve", "scoring", "consilium", "inventory", "atlas.write"],
  technician: ["cases", "inventory", "inventory.write"],
  resident: [],
};

export function AuthProvider({ children }) {
  const { setLang, hasStored } = useI18n();
  const [user, setUser] = useState(null);
  const [state, setState] = useState("loading"); // loading | ready | anonymous | error
  const [error, setError] = useState(null);

  const finish = useCallback((data) => {
    setToken(data.token);
    setUser(data.user);
    if (!hasStored && data.user.language) setLang(data.user.language);
    setState("ready");
  }, [hasStored, setLang]);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setState("anonymous");
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    (async () => {
      try {
        const linkToken = new URLSearchParams(window.location.hash.split("?")[1] || "").get("token");
        if (tg?.initData) {
          finish(await api("/auth/telegram", { method: "POST", body: { init_data: tg.initData } }));
        } else if (linkToken) {
          finish(await api("/auth/link", { method: "POST", body: { token: linkToken } }));
          window.location.hash = "#/";
        } else if (getToken()) {
          setUser(await api("/me"));
          setState("ready");
        } else {
          setState("anonymous");
        }
      } catch (e) {
        setError(e.message);
        setToken(null);
        setState("anonymous");
      }
    })();
  }, [finish, logout]);

  const devLogin = useCallback(async (role) => {
    finish(await api("/auth/dev-login", { method: "POST", body: { role, telegram_id: { super_admin: 1, pathologist: 2, technician: 3, resident: 4 }[role], name: `Dev ${role}` } }));
  }, [finish]);

  const can = useCallback((cap) => Boolean(user && CAPS[user.role]?.includes(cap)), [user]);

  return (
    <AuthContext.Provider value={{ user, setUser, state, error, logout, devLogin, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
