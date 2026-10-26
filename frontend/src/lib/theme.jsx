import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { tg } from "./telegram";

const ThemeContext = createContext({ dark: false, toggle: () => {} });

function initial() {
  try {
    const v = localStorage.getItem("pathouz.theme");
    if (v === "dark" || v === "light") return v === "dark";
  } catch {}
  if (tg?.colorScheme) return tg.colorScheme === "dark";
  return false; // light by default
}

export function ThemeProvider({ children }) {
  const [dark, setDark] = useState(initial);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    const color = dark ? "#0b1120" : "#ffffff";
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", color);
    try {
      tg?.setHeaderColor(color);
      tg?.setBackgroundColor(dark ? "#0b1120" : "#f5f7f9");
    } catch {}
  }, [dark]);

  const toggle = useCallback(() => {
    setDark((d) => {
      try { localStorage.setItem("pathouz.theme", d ? "light" : "dark"); } catch {}
      return !d;
    });
  }, []);

  return <ThemeContext.Provider value={{ dark, toggle }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
