import type { AccountEnvironment } from "@keycloak/keycloak-account-ui";
import { useEnvironment } from "@keycloak/keycloak-account-ui";
import {
  ArrowLeft,
  LogOut,
  Menu,
  ShieldCheck,
  X,
} from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { PageNav } from "./PageNav";
import style from "./App.module.css";

const labels = {
  zh: {
    accountCenter: "账号中心",
    securityState: "账号安全受统一身份服务保护",
    back: "返回太极",
    signOut: "退出登录",
    openNav: "打开导航",
    closeNav: "关闭导航",
    loading: "正在载入账号信息",
  },
  en: {
    accountCenter: "Account center",
    securityState: "Protected by unified identity services",
    back: "Back to Taiji",
    signOut: "Sign out",
    openNav: "Open navigation",
    closeNav: "Close navigation",
    loading: "Loading account information",
  },
};

function App() {
  const { environment, keycloak } = useEnvironment<AccountEnvironment>();
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();
  const copy = environment.locale.toLowerCase().startsWith("zh")
    ? labels.zh
    : labels.en;

  useEffect(() => setNavOpen(false), [location.pathname]);

  const claims = keycloak.idTokenParsed;
  const username =
    [claims?.given_name, claims?.family_name].filter(Boolean).join("") ||
    claims?.preferred_username ||
    claims?.email ||
    "User";
  const initial = username.slice(0, 1).toUpperCase();

  return (
    <div className={style.shell}>
      <header className={style.header}>
        <button
          className={style.menuButton}
          type="button"
          aria-label={navOpen ? copy.closeNav : copy.openNav}
          aria-expanded={navOpen}
          onClick={() => setNavOpen((open) => !open)}
        >
          {navOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        <a className={style.brand} href={environment.baseUrl}>
          <img src={`${environment.resourceUrl}/brand.svg`} alt="" />
          <span className={style.brandName}>方寸 IAM</span>
          <span className={style.brandSection}>{copy.accountCenter}</span>
        </a>

        <div className={style.headerActions}>
          {environment.referrerUrl && (
            <a className={style.backLink} href={environment.referrerUrl}>
              <ArrowLeft size={16} />
              <span>{environment.referrerName || copy.back}</span>
            </a>
          )}
          <div className={style.identity} title={username}>
            <span className={style.avatar}>{initial}</span>
            <span className={style.username}>{username}</span>
          </div>
          <button
            className={style.signOut}
            type="button"
            title={copy.signOut}
            aria-label={copy.signOut}
            onClick={() => void keycloak.logout()}
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <div className={style.body}>
        <aside className={`${style.sidebar} ${navOpen ? style.sidebarOpen : ""}`}>
          <div className={style.securityState}>
            <ShieldCheck size={18} />
            <span>{copy.securityState}</span>
          </div>
          <PageNav features={environment.features} />
        </aside>
        {navOpen && (
          <button
            className={style.scrim}
            type="button"
            aria-label={copy.closeNav}
            onClick={() => setNavOpen(false)}
          />
        )}

        <main className={style.main}>
          <Suspense
            fallback={
              <div className={style.loading} role="status">
                <span className={style.spinner} />
                <span>{copy.loading}</span>
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}

export default App;
