#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${TAIJI_ENV_FILE:-${repo_root}/deploy/taiji-docker/.env}"
namespace="${KUBE_NAMESPACE:-lihao}"

if [[ ! -f "${env_file}" ]]; then
  echo "Missing ${env_file}; create it from deploy/taiji-docker/.env.example first." >&2
  exit 1
fi

get_env() {
  local key="$1"
  local default_value="${2-}"
  local line
  line="$(grep -m1 -E "^${key}=" "${env_file}" || true)"
  if [[ -n "${line}" ]]; then
    printf '%s' "${line#*=}"
  else
    printf '%s' "${default_value}"
  fi
}

postgres_user="$(get_env POSTGRES_USER taiji)"
postgres_password="$(get_env POSTGRES_PASSWORD taiji_pw)"
postgres_db="$(get_env POSTGRES_DB taiji)"
keycloak_db="$(get_env KEYCLOAK_DB keycloak)"

require_secure_value() {
  local key="$1"
  local value="$2"
  local insecure_value="$3"
  if [[ -z "${value}" || "${value}" == "${insecure_value}" ]]; then
    echo "${key} is missing or still uses the development default." >&2
    exit 1
  fi
}

secret_key="$(get_env SECRET_KEY change-me-in-production)"
jwt_secret_key="$(get_env JWT_SECRET_KEY change-me-in-production)"
keycloak_admin_password="$(get_env KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD dev-only-change-me)"
oidc_client_secret="$(get_env TAIJI_OIDC_CLIENT_SECRET taiji-web-dev-secret)"

require_secure_value POSTGRES_PASSWORD "${postgres_password}" taiji_pw
require_secure_value SECRET_KEY "${secret_key}" change-me-in-production
require_secure_value JWT_SECRET_KEY "${jwt_secret_key}" change-me-in-production
require_secure_value KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD "${keycloak_admin_password}" dev-only-change-me
require_secure_value TAIJI_OIDC_CLIENT_SECRET "${oidc_client_secret}" taiji-web-dev-secret

for value_name in postgres_password; do
  value="${!value_name}"
  if grep -qE '[@:/?#%]' <<<"${value}"; then
    echo "${value_name} contains URL-reserved characters; use a URL-safe value." >&2
    exit 1
  fi
done

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
kubectl create secret generic taiji-secrets \
  --namespace "${namespace}" \
  --from-literal="POSTGRES_USER=${postgres_user}" \
  --from-literal="POSTGRES_PASSWORD=${postgres_password}" \
  --from-literal="POSTGRES_DB=${postgres_db}" \
  --from-literal="KEYCLOAK_DB=${keycloak_db}" \
  --from-literal="KC_DB_URL=jdbc:postgresql://postgres:5432/${keycloak_db}" \
  --from-literal="DATABASE_URL=postgresql+psycopg://${postgres_user}:${postgres_password}@postgres:5432/${postgres_db}" \
  --from-literal="SECRET_KEY=${secret_key}" \
  --from-literal="JWT_SECRET_KEY=${jwt_secret_key}" \
  --from-literal="KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME=$(get_env KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME kcadmin)" \
  --from-literal="KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD=${keycloak_admin_password}" \
  --from-literal="TAIJI_OIDC_CLIENT_SECRET=${oidc_client_secret}" \
  --from-literal="ADMIN_USERNAME=$(get_env ADMIN_USERNAME admin)" \
  --from-literal="ADMIN_EMAIL=$(get_env ADMIN_EMAIL admin@taiji.local)" \
  --from-literal="ADMIN_PASSWORD=$(get_env ADMIN_PASSWORD)" \
  --from-literal="IAM_BOOTSTRAP_ADMIN_EMAIL=$(get_env IAM_BOOTSTRAP_ADMIN_EMAIL admin@taiji.local)" \
  --dry-run=client -o yaml | kubectl apply -f -
