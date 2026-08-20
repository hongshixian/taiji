#!/usr/bin/env sh
set -eu

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
compose() {
  docker compose --env-file "${repo_root}/deploy/taiji-docker/.env" \
    -f "${repo_root}/deploy/taiji-docker/docker-compose.yml" "$@"
}

taiji_url="${TAIJI_PUBLIC_URL:-http://localhost:28080}"
iam_url="${IAM_PUBLIC_URL:-${taiji_url}/iam}"
realm="${IAM_REALM:-fangcun}"

discovery="$(curl -fsS "${iam_url}/realms/${realm}/.well-known/openid-configuration")"
printf '%s' "$discovery" | grep -q "\"issuer\":\"${iam_url}/realms/${realm}\""

curl -fsS "${taiji_url}/api/ready" | grep -q '"status":"ok"'
test -n "$(compose ps -q keycloak)"
test -z "$(compose ps -q nats 2>/dev/null || true)"
test -z "$(compose ps -q iam-projector 2>/dev/null || true)"
test -z "$(compose ps -q iam-proxy 2>/dev/null || true)"

printf 'Taiji sign-in smoke test passed (%s, realm=%s)\n' "$iam_url" "$realm"
