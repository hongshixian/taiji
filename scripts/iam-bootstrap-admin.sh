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
kcadm="/opt/keycloak/bin/kcadm.sh"

"${kcadm}" config credentials \
  --server "${server}" \
  --realm master \
  --user "${infra_user}" \
  --password "${infra_password}" >/dev/null

if [[ "${IAM_REALM_RECONCILE_ENABLED:-true}" == "true" ]]; then
  "${kcadm}" update users/profile -r "${realm}" \
    -f /opt/keycloak/conf/taiji/user-profile.json >/dev/null
  echo "IAM user profile reconciled."

  migrator_secret="${TAIJI_MIGRATOR_CLIENT_SECRET:?missing migrator client secret}"
  migrator_id="$("${kcadm}" get clients -r "${realm}" \
    -q clientId=taiji-migrator --fields id --format csv --noquotes | sed -n '1p')"
  if [[ -z "${migrator_id}" ]]; then
    "${kcadm}" create clients -r "${realm}" \
      -s clientId=taiji-migrator \
      -s 'name=太极一次性 IAM 迁移工具' \
      -s enabled=true \
      -s publicClient=false \
      -s serviceAccountsEnabled=true \
      -s standardFlowEnabled=false \
      -s directAccessGrantsEnabled=false \
      -s "secret=${migrator_secret}" >/dev/null
    echo "IAM migrator client created."
  else
    "${kcadm}" update "clients/${migrator_id}" -r "${realm}" \
      -s enabled=true \
      -s publicClient=false \
      -s serviceAccountsEnabled=true \
      -s standardFlowEnabled=false \
      -s directAccessGrantsEnabled=false \
      -s "secret=${migrator_secret}" >/dev/null
    echo "IAM migrator client reconciled."
  fi
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
