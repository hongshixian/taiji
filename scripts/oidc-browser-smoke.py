#!/usr/bin/env python3
"""Exercise Taiji's browser-facing OIDC flow against a running stack."""

import argparse
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    browser = requests.Session()
    completed = browser.get(f"{base_url}/api/v1/auth/login", timeout=15)
    completed.raise_for_status()
    callback_seen = False
    form = None
    fields = {}
    for _step in range(4):
        _allow_localhost_secure_cookies(browser, completed.url)
        form = BeautifulSoup(completed.text, "html.parser").select_one("#kc-form-login")
        if form is None:
            break
        fields = {
            element["name"]: element.get("value", "")
            for element in form.select("input[name], button[name]")
        }
        if form.select_one("input[name=username]"):
            fields["username"] = args.username
        if form.select_one("input[name=password]"):
            fields["password"] = args.password
        fields["login"] = "Sign In"
        if not form.select_one("input[name=rememberMe][checked]"):
            fields.pop("rememberMe", None)
        completed = browser.post(form["action"], data=fields, timeout=15)
        callback_seen = any(
            urlparse(item.url).path == "/api/v1/auth/callback"
            for item in completed.history
        )
        if callback_seen:
            break
    if not callback_seen:
        page = BeautifulSoup(completed.text, "html.parser")
        error = page.select_one(
            "#input-error, .kc-feedback-text, .alert-error, .pf-v5-c-alert__title"
        )
        visited = " -> ".join(
            f"{item.status_code}:{urlparse(item.url).path}" for item in completed.history
        )
        detail = error.get_text(" ", strip=True) if error else "no form error"
        cookies = ",".join(
            f"{item.name}@{item.domain}{item.path}:secure={item.secure}"
            for item in browser.cookies
        )
        page_text = " ".join(page.get_text(" ", strip=True).split())[:300]
        action_query = sorted(
            item.split("=", 1)[0] for item in urlparse(form["action"]).query.split("&") if item
        )
        final_query = sorted(
            item.split("=", 1)[0] for item in urlparse(completed.url).query.split("&") if item
        )
        field_shape = ",".join(
            f"{key}:{'<redacted>' if key == 'password' else repr(value)}"
            for key, value in sorted(fields.items())
        )
        raise RuntimeError(
            "OIDC callback was not reached after credential submission; "
            f"history={visited}; final={completed.status_code}:{urlparse(completed.url).path}; "
            f"detail={detail}; fields={field_shape}; "
            f"action_query={','.join(action_query)}; final_query={','.join(final_query)}; "
            f"page={page_text}; cookies={cookies}"
        )

    me = browser.get(f"{base_url}/api/v1/auth/me", timeout=15)
    me.raise_for_status()
    payload = me.json()["data"]
    if payload["username"] != args.username or payload["auth_mode"] != "oidc":
        raise RuntimeError("Taiji returned an unexpected authenticated identity")
    if not payload["tenants"] or not payload["current_tenant"]:
        raise RuntimeError("Taiji did not establish a current IAM tenant")

    logout = browser.post(
        f"{base_url}/api/v1/auth/logout",
        headers={"X-CSRF-Token": payload["csrf_token"]},
        timeout=15,
    )
    logout.raise_for_status()
    if browser.get(f"{base_url}/api/v1/auth/me", timeout=15).status_code != 401:
        raise RuntimeError("Taiji session remained usable after logout")

    print(
        f"OIDC browser smoke passed: user={payload['username']} "
        f"tenants={len(payload['tenants'])} current={payload['current_tenant']['name']}"
    )


def _allow_localhost_secure_cookies(browser: requests.Session, response_url: str):
    # Browsers treat localhost as a secure context; requests strictly withholds Secure
    # cookies over HTTP, so emulate browser behavior for local development smoke tests.
    parsed = urlparse(response_url)
    if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}:
        for cookie in browser.cookies:
            cookie.secure = False


if __name__ == "__main__":
    main()
