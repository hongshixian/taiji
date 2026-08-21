#!/usr/bin/env bash
set -euo pipefail

namespace="${KUBE_NAMESPACE:-lihao}"
source_config="${FRPC_SOURCE_CONFIG:-}"
proxy_name="${FRPC_SOURCE_PROXY_NAME:-fangcun-eval-n}"
secret_name="${FRPC_SECRET_NAME:-taiji-frpc-config}"

if [[ -z "${source_config}" || ! -f "${source_config}" ]]; then
  echo "Set FRPC_SOURCE_CONFIG to the existing Fangcun frpc.toml file." >&2
  exit 1
fi

tmp_config="$(mktemp)"
trap 'rm -f "${tmp_config}"' EXIT
chmod 600 "${tmp_config}"

python3 - "${source_config}" "${proxy_name}" >"${tmp_config}" <<'PY'
import sys
import tomllib

source_path, proxy_name = sys.argv[1:]
with open(source_path, "rb") as source:
    config = tomllib.load(source)

token = config.get("auth", {}).get("token")
if not token:
    raise SystemExit("The source FRP configuration has no auth.token")

source_proxy = next(
    (proxy for proxy in config.get("proxies", []) if proxy.get("name") == proxy_name),
    None,
)
if source_proxy is None:
    raise SystemExit(f"Proxy {proxy_name!r} was not found in the source configuration")
if source_proxy.get("type") != "tcp" or not source_proxy.get("remotePort"):
    raise SystemExit("The source proxy must be a TCP proxy with remotePort")

def toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

print("loginFailExit = false")
print(f"serverAddr = {toml_string(str(config['serverAddr']))}")
print(f"serverPort = {int(config.get('serverPort', 7000))}")
print(f"auth.token = {toml_string(str(token))}")
print("transport.protocol = \"tcp\"")
print("transport.tcpMux = true")
print("transport.tcpMuxKeepaliveInterval = 30")
print("transport.heartbeatInterval = 30")
print("transport.heartbeatTimeout = 90")
print()
print("[[proxies]]")
print('name = "k8s-taiji-evaluation"')
print('type = "tcp"')
print('localIP = "frontend"')
print("localPort = 80")
print(f"remotePort = {int(source_proxy['remotePort'])}")
PY

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
kubectl create secret generic "${secret_name}" \
  --namespace "${namespace}" \
  --from-file=frpc.toml="${tmp_config}" \
  --dry-run=client -o yaml | kubectl apply -f -
