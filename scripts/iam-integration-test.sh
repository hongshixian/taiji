#!/usr/bin/env bash
set -euo pipefail

base_url="${IAM_PUBLIC_URL:-http://localhost:8180}"
realm="${IAM_REALM:-fangcun}"
web_secret="${TAIJI_OIDC_CLIENT_SECRET:-taiji-web-dev-secret}"
reconciler_secret="${TAIJI_RECONCILER_CLIENT_SECRET:-taiji-reconciler-dev-secret}"
suffix="$(date +%s)-$$"
username="iam-integration-${suffix}"
email="${username}@example.test"
password="IntegrationPass1!"
tenant_name="IAM integration ${suffix}"
idempotency_key="iam-integration-${suffix}"
user_id=""
tenant_org_id=""
personal_org_id=""
pending_org_id=""
web_client_uuid=""

kcadm() {
  docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh "$@"
}

cleanup() {
  set +e
  [[ -n "${tenant_org_id}" ]] && kcadm delete "organizations/${tenant_org_id}" -r "${realm}" >/dev/null
  [[ -n "${pending_org_id}" ]] && kcadm delete "organizations/${pending_org_id}" -r "${realm}" >/dev/null
  [[ -n "${personal_org_id}" ]] && kcadm delete "organizations/${personal_org_id}" -r "${realm}" >/dev/null
  [[ -n "${user_id}" ]] && kcadm delete "users/${user_id}" -r "${realm}" >/dev/null
  [[ -n "${web_client_uuid}" ]] && \
    kcadm update "clients/${web_client_uuid}" -r "${realm}" -s directAccessGrantsEnabled=false >/dev/null
  kcadm remove-roles -r "${realm}" \
    --uusername service-account-taiji-reconciler \
    --rolename platform_admin >/dev/null 2>&1
}
trap cleanup EXIT

docker compose exec -T keycloak bash -lc \
  '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null'

web_client_uuid="$(kcadm get clients -r "${realm}" -q clientId=taiji-web \
  --fields id --format csv --noquotes | sed -n '1p')"
[[ -n "${web_client_uuid}" ]]
kcadm update "clients/${web_client_uuid}" -r "${realm}" -s directAccessGrantsEnabled=true >/dev/null
kcadm add-roles -r "${realm}" \
  --uusername service-account-taiji-reconciler \
  --rolename platform_admin >/dev/null

admin_token_response="$(curl -sS -X POST "${base_url}/realms/${realm}/protocol/openid-connect/token" \
  -d grant_type=client_credentials \
  -d client_id=taiji-reconciler \
  -d "client_secret=${reconciler_secret}")"
admin_token="$(jq -er .access_token <<<"${admin_token_response}")"

pending_body="$(jq -nc --arg name "Pending IAM integration ${suffix}" --arg email "${email}" \
  '{name: $name, initialAdmin: $email}')"
pending_created="$(curl -fsS -X POST "${base_url}/realms/${realm}/taiji-iam/v1/tenants" \
  -H "Authorization: Bearer ${admin_token}" \
  -H "Idempotency-Key: pending-${idempotency_key}" \
  -H 'Content-Type: application/json' \
  -d "${pending_body}")"
pending_tenant_id="$(jq -er '.id | select(length == 36)' <<<"${pending_created}")"
pending_org_id="$(jq -er .keycloak_org_id <<<"${pending_created}")"
jq -e '.lifecycle_status == "pending" and .enabled == true' <<<"${pending_created}" >/dev/null

kcadm create users -r "${realm}" \
  -s "username=${username}" \
  -s "email=${email}" \
  -s firstName=IAM \
  -s lastName=Integration \
  -s enabled=true \
  -s emailVerified=false >/dev/null
user_id="$(kcadm get users -r "${realm}" -q exact=true -q "username=${username}" \
  --fields id --format csv --noquotes | sed -n '1p')"
kcadm set-password -r "${realm}" --username "${username}" \
  --new-password "${password}" >/dev/null

user_token_response="$(curl -sS -X POST "${base_url}/realms/${realm}/protocol/openid-connect/token" \
  -d grant_type=password \
  -d client_id=taiji-web \
  -d "client_secret=${web_secret}" \
  -d "username=${username}" \
  -d "password=${password}")"
user_token="$(jq -er .access_token <<<"${user_token_response}")"

my_tenants="$(curl -fsS "${base_url}/realms/${realm}/taiji-iam/v1/me/tenants" \
  -H "Authorization: Bearer ${user_token}")"
jq -e --arg pending "${pending_tenant_id}" \
  '.tenants | length == 2
    and any(.tenant_type == "personal" and .role == "tenant_admin")
    and any(.id == $pending and .lifecycle_status == "active" and .role == "tenant_admin")' \
  <<<"${my_tenants}" >/dev/null
personal_org_id="$(jq -er '.tenants[] | select(.tenant_type == "personal") | .keycloak_org_id' \
  <<<"${my_tenants}")"
personal_tenant_id="$(jq -er '.tenants[] | select(.tenant_type == "personal") | .id' \
  <<<"${my_tenants}")"

create_body="$(jq -nc --arg name "${tenant_name}" '{name: $name, initialAdmin: "admin"}')"
created="$(curl -fsS -X POST "${base_url}/realms/${realm}/taiji-iam/v1/tenants" \
  -H "Authorization: Bearer ${admin_token}" \
  -H "Idempotency-Key: ${idempotency_key}" \
  -H 'Content-Type: application/json' \
  -d "${create_body}")"
tenant_id="$(jq -er '.id | select(length == 36)' <<<"${created}")"
tenant_org_id="$(jq -er .keycloak_org_id <<<"${created}")"

service_account_code="$(curl -sS -o /tmp/taiji-iam-service-account.json -w '%{http_code}' -X POST \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants/${tenant_id}/members" \
  -H "Authorization: Bearer ${admin_token}" \
  -H 'Content-Type: application/json' \
  -d '{"identifier":"service-account-taiji-reconciler","role":"member"}')"
[[ "${service_account_code}" == 409 ]]
jq -e '.code == "service_account_forbidden"' /tmp/taiji-iam-service-account.json >/dev/null

repeated="$(curl -fsS -X POST "${base_url}/realms/${realm}/taiji-iam/v1/tenants" \
  -H "Authorization: Bearer ${admin_token}" \
  -H "Idempotency-Key: ${idempotency_key}" \
  -H 'Content-Type: application/json' \
  -d "${create_body}")"
[[ "$(jq -r .id <<<"${repeated}")" == "${tenant_id}" ]]

conflict_code="$(curl -sS -o /tmp/taiji-iam-conflict.json -w '%{http_code}' -X POST \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants" \
  -H "Authorization: Bearer ${admin_token}" \
  -H "Idempotency-Key: ${idempotency_key}" \
  -H 'Content-Type: application/json' \
  -d '{"name":"different","initialAdmin":"admin"}')"
[[ "${conflict_code}" == 409 ]]
jq -e '.code == "idempotency_conflict"' /tmp/taiji-iam-conflict.json >/dev/null

member="$(curl -fsS -X POST \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants/${tenant_id}/members" \
  -H "Authorization: Bearer ${admin_token}" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg identifier "${username}" '{identifier: $identifier, role: "member"}')")"
global_user_id="$(jq -er .id <<<"${member}")"

my_tenants="$(curl -fsS "${base_url}/realms/${realm}/taiji-iam/v1/me/tenants" \
  -H "Authorization: Bearer ${user_token}")"
jq -e --arg id "${tenant_id}" '.tenants | length == 3 and any(.id == $id and .role == "member")' \
  <<<"${my_tenants}" >/dev/null

forbidden_code="$(curl -sS -o /tmp/taiji-iam-forbidden.json -w '%{http_code}' \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants/${tenant_id}/members" \
  -H "Authorization: Bearer ${user_token}")"
[[ "${forbidden_code}" == 403 ]]

personal_code="$(curl -sS -o /tmp/taiji-iam-personal.json -w '%{http_code}' -X POST \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants/${personal_tenant_id}/members" \
  -H "Authorization: Bearer ${user_token}" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg identifier "${username}" '{identifier: $identifier, role: "member"}')")"
[[ "${personal_code}" == 409 ]]
jq -e '.code == "personal_tenant_immutable"' /tmp/taiji-iam-personal.json >/dev/null

personal_list_code="$(curl -sS -o /tmp/taiji-iam-personal-list.json -w '%{http_code}' \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants/${personal_tenant_id}/members" \
  -H "Authorization: Bearer ${user_token}")"
[[ "${personal_list_code}" == 409 ]]
jq -e '.code == "personal_tenant_immutable"' /tmp/taiji-iam-personal-list.json >/dev/null

platform_admin="$(curl -fsS -X POST \
  "${base_url}/realms/${realm}/taiji-iam/v1/platform-admins" \
  -H "Authorization: Bearer ${admin_token}" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg identifier "${username}" '{identifier: $identifier}')")"
[[ "$(jq -r .id <<<"${platform_admin}")" == "${global_user_id}" ]]
jq -e '.platform_admin == true' <<<"${platform_admin}" >/dev/null

platform_admins="$(curl -fsS \
  "${base_url}/realms/${realm}/taiji-iam/v1/platform-admins" \
  -H "Authorization: Bearer ${admin_token}")"
jq -e --arg id "${global_user_id}" \
  '.platform_admins | any(.id == $id and .platform_admin == true)' \
  <<<"${platform_admins}" >/dev/null

user_token_response="$(curl -sS -X POST "${base_url}/realms/${realm}/protocol/openid-connect/token" \
  -d grant_type=password \
  -d client_id=taiji-web \
  -d "client_secret=${web_secret}" \
  -d "username=${username}" \
  -d "password=${password}")"
user_token="$(jq -er .access_token <<<"${user_token_response}")"
self_revoke_code="$(curl -sS -o /tmp/taiji-iam-platform-self.json -w '%{http_code}' -X DELETE \
  "${base_url}/realms/${realm}/taiji-iam/v1/platform-admins/${global_user_id}" \
  -H "Authorization: Bearer ${user_token}")"
[[ "${self_revoke_code}" == 409 ]]
jq -e '.code == "cannot_revoke_self"' /tmp/taiji-iam-platform-self.json >/dev/null

platform_admin="$(curl -fsS -X DELETE \
  "${base_url}/realms/${realm}/taiji-iam/v1/platform-admins/${global_user_id}" \
  -H "Authorization: Bearer ${admin_token}")"
jq -e '.platform_admin == false' <<<"${platform_admin}" >/dev/null

members="$(curl -fsS \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants/${tenant_id}/members" \
  -H "Authorization: Bearer ${admin_token}")"
admin_global_id="$(jq -er '.members[] | select(.username == "admin") | .id' <<<"${members}")"
last_admin_code="$(curl -sS -o /tmp/taiji-iam-last-admin.json -w '%{http_code}' -X DELETE \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants/${tenant_id}/members/${admin_global_id}" \
  -H "Authorization: Bearer ${admin_token}")"
[[ "${last_admin_code}" == 409 ]]
jq -e '.code == "last_tenant_admin"' /tmp/taiji-iam-last-admin.json >/dev/null

invitation="$(curl -fsS -X POST \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants/${tenant_id}/members" \
  -H "Authorization: Bearer ${admin_token}" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg identifier "pending-${suffix}@example.test" \
    '{identifier: $identifier, role: "member"}')")"
invitation_id="$(jq -er .invitation_id <<<"${invitation}")"
curl -fsS -X POST \
  "${base_url}/realms/${realm}/taiji-iam/v1/invitations/${invitation_id}/resend" \
  -H "Authorization: Bearer ${admin_token}" >/dev/null
revoke_code="$(curl -sS -o /dev/null -w '%{http_code}' -X DELETE \
  "${base_url}/realms/${realm}/taiji-iam/v1/invitations/${invitation_id}" \
  -H "Authorization: Bearer ${admin_token}")"
[[ "${revoke_code}" == 204 ]]

curl -fsS -X DELETE \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants/${tenant_id}/members/${global_user_id}" \
  -H "Authorization: Bearer ${admin_token}" >/dev/null
curl -fsS -X DELETE \
  "${base_url}/realms/${realm}/taiji-iam/v1/tenants/${tenant_id}/members/${global_user_id}" \
  -H "Authorization: Bearer ${admin_token}" >/dev/null

my_tenants="$(curl -fsS "${base_url}/realms/${realm}/taiji-iam/v1/me/tenants" \
  -H "Authorization: Bearer ${user_token}")"
jq -e --arg pending "${pending_tenant_id}" \
  '.tenants | length == 2
    and any(.tenant_type == "personal")
    and any(.id == $pending and .role == "tenant_admin")' <<<"${my_tenants}" >/dev/null

event_count="$(docker compose exec -T nats wget -qO- \
  'http://127.0.0.1:8222/jsz?streams=true' | jq -er '.messages | select(. > 0)')"
if docker compose logs --since=5m keycloak | grep -q 'Unable to publish IAM event'; then
  echo "IAM event publisher reported a failure" >&2
  exit 1
fi

echo "IAM integration test passed (${event_count} persisted events)."
