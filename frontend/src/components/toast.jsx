import { createContext, useCallback, useContext, useState } from "react";
import { Toast } from "./ui";
import { haptic } from "../lib/telegram";

const ToastContext = createContext(() => {});

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const show = useCallback((message, kind = "success") => {
    haptic(kind === "error" ? "error" : "success");
    setToast({ message, kind, id: Date.now() });
  }, []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      <Toast key={toast?.id} message={toast?.message} kind={toast?.kind} onDone={() => setToast(null)} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
