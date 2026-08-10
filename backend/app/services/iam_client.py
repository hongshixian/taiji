"""Minimal client for Taiji's controlled Keycloak IAM API."""

from dataclasses import dataclass

import requests
from flask import current_app

from app.utils.errors import BusinessError, ErrorCode


@dataclass(frozen=True)
class IamHttpError(Exception):
    status: int
    code: str
    message: str


class IamClient:
    def __init__(self):
        realm = current_app.config["IAM_REALM"]
        self.realm_url = f"{current_app.config['IAM_INTERNAL_URL']}/realms/{realm}"
        self.timeout = (2, 5)

    def list_my_tenants(self, access_token: str) -> dict:
        return self._request(
            "GET",
            f"{self.realm_url}/taiji-iam/v1/me/tenants",
            access_token=access_token,
        )

    def refresh_token(self, refresh_token: str) -> dict:
        try:
            response = requests.post(
                f"{self.realm_url}/protocol/openid-connect/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": current_app.config["OIDC_CLIENT_ID"],
                    "client_secret": current_app.config["OIDC_CLIENT_SECRET"],
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise IamHttpError(503, "iam_unavailable", "身份服务暂时不可用") from exc
        if response.status_code >= 400:
            payload = _json_or_empty(response)
            raise IamHttpError(
                response.status_code,
                payload.get("error", "token_refresh_failed"),
                payload.get("error_description", "身份会话刷新失败"),
            )
        return response.json()

    def _request(self, method: str, url: str, *, access_token: str) -> dict:
        try:
            response = requests.request(
                method,
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise IamHttpError(503, "iam_unavailable", "身份服务暂时不可用") from exc
        if response.status_code >= 400:
            payload = _json_or_empty(response)
            raise IamHttpError(
                response.status_code,
                payload.get("code", "iam_request_failed"),
                payload.get("message", "身份服务请求失败"),
            )
        return response.json()


def as_business_error(error: IamHttpError) -> BusinessError:
    if error.status in {401, 403}:
        return BusinessError(ErrorCode.SESSION_EXPIRED, "身份会话已失效，请重新登录")
    return BusinessError(ErrorCode.IAM_UNAVAILABLE)


def _json_or_empty(response) -> dict:
    try:
        value = response.json()
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}
