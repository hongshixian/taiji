#!/usr/bin/env bash
set -euo pipefail

if [[ "${IAM_BOOTSTRAP_ENABLED:-true}" != "true" \
      && "${IAM_REALM_RECONCILE_ENABLED:-true}" != "true" ]]; then
  echo "IAM bootstrap and realm reconciliation are disabled."
  exit 0
fi

server="${KEYCLOAK_INTERNAL_URL:-http://keycloak:8080}"
realm="${IAM_REALM:-fangcun}"
infra_user="${KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME:?missing infrastructure admin username}"
infra_password="${KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD:?missing infrastructure admin password}"
business_username="admin"
business_email="${IAM_BOOTSTRAP_ADMIN_EMAIL:-admin@taiji.local}"
taiji_public_url="${TAIJI_PUBLIC_URL:?missing Taiji public URL}"
kcadm="/opt/keycloak/bin/kcadm.sh"

"${kcadm}" config credentials \
  --server "${server}" \
  --realm master \
  --user "${infra_user}" \
  --password "${infra_password}" >/dev/null

if [[ "${IAM_REALM_RECONCILE_ENABLED:-true}" == "true" ]]; then
  "${kcadm}" update "realms/${realm}" \
    -s loginTheme=taiji \
    -s accountTheme=fangcun-account \
    -s internationalizationEnabled=true \
    -s 'supportedLocales=["zh-CN","en"]' \
    -s defaultLocale=zh-CN >/dev/null
  echo "IAM themes and locale reconciled."

  "${kcadm}" update users/profile -r "${realm}" \
    -f /opt/keycloak/conf/taiji/user-profile.json >/dev/null
  echo "IAM user profile reconciled."

  reconcile_service_client() {
    local client_id="$1"
    local client_name="$2"
    local client_secret="$3"
    local internal_id
    internal_id="$("${kcadm}" get clients -r "${realm}" \
      -q "clientId=${client_id}" --fields id --format csv --noquotes | sed -n '1p')"
    if [[ -z "${internal_id}" ]]; then
    "${kcadm}" create clients -r "${realm}" \
      -s "clientId=${client_id}" \
      -s "name=${client_name}" \
      -s enabled=true \
      -s publicClient=false \
      -s serviceAccountsEnabled=true \
      -s standardFlowEnabled=false \
      -s directAccessGrantsEnabled=false \
      -s "secret=${client_secret}" >/dev/null
      echo "IAM ${client_id} client created."
    else
      "${kcadm}" update "clients/${internal_id}" -r "${realm}" \
      -s enabled=true \
      -s publicClient=false \
      -s serviceAccountsEnabled=true \
      -s standardFlowEnabled=false \
      -s directAccessGrantsEnabled=false \
      -s "secret=${client_secret}" >/dev/null
      echo "IAM ${client_id} client reconciled."
    fi
  }

  reconcile_service_client \
    taiji-migrator '太极一次性 IAM 迁移工具' \
    "${TAIJI_MIGRATOR_CLIENT_SECRET:?missing migrator client secret}"
  reconcile_service_client \
    taiji-reconciler '太极 IAM 对账服务' \
    "${TAIJI_RECONCILER_CLIENT_SECRET:?missing reconciler client secret}"

  web_id="$("${kcadm}" get clients -r "${realm}" \
    -q clientId=taiji-web --fields id --format csv --noquotes | sed -n '1p')"
  if [[ -z "${web_id}" ]]; then
    echo "IAM taiji-web client is missing; restore the realm baseline before startup." >&2
    exit 1
  fi
  "${kcadm}" update "clients/${web_id}" -r "${realm}" \
    -s enabled=true \
    -s publicClient=false \
    -s serviceAccountsEnabled=false \
    -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=false \
    -s "redirectUris=[\"${taiji_public_url}/api/v1/auth/callback\"]" \
    -s "webOrigins=[\"${taiji_public_url}\"]" \
    -s "attributes.\"post.logout.redirect.uris\"=\"${taiji_public_url}/*\"" \
    -s "secret=${TAIJI_OIDC_CLIENT_SECRET:?missing OIDC client secret}" >/dev/null
  echo "IAM taiji-web client reconciled."

  account_console_id="$("${kcadm}" get clients -r "${realm}" \
    -q clientId=account-console --fields id --format csv --noquotes | sed -n '1p')"
  if [[ -z "${account_console_id}" ]]; then
    echo "IAM account-console client is missing; restore the realm baseline before startup." >&2
    exit 1
  fi
  "${kcadm}" update "clients/${account_console_id}" -r "${realm}" \
    -s "webOrigins=[\"${IAM_PUBLIC_URL:?missing IAM public URL}\"]" >/dev/null
  echo "IAM account-console origin reconciled."
fi

if [[ "${IAM_BOOTSTRAP_ENABLED:-true}" != "true" ]]; then
  echo "IAM business administrator bootstrap is disabled."
  exit 0
fi

realm_attributes="$("${kcadm}" get "realms/${realm}")"
if grep -Eq '"fc_bootstrap_completed"[[:space:]]*:[[:space:]]*"?true"?' <<<"${realm_attributes}"; then
  echo "IAM business administrator bootstrap was already completed."
  exit 0
fi

existing_id="$("${kcadm}" get users -r "${realm}" \
  -q exact=true -q "username=${business_username}" \
  --fields id --format csv --noquotes | sed -n '1p')"
if [[ -n "${existing_id}" ]]; then
  echo "Refusing to overwrite existing IAM user '${business_username}' without a bootstrap marker." >&2
  echo "Migrate or recover this account explicitly, then set realm attribute fc_bootstrap_completed=true." >&2
  exit 1
fi

random_part="$(dd if=/dev/urandom bs=48 count=1 2>/dev/null | base64 | tr -dc 'A-Za-z0-9' | cut -c1-24)"
temporary_password="${random_part}!Aa1"

"${kcadm}" create users -r "${realm}" \
  -s "username=${business_username}" \
  -s "email=${business_email}" \
  -s enabled=true \
  -s emailVerified=false >/dev/null
"${kcadm}" set-password -r "${realm}" \
  --username "${business_username}" \
  --new-password "${temporary_password}" \
  --temporary
"${kcadm}" add-roles -r "${realm}" \
  --uusername "${business_username}" \
  --rolename platform_admin
"${kcadm}" update "realms/${realm}" -s 'attributes.fc_bootstrap_completed="true"' >/dev/null

printf '%s\n' \
  "IAM bootstrap completed." \
  "username: ${business_username}" \
  "temporary password: ${temporary_password}" \
  "This password is shown once. Sign in and replace it immediately."
