import { lazy, Suspense, useState } from "react";
import { NavLink, Route, Routes, Link } from "react-router-dom";
import {
  AudioLines,
  Bird,
  Camera,
  ChartNoAxesCombined,
  ChevronRight,
  Download,
  GitCompareArrows,
  History as HistoryIcon,
  Images,
  LayoutDashboard,
  Menu,
  X,
  CreditCard,
  UserRound,
  Wallet,
} from "lucide-react";
import { api, useApi } from "./api";
import { ApiError } from "../../shared/api";
import Home from "./pages/Home";
import Analyze from "./pages/Analyze";
import { AnalysisDetails, BirdDetails, History } from "./pages/History";
import Compare from "./pages/Compare";
import "./styles.css";
import { FeatureGate, RequireAuth, useAuth } from "./auth";
import { AuthPage, MySubscription, Payments, Plans } from "./pages/Account";

const links = [
  ["/", "Головна", LayoutDashboard],
  ["/photo", "Аналіз фотографій", Camera],
  ["/audio", "Аналіз аудіо", AudioLines],
  ["/history", "Історія аналізів", HistoryIcon],
  ["/gallery", "Галерея", Images],
  ["/statistics", "Статистика", ChartNoAxesCombined],
  ["/compare", "Порівняння", GitCompareArrows],
  ["/plans", "Тарифи", CreditCard],
  ["/account", "Моя підписка", UserRound],
  ["/payments", "Історія платежів", Wallet],
] as const;
const Statistics = lazy(() => import("./pages/Statistics"));
const Checkout = lazy(() => import("./pages/Checkout"));
export default function App() {
  const [menu, setMenu] = useState(false);
  const auth = useAuth();
  const health = useApi<{ status: string; database: boolean; ai: boolean }>(
    "/health",
  );
  const degraded =
    health.error instanceof ApiError && health.error.status === 503;
  return (
    <div className="shell">
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <Link className="brand" to="/" onClick={() => setMenu(false)}>
          <span className="brand-icon">
            <Bird size={28} />
          </span>
          <span>
            AI Bird Lab<small>ЛАБОРАТОРІЯ ВІДКРИТТІВ</small>
          </span>
        </Link>
        <span className="nav-caption">ЛАБОРАТОРІЯ</span>
        <nav>
          {links.map(([path, name, Icon]) => (
            <NavLink
              end={path === "/"}
              key={path}
              to={path}
              onClick={() => setMenu(false)}
            >
              <Icon size={19} />
              <span>{name}</span>
              <ChevronRight className="nav-arrow" size={14} />
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <a href={`${api.base}/api/export/csv`}>
            <Download size={18} /> Експортувати дані
          </a>
          <div className="sync-note">
            <span
              className={`status-dot ${health.data?.status === "ok" ? "" : "offline"}`}
            />
            <div>
              <strong>
                {health.data?.status === "ok"
                  ? "Сервіси доступні"
                  : degraded
                    ? "Частина сервісів недоступна"
                    : "Перевірте з’єднання"}
              </strong>
              <small>Єдина історія для всіх пристроїв</small>
            </div>
          </div>
          <span className="caption">AI Bird Lab · Версія 2.0</span>
        </div>
      </aside>
      {menu && (
        <button
          className="menu-shade"
          aria-label="Закрити меню"
          onClick={() => setMenu(false)}
        />
      )}
      <div className="workspace">
        <header className="topbar">
          <button
            className="menu-button"
            onClick={() => setMenu((v) => !v)}
            aria-label="Меню"
          >
            {menu ? <X /> : <Menu />}
          </button>
          <span>
            <Bird size={16} /> Простір дослідника
          </span>
          <div>
            <span className="online-label">
              <span className={`status-dot ${health.data ? "" : "offline"}`} />{" "}
              {health.data
                ? "Підключено до лабораторії"
                : degraded
                  ? "Частина сервісів недоступна"
                  : "Сервер недоступний"}
            </span>
            <Link
              className="avatar"
              to={auth.user ? "/account" : "/login"}
              aria-label={auth.user ? "Мій обліковий запис" : "Увійти"}
            >
              {auth.user?.email.slice(0, 1).toUpperCase() || "У"}
            </Link>
          </div>
        </header>
        <main>
          <Routes>
            <Route path="/login" element={<AuthPage />} />
            <Route path="/plans" element={<Plans />} />
            <Route element={<RequireAuth />}>
              <Route path="/" element={<Home />} />
              <Route
                path="/photo"
                element={<Analyze key="image" kind="image" />}
              />
              <Route
                path="/audio"
                element={
                  <FeatureGate feature="audio">
                    <Analyze key="audio" kind="audio" />
                  </FeatureGate>
                }
              />
              <Route path="/history" element={<History />} />
              <Route path="/history/:id" element={<AnalysisDetails />} />
              <Route
                path="/gallery"
                element={
                  <FeatureGate feature="gallery">
                    <History key="gallery" gallery />
                  </FeatureGate>
                }
              />
              <Route
                path="/statistics"
                element={
                  <FeatureGate feature="statistics">
                    <Suspense
                      fallback={
                        <div className="state" role="status">
                          Завантажуємо графіки…
                        </div>
                      }
                    >
                      <Statistics />
                    </Suspense>
                  </FeatureGate>
                }
              />
              <Route
                path="/compare"
                element={
                  <FeatureGate feature="compare">
                    <Compare />
                  </FeatureGate>
                }
              />
              <Route path="/birds/:id" element={<BirdDetails />} />
              <Route path="/account" element={<MySubscription />} />
              <Route path="/payments" element={<Payments />} />
              <Route
                path="/checkout/:planId"
                element={
                  <Suspense
                    fallback={
                      <div className="state" role="status">
                        Готуємо оплату…
                      </div>
                    }
                  >
                    <Checkout />
                  </Suspense>
                }
              />
            </Route>
            <Route
              path="*"
              element={
                <div className="state">
                  <h1>Сторінку не знайдено</h1>
                  <Link to="/">Повернутися до лабораторії</Link>
                </div>
              }
            />
          </Routes>
          <footer>
            Створено для допитливих до природи{" "}
            <span>AI допомагає спостерігати. Ви робите відкриття.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
