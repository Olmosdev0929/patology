import { useEffect } from "react";
import { HashRouter, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import Layout from "./components/Layout";
import { ToastProvider } from "./components/toast";
import { Loading } from "./components/ui";
import { AuthProvider, useAuth } from "./lib/auth";
import { I18nProvider } from "./lib/i18n";
import { ThemeProvider } from "./lib/theme";
import { tg } from "./lib/telegram";
import Academy from "./pages/Academy";
import Admin from "./pages/Admin";
import { AtlasDisease, AtlasHome } from "./pages/Atlas";
import CaseDetail from "./pages/CaseDetail";
import Cases from "./pages/Cases";
import GalleryPage from "./pages/GalleryPage";
import Inventory from "./pages/Inventory";
import Login from "./pages/Login";

/** Telegram's native BackButton follows the router history. */
function TelegramBackButton() {
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    if (!tg?.BackButton) return;
    const back = () => navigate(-1);
    const depth = location.pathname.split("/").filter(Boolean).length;
    if (depth > 1) tg.BackButton.show(); else tg.BackButton.hide();
    tg.BackButton.onClick(back);
    return () => tg.BackButton.offClick(back);
  }, [location, navigate]);
  return null;
}

function Guard({ cap, children }) {
  const { can } = useAuth();
  return can(cap) ? children : <Navigate to="/atlas" replace />;
}

function OrganRedirect() {
  const { slug } = useParams();
  return <Navigate to={`/atlas?organ=${slug}`} replace />;
}

function Shell() {
  const { state } = useAuth();
  if (state === "loading") return <Loading />;
  if (state !== "ready") return <Login />;
  return (
    <>
      <TelegramBackButton />
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/atlas" replace />} />
          <Route path="atlas" element={<AtlasHome />} />
          <Route path="atlas/organ/:slug" element={<OrganRedirect />} />
          <Route path="atlas/disease/:slug" element={<AtlasDisease />} />
          <Route path="cases" element={<Guard cap="cases"><Cases /></Guard>} />
          <Route path="cases/:code" element={<Guard cap="cases"><CaseDetail /></Guard>} />
          <Route path="inventory" element={<Guard cap="inventory"><Inventory /></Guard>} />
          <Route path="academy" element={<Academy />} />
          <Route path="gallery" element={<GalleryPage />} />
          <Route path="admin" element={<Guard cap="admin"><Admin /></Guard>} />
          <Route path="*" element={<Navigate to="/atlas" replace />} />
        </Route>
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <I18nProvider>
        <AuthProvider>
          <ToastProvider>
            <HashRouter>
              <Shell />
            </HashRouter>
          </ToastProvider>
        </AuthProvider>
      </I18nProvider>
    </ThemeProvider>
  );
}
