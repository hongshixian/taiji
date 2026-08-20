#!/usr/bin/env python3
"""Exercise Taiji-owned tenant workflows through the browser-facing OIDC BFF."""

import argparse
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests


def login(base_url: str, username: str, password: str):
    browser = requests.Session()
    response = browser.get(f"{base_url}/api/v1/auth/login", timeout=30)
    response.raise_for_status()
    callback_seen = False
    for _step in range(4):
        _allow_localhost_secure_cookies(browser, response.url)
        form = BeautifulSoup(response.text, "html.parser").select_one("#kc-form-login")
        if form is None:
            break
        fields = {
            element["name"]: element.get("value", "")
            for element in form.select("input[name], button[name]")
        }
        if form.select_one("input[name=username]"):
            fields["username"] = username
        if form.select_one("input[name=password]"):
            fields["password"] = password
        fields["login"] = "Sign In"
        if not form.select_one("input[name=rememberMe][checked]"):
            fields.pop("rememberMe", None)
        response = browser.post(form["action"], data=fields, timeout=30)
        callback_seen = any(
            urlparse(item.url).path == "/api/v1/auth/callback"
            for item in response.history
        )
        if callback_seen:
            break
    if not callback_seen:
        raise RuntimeError(f"OIDC callback was not reached for {username}")
    return browser, get_me(browser, base_url)


def get_me(browser: requests.Session, base_url: str):
    response = browser.get(f"{base_url}/api/v1/auth/me", timeout=30)
    response.raise_for_status()
    return response.json()["data"]


def post(browser, url, csrf_token, payload=None):
    response = browser.post(
        url,
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:28080")
    parser.add_argument("--admin-username", required=True)
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--member-username", required=True)
    parser.add_argument("--member-password", required=True)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    admin_browser, admin = login(
        base_url, args.admin_username, args.admin_password
    )
    if not admin["is_superuser"]:
        raise RuntimeError("platform_admin did not bootstrap local superuser authority")

    member_browser, member = login(
        base_url, args.member_username, args.member_password
    )
    if member["is_superuser"] or len(member["tenants"]) != 1:
        raise RuntimeError("member did not start with exactly one personal workspace")

    created = post(
        admin_browser,
        f"{base_url}/api/v1/superadmin/tenants",
        admin["csrf_token"],
        {
            "name": "Docker Verification Enterprise",
            "initial_admin": args.admin_username,
        },
    )["data"]
    tenant_id = created["id"]
    if created["tenant_type"] != "enterprise":
        raise RuntimeError("created tenant is not an enterprise tenant")

    post(
        admin_browser,
        f"{base_url}/api/v1/superadmin/tenants/{tenant_id}/members",
        admin["csrf_token"],
        {"identifier": args.member_username, "role": "member"},
    )

    tenants = member_browser.get(
        f"{base_url}/api/v1/auth/tenants", timeout=30
    )
    tenants.raise_for_status()
    tenant_options = tenants.json()["data"]
    enterprise = next(
        (item for item in tenant_options if item["id"] == tenant_id), None
    )
    if enterprise is None or enterprise["role"] != "member":
        raise RuntimeError("member cannot see the assigned enterprise tenant")

    switched = post(
        member_browser,
        f"{base_url}/api/v1/auth/switch-tenant",
        member["csrf_token"],
        {"tenant_id": tenant_id},
    )["data"]
    if switched["tenant"]["id"] != tenant_id or switched["role"] != "member":
        raise RuntimeError("member tenant switch did not establish local membership")

    password = member_browser.put(
        f"{base_url}/api/v1/auth/password",
        headers={"X-CSRF-Token": member["csrf_token"]},
        timeout=30,
    )
    password.raise_for_status()
    account_url = password.json()["data"]["account_url"]
    if not urlparse(account_url).path.startswith("/iam/realms/fangcun/account"):
        raise RuntimeError("password management URL is not under the Taiji origin")
    account_page = member_browser.get(account_url, timeout=30)
    account_page.raise_for_status()

    post(
        member_browser,
        f"{base_url}/api/v1/auth/logout",
        member["csrf_token"],
    )
    post(
        admin_browser,
        f"{base_url}/api/v1/auth/logout",
        admin["csrf_token"],
    )
    if member_browser.get(f"{base_url}/api/v1/auth/me", timeout=30).status_code != 401:
        raise RuntimeError("member Taiji session remained usable after logout")

    print(
        "OIDC platform smoke passed: "
        f"tenant={tenant_id} admin={args.admin_username} member={args.member_username}"
    )


def _allow_localhost_secure_cookies(browser: requests.Session, response_url: str):
    parsed = urlparse(response_url)
    if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}:
        for cookie in browser.cookies:
            cookie.secure = False


if __name__ == "__main__":
    main()
