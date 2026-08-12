import type { Feature } from "@keycloak/keycloak-account-ui";
import {
  AppWindow,
  Building2,
  KeyRound,
  Link2,
  MonitorSmartphone,
  UserRound,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import style from "./App.module.css";

type NavEntry = {
  path: string;
  zh: string;
  en: string;
  icon: LucideIcon;
  feature?: keyof Feature;
};

const items: NavEntry[] = [
  { path: "personalInfo", zh: "个人资料", en: "Personal info", icon: UserRound },
  {
    path: "account-security/signingIn",
    zh: "登录与密码",
    en: "Sign-in & password",
    icon: KeyRound,
  },
  {
    path: "account-security/deviceActivity",
    zh: "登录设备",
    en: "Signed-in devices",
    icon: MonitorSmartphone,
  },
  {
    path: "account-security/linkedAccounts",
    zh: "关联账号",
    en: "Linked accounts",
    icon: Link2,
    feature: "isLinkedAccountsEnabled",
  },
  {
    path: "applications",
    zh: "授权应用",
    en: "Applications",
    icon: AppWindow,
    feature: "isViewApplicationsEnabled",
  },
  {
    path: "organizations",
    zh: "所属租户",
    en: "Organizations",
    icon: Building2,
    feature: "isViewOrganizationsEnabled",
  },
  {
    path: "groups",
    zh: "用户组",
    en: "Groups",
    icon: UsersRound,
    feature: "isViewGroupsEnabled",
  },
];

export function PageNav({ features }: { features: Feature }) {
  const isZh = document.documentElement.lang.toLowerCase().startsWith("zh");

  return (
    <nav className={style.nav} aria-label={isZh ? "账号设置" : "Account settings"}>
      {items
        .filter(({ feature }) => !feature || features[feature])
        .map(({ path, zh, en, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `${style.navItem} ${isActive ? style.navItemActive : ""}`
            }
          >
            <Icon size={18} strokeWidth={1.9} />
            <span>{isZh ? zh : en}</span>
          </NavLink>
        ))}
    </nav>
  );
}
