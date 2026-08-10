"""Minimal client for Taiji's controlled Keycloak IAM API."""

from dataclasses import dataclass
import time

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
        self._service_token = None
        self._service_token_expires_at = 0.0

    def health(self) -> dict:
        return self._request_public("GET", f"{self.realm_url}/taiji-iam/health")

    def reconciliation_tenants(self) -> list[dict]:
        result = self._request(
            "GET",
            f"{self.realm_url}/taiji-iam/v1/reconciliation/tenants",
            access_token=self._reconciler_token(),
        )
        return result.get("tenants", [])

    def reconciliation_members(self, tenant_id: str) -> list[dict]:
        result = self._request(
            "GET",
            f"{self.realm_url}/taiji-iam/v1/reconciliation/tenants/{tenant_id}/members",
            access_token=self._reconciler_token(),
        )
        return result.get("members", [])

    def reconciliation_platform_admins(self) -> list[dict]:
        result = self._request(
            "GET",
            f"{self.realm_url}/taiji-iam/v1/reconciliation/platform-admins",
            access_token=self._reconciler_token(),
        )
        return result.get("platform_admins", [])

    def list_my_tenants(self, access_token: str) -> dict:
        return self._request(
            "GET",
            f"{self.realm_url}/taiji-iam/v1/me/tenants",
            access_token=access_token,
        )

    def list_members(self, access_token: str, tenant_id: str) -> dict:
        return self._request(
            "GET",
            f"{self.realm_url}/taiji-iam/v1/tenants/{tenant_id}/members",
            access_token=access_token,
        )

    def add_member(self, access_token: str, tenant_id: str, payload: dict) -> dict:
        return self._request(
            "POST",
            f"{self.realm_url}/taiji-iam/v1/tenants/{tenant_id}/members",
            access_token=access_token,
            payload=payload,
        )

    def update_member(
        self, access_token: str, tenant_id: str, user_id: str, payload: dict
    ) -> dict:
        return self._request(
            "PATCH",
            f"{self.realm_url}/taiji-iam/v1/tenants/{tenant_id}/members/{user_id}",
            access_token=access_token,
            payload=payload,
        )

    def deactivate_member(self, access_token: str, tenant_id: str, user_id: str) -> dict:
        return self._request(
            "DELETE",
            f"{self.realm_url}/taiji-iam/v1/tenants/{tenant_id}/members/{user_id}",
            access_token=access_token,
        )

    def create_tenant(
        self, access_token: str, payload: dict, idempotency_key: str
    ) -> dict:
        return self._request(
            "POST",
            f"{self.realm_url}/taiji-iam/v1/tenants",
            access_token=access_token,
            payload=payload,
            extra_headers={"Idempotency-Key": idempotency_key},
        )

    def update_tenant(self, access_token: str, tenant_id: str, payload: dict) -> dict:
        return self._request(
            "PATCH",
            f"{self.realm_url}/taiji-iam/v1/tenants/{tenant_id}",
            access_token=access_token,
            payload=payload,
        )

    def list_platform_admins(self, access_token: str) -> dict:
        return self._request(
            "GET",
            f"{self.realm_url}/taiji-iam/v1/platform-admins",
            access_token=access_token,
        )

    def grant_platform_admin(self, access_token: str, identifier: str) -> dict:
        return self._request(
            "POST",
            f"{self.realm_url}/taiji-iam/v1/platform-admins",
            access_token=access_token,
            payload={"identifier": identifier},
        )

    def revoke_platform_admin(self, access_token: str, user_id: str) -> dict:
        return self._request(
            "DELETE",
            f"{self.realm_url}/taiji-iam/v1/platform-admins/{user_id}",
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

    def _reconciler_token(self) -> str:
        now = time.monotonic()
        if self._service_token and now < self._service_token_expires_at:
            return self._service_token
        try:
            response = requests.post(
                f"{self.realm_url}/protocol/openid-connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": current_app.config["IAM_RECONCILER_CLIENT_ID"],
                    "client_secret": current_app.config["IAM_RECONCILER_CLIENT_SECRET"],
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise IamHttpError(503, "iam_unavailable", "身份服务暂时不可用") from exc
        if response.status_code >= 400:
            payload = _json_or_empty(response)
            raise IamHttpError(
                response.status_code,
                payload.get("error", "service_token_failed"),
                payload.get("error_description", "对账服务认证失败"),
            )
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise IamHttpError(502, "invalid_iam_response", "身份服务返回了无效响应")
        self._service_token = token
        self._service_token_expires_at = now + max(int(payload.get("expires_in", 60)) - 10, 1)
        return token

    def _request_public(self, method: str, url: str) -> dict:
        try:
            response = requests.request(method, url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise IamHttpError(503, "iam_unavailable", "身份服务暂时不可用") from exc
        if response.status_code >= 400:
            raise IamHttpError(response.status_code, "iam_unavailable", "身份服务暂时不可用")
        value = response.json()
        if not isinstance(value, dict):
            raise IamHttpError(502, "invalid_iam_response", "身份服务返回了无效响应")
        return value

    def _request(
        self,
        method: str,
        url: str,
        *,
        access_token: str,
        payload: dict | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        headers.update(extra_headers or {})
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=payload,
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
        if response.status_code == 204 or not response.content:
            return {}
        value = response.json()
        if not isinstance(value, dict):
            raise IamHttpError(502, "invalid_iam_response", "身份服务返回了无效响应")
        return value


def as_business_error(error: IamHttpError) -> BusinessError:
    if error.status == 401:
        return BusinessError(ErrorCode.SESSION_EXPIRED, "身份会话已失效，请重新登录")
    if error.status == 403:
        return BusinessError(ErrorCode.PERMISSION_DENIED, error.message)
    if error.status >= 500:
        return BusinessError(ErrorCode.IAM_UNAVAILABLE)
    if error.code == "user_not_found":
        return BusinessError(ErrorCode.USER_NOT_FOUND, error.message)
    if error.code == "tenant_not_found":
        return BusinessError(ErrorCode.TENANT_NOT_FOUND, error.message)
    if error.code in {"identity_conflict", "idempotency_conflict"}:
        return BusinessError(ErrorCode.IDENTITY_CONFLICT, error.message)
    if error.code in {"personal_tenant_immutable", "last_tenant_admin", "last_platform_admin"}:
        return BusinessError(ErrorCode.IAM_CONFLICT, error.message)
    if error.status == 404:
        return BusinessError(ErrorCode.NOT_FOUND, error.message)
    if error.status == 409:
        return BusinessError(ErrorCode.IAM_CONFLICT, error.message)
    return BusinessError(ErrorCode.VALIDATION_ERROR, error.message)


def _json_or_empty(response) -> dict:
    try:
        value = response.json()
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}
