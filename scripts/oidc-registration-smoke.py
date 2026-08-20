#!/usr/bin/env python3
"""Exercise self-registration and personal workspace provisioning through OIDC."""

import argparse
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:28080")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    browser = requests.Session()
    page = browser.get(f"{base_url}/api/v1/auth/register", timeout=30)
    page.raise_for_status()
    _allow_localhost_secure_cookies(browser, page.url)
    form = BeautifulSoup(page.text, "html.parser").select_one("#kc-register-form")
    if form is None:
        raise RuntimeError("Keycloak registration form was not rendered")

    fields = {
        element["name"]: element.get("value", "")
        for element in form.select("input[name], button[name]")
    }
    fields.update({
        "username": args.username,
        "email": args.email,
        "firstName": "Docker",
        "lastName": "Registration",
        "password": args.password,
        "password-confirm": args.password,
    })
    completed = browser.post(form["action"], data=fields, timeout=30)
    callback_seen = any(
        urlparse(item.url).path == "/api/v1/auth/callback"
        for item in completed.history
    )
    if not callback_seen:
        error_page = BeautifulSoup(completed.text, "html.parser")
        error = error_page.select_one(
            "#input-error, .kc-feedback-text, .alert-error, .pf-v5-c-alert__title"
        )
        detail = error.get_text(" ", strip=True) if error else completed.url
        raise RuntimeError(f"registration did not reach Taiji callback: {detail}")

    me = browser.get(f"{base_url}/api/v1/auth/me", timeout=30)
    me.raise_for_status()
    identity = me.json()["data"]
    if identity["username"] != args.username or identity["is_superuser"]:
        raise RuntimeError("registered Taiji identity is incorrect")
    if len(identity["tenants"]) != 1:
        raise RuntimeError("registered user did not receive exactly one workspace")
    personal = identity["current_tenant"]
    if personal["type"] != "personal" or identity["role"] != "tenant_admin":
        raise RuntimeError("registered user does not own a personal workspace")

    logout = browser.post(
        f"{base_url}/api/v1/auth/logout",
        headers={"X-CSRF-Token": identity["csrf_token"]},
        timeout=30,
    )
    logout.raise_for_status()
    print(
        "OIDC registration smoke passed: "
        f"user={args.username} workspace={personal['name']}"
    )


def _allow_localhost_secure_cookies(browser: requests.Session, response_url: str):
    parsed = urlparse(response_url)
    if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}:
        for cookie in browser.cookies:
            cookie.secure = False


if __name__ == "__main__":
    main()
