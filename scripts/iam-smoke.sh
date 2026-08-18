#!/usr/bin/env sh
set -eu

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
compose() {
  docker compose --env-file "${repo_root}/deploy/taiji-docker/.env" \
    -f "${repo_root}/deploy/taiji-docker/docker-compose.yml" "$@"
}

iam_url="${IAM_PUBLIC_URL:-http://localhost:${KEYCLOAK_PORT:-8180}}"
realm="${IAM_REALM:-fangcun}"

discovery="$(curl -fsS "${iam_url}/realms/${realm}/.well-known/openid-configuration")"
printf '%s' "$discovery" | grep -q "\"issuer\":\"${iam_url}/realms/${realm}\""

extension_health="$(curl -fsS "${iam_url}/realms/${realm}/taiji-iam/health")"
printf '%s' "$extension_health" | grep -q '"status":"ok"'
printf '%s' "$extension_health" | grep -q '"provider":"taiji-iam"'

nats_container="$(compose ps -q nats)"
test -n "$nats_container"
docker exec "$nats_container" wget -qO- http://127.0.0.1:8222/jsz | grep -q '"store_dir"'

printf 'IAM smoke test passed (%s, realm=%s)\n' "$iam_url" "$realm"
