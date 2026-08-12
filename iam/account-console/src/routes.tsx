import {
  Applications,
  DeviceActivity,
  Groups,
  LinkedAccounts,
  Organizations,
  PersonalInfo,
  SigningIn,
} from "@keycloak/keycloak-account-ui";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Navigate, type RouteObject, useRouteError } from "react-router-dom";
import App from "./App";
import style from "./App.module.css";
import { environment } from "./environment";

function ErrorState() {
  const error = useRouteError();
  console.error(error);

  return (
    <div className={style.errorState} role="alert">
      <AlertTriangle size={30} />
      <h1>页面载入失败</h1>
      <p>账号中心暂时无法载入此页面，请重试。</p>
      <button type="button" onClick={() => window.location.reload()}>
        <RotateCcw size={16} />
        重新载入
      </button>
    </div>
  );
}

const rootPath = decodeURIComponent(new URL(environment.baseUrl).pathname);

export const routes: RouteObject[] = [
  {
    path: rootPath,
    element: <App />,
    errorElement: <ErrorState />,
    children: [
      { index: true, element: <Navigate to="personalInfo" replace /> },
      { path: "personalInfo", element: <PersonalInfo /> },
      { path: "account-security/signingIn", element: <SigningIn /> },
      { path: "account-security/deviceActivity", element: <DeviceActivity /> },
      { path: "account-security/linkedAccounts", element: <LinkedAccounts /> },
      { path: "applications", element: <Applications /> },
      { path: "organizations", element: <Organizations /> },
      { path: "groups", element: <Groups /> },
      { path: "*", element: <Navigate to="personalInfo" replace /> },
    ],
  },
];
