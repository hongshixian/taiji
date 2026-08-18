#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose() {
  docker compose --env-file "${repo_root}/deploy/taiji-docker/.env" \
    -f "${repo_root}/deploy/taiji-docker/docker-compose.yml" "$@"
}

base_url="${IAM_PUBLIC_URL:-http://localhost:8180}"
realm="${IAM_REALM:-fangcun}"
migrator_secret="${TAIJI_MIGRATOR_CLIENT_SECRET:-taiji-migrator-dev-secret}"
web_secret="${TAIJI_OIDC_CLIENT_SECRET:-taiji-web-dev-secret}"
suffix="$(date +%s)-$$"
username="iam-migrate-${suffix}"
email="${username}@example.test"
password="CorrectHorse1!"
user_global_id="$(cat /proc/sys/kernel/random/uuid)"
tenant_global_id="$(cat /proc/sys/kernel/random/uuid)"
legacy_hash='scrypt:32768:8:1$ffpn1fRbzS2oh0HT$4021e1132568b96d9ff73a88cb54ba0455ec0ad8088a13651f13154680f3e32cf484bc54742bd13487e8d714b08ad3bd94bfea0324780f26380a126a64e10da8'
user_subject=""
tenant_org_id=""
personal_org_id=""
web_client_uuid=""
original_direct_grants="false"

kcadm() {
  compose exec -T keycloak /opt/keycloak/bin/kcadm.sh "$@"
}

cleanup() {
  set +e
  [[ -n "${tenant_org_id}" ]] && kcadm delete "organizations/${tenant_org_id}" -r "${realm}" >/dev/null
  [[ -n "${personal_org_id}" ]] && kcadm delete "organizations/${personal_org_id}" -r "${realm}" >/dev/null
  [[ -n "${user_subject}" ]] && kcadm delete "users/${user_subject}" -r "${realm}" >/dev/null
  if [[ -n "${web_client_uuid}" ]]; then
    kcadm update "clients/${web_client_uuid}" -r "${realm}" \
      -s "directAccessGrantsEnabled=${original_direct_grants}" >/dev/null
  fi
  rm -f /tmp/taiji-iam-migration-wrong.json
}
trap cleanup EXIT
trap 'echo "IAM migration integration test failed near line ${LINENO}." >&2' ERR

compose exec -T keycloak bash -lc \
  '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null'

web_client_uuid="$(kcadm get clients -r "${realm}" -q clientId=taiji-web \
  --fields id --format csv --noquotes | sed -n '1p')"
[[ -n "${web_client_uuid}" ]]
original_direct_grants="$(kcadm get "clients/${web_client_uuid}" -r "${realm}" \
  --fields directAccessGrantsEnabled --format csv --noquotes | sed -n '1p')"
kcadm update "clients/${web_client_uuid}" -r "${realm}" \
  -s directAccessGrantsEnabled=true >/dev/null

migrator_token_response="$(curl -sS -X POST \
  "${base_url}/realms/${realm}/protocol/openid-connect/token" \
  -d grant_type=client_credentials \
  -d client_id=taiji-migrator \
  -d "client_secret=${migrator_secret}")"
migrator_token="$(jq -er .access_token <<<"${migrator_token_response}")"

tenant_body="$(jq -nc --arg name "Migrated tenant ${suffix}" \
  '{name: $name, enabled: true, protectedTenant: true}')"
tenant_response="$(curl -fsS -X PUT \
  "${base_url}/realms/${realm}/taiji-iam/v1/migration/tenants/${tenant_global_id}" \
  -H "Authorization: Bearer ${migrator_token}" \
  -H 'Content-Type: application/json' -d "${tenant_body}")"
tenant_org_id="$(jq -er .keycloak_org_id <<<"${tenant_response}")"
jq -e --arg id "${tenant_global_id}" \
  '.id == $id and .tenant_type == "enterprise" and .protected == true' \
  <<<"${tenant_response}" >/dev/null

user_body="$(jq -nc \
  --arg username "${username}" \
  --arg email "${email}" \
  --arg legacy "${legacy_hash}" \
  '{username: $username, email: $email, enabled: true, platformAdmin: false,
    linkExisting: false, legacyPasswordHash: $legacy}')"
user_response="$(curl -fsS -X PUT \
  "${base_url}/realms/${realm}/taiji-iam/v1/migration/users/${user_global_id}" \
  -H "Authorization: Bearer ${migrator_token}" \
  -H 'Content-Type: application/json' -d "${user_body}")"
user_subject="$(jq -er .keycloak_subject <<<"${user_response}")"
personal_org_id="$(jq -er .personal_tenant.keycloak_org_id <<<"${user_response}")"
jq -e '.created == true and .password_imported == true
  and .personal_tenant.tenant_type == "personal"
  and .personal_tenant.role == "tenant_admin"' <<<"${user_response}" >/dev/null

membership_body='{"role":"member","active":true}'
membership_response="$(curl -fsS -X PUT \
  "${base_url}/realms/${realm}/taiji-iam/v1/migration/tenants/${tenant_global_id}/members/${user_global_id}" \
  -H "Authorization: Bearer ${migrator_token}" \
  -H 'Content-Type: application/json' -d "${membership_body}")"
jq -e '.active == true and .role == "member"' <<<"${membership_response}" >/dev/null

credentials_before="$(kcadm get "users/${user_subject}/credentials" -r "${realm}")"
grep -q 'taiji-legacy' <<<"${credentials_before}"

wrong_code="$(curl -sS -o /tmp/taiji-iam-migration-wrong.json -w '%{http_code}' -X POST \
  "${base_url}/realms/${realm}/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=taiji-web -d "client_secret=${web_secret}" \
  -d "username=${username}" -d password=WrongPassword1!)"
[[ "${wrong_code}" == "400" || "${wrong_code}" == "401" ]]
jq -e '.error == "invalid_grant"' /tmp/taiji-iam-migration-wrong.json >/dev/null

user_token_response="$(curl -fsS -X POST \
  "${base_url}/realms/${realm}/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=taiji-web -d "client_secret=${web_secret}" \
  -d "username=${username}" -d "password=${password}")"
user_token="$(jq -er .access_token <<<"${user_token_response}")"

my_tenants="$(curl -fsS \
  "${base_url}/realms/${realm}/taiji-iam/v1/me/tenants" \
  -H "Authorization: Bearer ${user_token}")"
jq -e --arg enterprise "${tenant_global_id}" \
  '.platform_admin == false
    and (.tenants | any(.tenant_type == "personal" and .role == "tenant_admin"))
    and (.tenants | any(.id == $enterprise and .role == "member"))' \
  <<<"${my_tenants}" >/dev/null

credentials_after="$(kcadm get "users/${user_subject}/credentials" -r "${realm}")"
! grep -q 'taiji-legacy' <<<"${credentials_after}"

platform_admin_body="$(jq '.platformAdmin = true' <<<"${user_body}")"
curl -fsS -X PUT \
  "${base_url}/realms/${realm}/taiji-iam/v1/migration/users/${user_global_id}" \
  -H "Authorization: Bearer ${migrator_token}" \
  -H 'Content-Type: application/json' -d "${platform_admin_body}" >/dev/null
platform_token="$(curl -fsS -X POST \
  "${base_url}/realms/${realm}/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=taiji-web -d "client_secret=${web_secret}" \
  -d "username=${username}" -d "password=${password}" | jq -er .access_token)"
curl -fsS "${base_url}/realms/${realm}/taiji-iam/v1/me/tenants" \
  -H "Authorization: Bearer ${platform_token}" | jq -e '.platform_admin == true' >/dev/null

repeated_user="$(curl -fsS -X PUT \
  "${base_url}/realms/${realm}/taiji-iam/v1/migration/users/${user_global_id}" \
  -H "Authorization: Bearer ${migrator_token}" \
  -H 'Content-Type: application/json' -d "${user_body}")"
jq -e '.created == false and .password_imported == false' <<<"${repeated_user}" >/dev/null
revoked_token="$(curl -fsS -X POST \
  "${base_url}/realms/${realm}/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=taiji-web -d "client_secret=${web_secret}" \
  -d "username=${username}" -d "password=${password}" | jq -er .access_token)"
curl -fsS "${base_url}/realms/${realm}/taiji-iam/v1/me/tenants" \
  -H "Authorization: Bearer ${revoked_token}" | jq -e '.platform_admin == false' >/dev/null

printf '%s\n' \
  "IAM migration integration test passed." \
  "- legacy Werkzeug password verified" \
  "- credential automatically rehashed by Keycloak" \
  "- personal and enterprise memberships visible" \
  "- platform administrator grant and revocation synchronized" \
  "- migration API idempotency verified"
