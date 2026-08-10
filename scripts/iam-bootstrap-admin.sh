#!/usr/bin/env bash
set -euo pipefail

if [[ "${IAM_BOOTSTRAP_ENABLED:-true}" != "true" ]]; then
  echo "IAM business administrator bootstrap is disabled."
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
