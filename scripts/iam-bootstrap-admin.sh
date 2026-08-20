#!/usr/bin/env bash
set -euo pipefail

if [[ "${IAM_BOOTSTRAP_ENABLED:-true}" != "true" \
      && "${IAM_REALM_RECONCILE_ENABLED:-true}" != "true" ]]; then
  echo "Login bootstrap and realm reconciliation are disabled."
  exit 0
fi

server="${KEYCLOAK_INTERNAL_URL:-http://keycloak:8080}"
realm="${IAM_REALM:-fangcun}"
infra_user="${KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME:?missing infrastructure admin username}"
infra_password="${KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD:?missing infrastructure admin password}"
business_username="admin"
business_email="${IAM_BOOTSTRAP_ADMIN_EMAIL:-admin@taiji.local}"
taiji_public_url="${TAIJI_PUBLIC_URL:?missing Taiji public URL}"
taiji_public_urls="${TAIJI_PUBLIC_URLS:-${taiji_public_url}}"
kcadm="/opt/keycloak/bin/kcadm.sh"

redirect_uris=()
web_origins=()
logout_uris=""
IFS=',' read -ra configured_public_urls <<<"${taiji_public_urls}"
configured_public_urls=("${taiji_public_url}" "${configured_public_urls[@]}")
declare -A seen_public_urls=()
for configured_url in "${configured_public_urls[@]}"; do
  configured_url="$(printf '%s' "${configured_url}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's:/*$::')"
  [[ -n "${configured_url}" ]] || continue
  if [[ ! "${configured_url}" =~ ^https?://[^/]+$ ]]; then
    echo "Invalid Taiji public URL: ${configured_url}" >&2
    exit 1
  fi
  [[ -z "${seen_public_urls[${configured_url}]:-}" ]] || continue
  seen_public_urls["${configured_url}"]=1
  redirect_uris+=("\"${configured_url}/api/v1/auth/callback\"")
  web_origins+=("\"${configured_url}\"")
  if [[ -n "${logout_uris}" ]]; then
    logout_uris+="##"
  fi
  logout_uris+="${configured_url}/*"
done
if [[ ${#redirect_uris[@]} -eq 0 ]]; then
  echo "No valid Taiji public URLs configured." >&2
  exit 1
fi
redirect_uris_json="[$(IFS=,; echo "${redirect_uris[*]}")]"
web_origins_json="[$(IFS=,; echo "${web_origins[*]}")]"

"${kcadm}" config credentials \
  --server "${server}" \
  --realm master \
  --user "${infra_user}" \
  --password "${infra_password}" >/dev/null

if [[ "${IAM_REALM_RECONCILE_ENABLED:-true}" == "true" ]]; then
  "${kcadm}" update "realms/${realm}" \
    -s loginTheme=taiji \
    -s accountTheme=fangcun-account \
    -s organizationsEnabled=false \
    -s 'eventsListeners=["jboss-logging"]' \
    -s internationalizationEnabled=true \
    -s 'supportedLocales=["zh-CN","en"]' \
    -s defaultLocale=zh-CN >/dev/null
  echo "Login themes and locale reconciled."

  "${kcadm}" update users/profile -r "${realm}" \
    -f /opt/keycloak/conf/taiji/user-profile.json >/dev/null
  echo "Login user profile reconciled."

  web_id="$("${kcadm}" get clients -r "${realm}" \
    -q clientId=taiji-web --fields id --format csv --noquotes | sed -n '1p')"
  if [[ -z "${web_id}" ]]; then
    echo "Taiji web client is missing; restore the realm baseline before startup." >&2
    exit 1
  fi
  "${kcadm}" update "clients/${web_id}" -r "${realm}" \
    -s enabled=true \
    -s publicClient=false \
    -s serviceAccountsEnabled=false \
    -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=false \
    -s "redirectUris=${redirect_uris_json}" \
    -s "webOrigins=${web_origins_json}" \
    -s "attributes.\"post.logout.redirect.uris\"=\"${logout_uris}\"" \
    -s "secret=${TAIJI_OIDC_CLIENT_SECRET:?missing OIDC client secret}" >/dev/null
  echo "Taiji web client reconciled."

  roles_scope_id="$("${kcadm}" get client-scopes -r "${realm}" \
    --fields id,name --format csv --noquotes \
    | sed -n 's/,roles$//p' | sed -n '1p')"
  if [[ -z "${roles_scope_id}" ]]; then
    echo "Built-in roles client scope is missing." >&2
    exit 1
  fi
  realm_roles_mapper_id="$("${kcadm}" get \
    "client-scopes/${roles_scope_id}/protocol-mappers/models" -r "${realm}" \
    --fields id,name --format csv --noquotes \
    | sed -n 's/,realm roles$//p' | sed -n '1p')"
  if [[ -z "${realm_roles_mapper_id}" ]]; then
    echo "Realm roles protocol mapper is missing." >&2
    exit 1
  fi
  "${kcadm}" update \
    "client-scopes/${roles_scope_id}/protocol-mappers/models/${realm_roles_mapper_id}" \
    -r "${realm}" \
    -s 'config."id.token.claim"="true"' \
    -s 'config."userinfo.token.claim"="true"' >/dev/null
  echo "Platform bootstrap role claim reconciled."

  account_console_id="$("${kcadm}" get clients -r "${realm}" \
    -q clientId=account-console --fields id --format csv --noquotes | sed -n '1p')"
  if [[ -z "${account_console_id}" ]]; then
    echo "Account console client is missing; restore the realm baseline before startup." >&2
    exit 1
  fi
  "${kcadm}" update "clients/${account_console_id}" -r "${realm}" \
    -s "webOrigins=[\"${taiji_public_url}\"]" >/dev/null
  echo "Account console origin reconciled."
fi

if [[ "${IAM_BOOTSTRAP_ENABLED:-true}" != "true" ]]; then
  echo "Taiji platform administrator bootstrap is disabled."
  exit 0
fi

realm_attributes="$("${kcadm}" get "realms/${realm}")"
if grep -Eq '"fc_bootstrap_completed"[[:space:]]*:[[:space:]]*"?true"?' <<<"${realm_attributes}"; then
  echo "Taiji platform administrator bootstrap was already completed."
  exit 0
fi

existing_id="$("${kcadm}" get users -r "${realm}" \
  -q exact=true -q "username=${business_username}" \
  --fields id --format csv --noquotes | sed -n '1p')"
if [[ -n "${existing_id}" ]]; then
  echo "Refusing to overwrite existing login user '${business_username}' without a bootstrap marker." >&2
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
  "Taiji login bootstrap completed." \
  "username: ${business_username}" \
  "temporary password: ${temporary_password}" \
  "This password is shown once. Sign in and replace it immediately."
