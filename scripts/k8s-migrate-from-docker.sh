#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
namespace="${KUBE_NAMESPACE:-lihao}"
env_file="${TAIJI_ENV_FILE:-${repo_root}/deploy/taiji-docker/.env}"
backup_root="${TAIJI_MIGRATION_BACKUP_ROOT:-${repo_root}/../taiji-backups}"
timestamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="${backup_root}/production-migration-${timestamp}"
confirmation="${CONFIRM_TAIJI_PRODUCTION_MIGRATION:-}"

if [[ "${confirmation}" != "docker-to-k8s" ]]; then
  echo "Set CONFIRM_TAIJI_PRODUCTION_MIGRATION=docker-to-k8s to run this destructive target restore." >&2
  exit 1
fi
if [[ ! -f "${env_file}" ]]; then
  echo "Missing Docker environment file: ${env_file}" >&2
  exit 1
fi

compose=(
  docker compose
  --env-file "${env_file}"
  -f "${repo_root}/deploy/taiji-docker/docker-compose.yml"
)
if [[ -f "${repo_root}/deploy/taiji-docker/docker-compose.override.yml" ]]; then
  compose+=( -f "${repo_root}/deploy/taiji-docker/docker-compose.override.yml" )
fi

kubectl_cmd() {
  env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY kubectl "$@"
}

source_apps_stopped=false
helper_created=false
migration_succeeded=false

cleanup() {
  local exit_code=$?
  if [[ "${helper_created}" == true ]]; then
    kubectl_cmd delete pod taiji-migration-files -n "${namespace}" --ignore-not-found --wait=false >/dev/null 2>&1 || true
  fi
  if [[ "${source_apps_stopped}" == true && "${migration_succeeded}" != true ]]; then
    echo "Migration failed; restarting the Docker application services." >&2
    "${compose[@]}" up -d keycloak backend worker frontend >/dev/null 2>&1 || true
  fi
  exit "${exit_code}"
}
trap cleanup EXIT

for command in docker kubectl tar sha256sum diff; do
  command -v "${command}" >/dev/null || { echo "Missing command: ${command}" >&2; exit 1; }
done

mkdir -p "${backup_dir}"
chmod 700 "${backup_dir}"

source_postgres="$("${compose[@]}" ps -q postgres)"
if [[ -z "${source_postgres}" ]]; then
  echo "The Docker PostgreSQL container is not running." >&2
  exit 1
fi
kubectl_cmd wait --for=condition=Ready "pod/taiji-postgres-0" -n "${namespace}" --timeout=120s
source_database="$(docker exec "${source_postgres}" printenv POSTGRES_DB)"
source_keycloak_database="$(grep -m1 '^KEYCLOAK_DB=' "${env_file}" | cut -d= -f2- || true)"
source_keycloak_database="${source_keycloak_database:-keycloak}"
target_database="$(kubectl_cmd get secret taiji-secrets -n "${namespace}" -o jsonpath='{.data.POSTGRES_DB}' | base64 -d)"
target_keycloak_database="$(kubectl_cmd get secret taiji-secrets -n "${namespace}" -o jsonpath='{.data.KEYCLOAK_DB}' | base64 -d)"
if [[ "${source_database}" != "${target_database}" || "${source_keycloak_database}" != "${target_keycloak_database}" ]]; then
  echo "Source and target database names must match for a full migration." >&2
  exit 1
fi

count_tables_docker() {
  local database="$1"
  docker exec -i "${source_postgres}" sh -s -- "${database}" <<'SH' | sort
set -eu
database="$1"
count_query="$(PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$database" -Atc "
  SELECT string_agg(
    format('SELECT %L AS table_name, count(*)::bigint AS row_count FROM %I.%I', tablename, schemaname, tablename),
    ' UNION ALL ' ORDER BY tablename
  )
  FROM pg_tables
  WHERE schemaname = 'public'
")"
PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$database" -AtF '|' -c "$count_query"
SH
}

count_tables_k8s() {
  local database="$1"
  kubectl_cmd exec -i -n "${namespace}" taiji-postgres-0 -- sh -s -- "${database}" <<'SH' | sort
set -eu
database="$1"
count_query="$(PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$database" -Atc "
  SELECT string_agg(
    format('SELECT %L AS table_name, count(*)::bigint AS row_count FROM %I.%I', tablename, schemaname, tablename),
    ' UNION ALL ' ORDER BY tablename
  )
  FROM pg_tables
  WHERE schemaname = 'public'
")"
PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$database" -AtF '|' -c "$count_query"
SH
}

echo "Backing up the current K8s target before replacement."
kubectl_cmd scale deployment taiji-frontend taiji-backend taiji-worker taiji-keycloak -n "${namespace}" --replicas=0
kubectl_cmd delete job taiji-iam-bootstrap -n "${namespace}" --ignore-not-found
for app in frontend backend worker keycloak; do
  while kubectl_cmd get pod -n "${namespace}" -l "app.kubernetes.io/name=${app}" -o name | grep -q .; do sleep 2; done
done

kubectl_cmd exec -n "${namespace}" taiji-postgres-0 -- sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" --format=custom --no-owner --no-acl "$POSTGRES_DB"' \
  >"${backup_dir}/target-taiji-before.dump"
kubectl_cmd exec -i -n "${namespace}" taiji-postgres-0 -- sh -s -- "${target_keycloak_database}" >"${backup_dir}/target-keycloak-before.dump" <<'SH'
set -eu
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" --format=custom --no-owner --no-acl "$1"
SH

echo "Stopping Docker writers and taking the source snapshot."
source_apps_stopped=true
"${compose[@]}" stop frontend worker backend keycloak

docker exec "${source_postgres}" sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" --format=custom --no-owner --no-acl "$POSTGRES_DB"' \
  >"${backup_dir}/source-taiji.dump"
docker exec "${source_postgres}" sh -lc \
  "PGPASSWORD=\"\$POSTGRES_PASSWORD\" pg_dump -U \"\$POSTGRES_USER\" --format=custom --no-owner --no-acl '${source_keycloak_database}'" \
  >"${backup_dir}/source-keycloak.dump"

count_tables_docker "${source_database}" >"${backup_dir}/source-taiji-counts.tsv"
count_tables_docker "${source_keycloak_database}" >"${backup_dir}/source-keycloak-counts.tsv"

tar -C "${repo_root}" -czf "${backup_dir}/source-files.tar.gz" app_data app_logs
find "${repo_root}/app_data" "${repo_root}/app_logs" -type f -exec sha256sum {} \; \
  | sed "s#${repo_root}/##" | sort >"${backup_dir}/source-files.sha256"
sha256sum "${backup_dir}"/*.dump "${backup_dir}/source-files.tar.gz" >"${backup_dir}/SHA256SUMS"
chmod 600 "${backup_dir}"/*

echo "Replacing the K8s databases."
kubectl_cmd exec -i -n "${namespace}" taiji-postgres-0 -- sh -s -- "${target_database}" "${target_keycloak_database}" <<'SH'
set -eu
for database in "$@"; do
  PGPASSWORD="$POSTGRES_PASSWORD" dropdb -U "$POSTGRES_USER" --if-exists --force "$database"
  PGPASSWORD="$POSTGRES_PASSWORD" createdb -U "$POSTGRES_USER" "$database"
done
SH

kubectl_cmd exec -i -n "${namespace}" taiji-postgres-0 -- \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -U "$POSTGRES_USER" --dbname="$1" --no-owner --no-acl --exit-on-error' \
  sh "${target_database}" <"${backup_dir}/source-taiji.dump"
kubectl_cmd exec -i -n "${namespace}" taiji-postgres-0 -- \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -U "$POSTGRES_USER" --dbname="$1" --no-owner --no-acl --exit-on-error' \
  sh "${target_keycloak_database}" <"${backup_dir}/source-keycloak.dump"

count_tables_k8s "${target_database}" >"${backup_dir}/target-taiji-counts.tsv"
count_tables_k8s "${target_keycloak_database}" >"${backup_dir}/target-keycloak-counts.tsv"
diff -u "${backup_dir}/source-taiji-counts.tsv" "${backup_dir}/target-taiji-counts.tsv"
diff -u "${backup_dir}/source-keycloak-counts.tsv" "${backup_dir}/target-keycloak-counts.tsv"
kubectl_cmd exec -n "${namespace}" taiji-redis-0 -- redis-cli FLUSHALL >/dev/null

echo "Replacing K8s app_data and app_logs."
kubectl_cmd apply -n "${namespace}" -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: taiji-migration-files
  labels:
    app.kubernetes.io/name: migration-files
    app.kubernetes.io/part-of: taiji
spec:
  restartPolicy: Never
  containers:
    - name: files
      image: harbor.aixiongan.org.cn:9443/lihao/nginx:alpine
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: 25m
          memory: 32Mi
        limits:
          cpu: 100m
          memory: 128Mi
      volumeMounts:
        - name: shared
          mountPath: /shared
  volumes:
    - name: shared
      persistentVolumeClaim:
        claimName: pvc-gpfshome-lihao
YAML
helper_created=true
kubectl_cmd wait --for=condition=Ready pod/taiji-migration-files -n "${namespace}" --timeout=180s
kubectl_cmd exec -n "${namespace}" taiji-migration-files -- sh -ec \
  'rm -rf /shared/taiji/app_data /shared/taiji/app_logs; mkdir -p /shared/taiji'
kubectl_cmd cp "${backup_dir}/source-files.tar.gz" \
  "${namespace}/taiji-migration-files:/tmp/source-files.tar.gz" -c files
kubectl_cmd exec -n "${namespace}" taiji-migration-files -- \
  tar -xzf /tmp/source-files.tar.gz -C /shared/taiji
kubectl_cmd exec -n "${namespace}" taiji-migration-files -- sh -c \
  'find /shared/taiji/app_data /shared/taiji/app_logs -type f -exec sha256sum {} \;' \
  | sed 's#/shared/taiji/##' | sort >"${backup_dir}/target-files.sha256"
diff -u "${backup_dir}/source-files.sha256" "${backup_dir}/target-files.sha256"
kubectl_cmd delete pod taiji-migration-files -n "${namespace}" --wait=true
helper_created=false

echo "Starting K8s identity services with the production domain."
kubectl_cmd apply -f "${repo_root}/deploy/taiji-k8s/01-configmap.yaml" -n "${namespace}"
kubectl_cmd scale deployment taiji-keycloak -n "${namespace}" --replicas=1
kubectl_cmd rollout status deployment/taiji-keycloak -n "${namespace}" --timeout=600s
kubectl_cmd apply -f "${repo_root}/deploy/taiji-k8s/13-init-jobs.yaml" -n "${namespace}"
kubectl_cmd wait --for=condition=complete job/taiji-iam-bootstrap -n "${namespace}" --timeout=600s

echo "Starting the K8s application."
kubectl_cmd scale deployment taiji-backend taiji-worker taiji-frontend -n "${namespace}" --replicas=1
kubectl_cmd rollout status deployment/taiji-backend -n "${namespace}" --timeout=600s
kubectl_cmd rollout status deployment/taiji-worker -n "${namespace}" --timeout=600s
kubectl_cmd rollout status deployment/taiji-frontend -n "${namespace}" --timeout=600s

count_tables_k8s "${target_database}" >"${backup_dir}/target-taiji-counts-after-start.tsv"
count_tables_k8s "${target_keycloak_database}" >"${backup_dir}/target-keycloak-counts-after-start.tsv"

kubectl_cmd exec -n "${namespace}" deployment/taiji-frontend -- \
  wget -qO- http://backend:5000/api/ready >"${backup_dir}/k8s-ready.json"
grep -q '"status":"ok"' "${backup_dir}/k8s-ready.json"

migration_succeeded=true
echo "Migration completed. Docker writers remain stopped until the FRP cutover is verified."
echo "Backup and verification artifacts: ${backup_dir}"
