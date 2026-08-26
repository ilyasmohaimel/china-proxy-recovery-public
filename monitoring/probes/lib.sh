#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROBE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PROBE_CONFIG=${CHINA_PROXY_PROBE_CONFIG:-$HOME/.config/china-proxy-probes/config.env}

load_probe_config() {
  [[ -r $PROBE_CONFIG ]] || { printf 'PROBE_CONFIG_MISSING\n' >&2; return 1; }
  # shellcheck disable=SC1090
  source "$PROBE_CONFIG"
}

now_ms() { date +%s%3N; }

wait_for_socks() {
  local port=$1 pid=$2
  local n
  for n in {1..30}; do
    kill -0 "$pid" 2>/dev/null || return 1
    if curl -fsS --max-time 2 --proxy "socks5h://127.0.0.1:$port" https://www.google.com/generate_204 -o /dev/null 2>/dev/null; then
      return 0
    fi
    sleep 0.2
  done
  return 1
}

run_transport_probe() {
  local label=$1 kind=$2 binary=$3 config=$4 port=$5
  local start end duration temp pid error= success=false egress=
  start=$(now_ms)
  temp=$(mktemp -d "/tmp/china-proxy-probe.${kind}.XXXXXX")
  chmod 700 "$temp"
  cleanup() {
    if [[ -n ${pid:-} ]]; then kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; fi
    rm -rf -- "$temp"
  }
  trap cleanup RETURN

  if [[ ! -x $binary || ! -r $config ]]; then
    error="${label}_CONFIG_MISSING"
  else
    case "$kind" in
      reality|xhttp) "$binary" run -config "$config" >"$temp/core.log" 2>&1 & ;;
      hysteria2) "$binary" client --disable-update-check -c "$config" >"$temp/core.log" 2>&1 & ;;
      *) return 2 ;;
    esac
    pid=$!
    if ! wait_for_socks "$port" "$pid"; then
      error="${label}_HANDSHAKE_FAILED"
    elif ! egress=$(curl -4fsS --max-time 15 --proxy "socks5h://127.0.0.1:$port" https://icanhazip.com/); then
      error="${label}_HTTPS_FAILED"
    elif [[ ${egress//$'\n'/} != "$EXPECTED_EGRESS_IP" ]]; then
      error="${label}_EGRESS_MISMATCH"
    elif ! curl -4fsS --max-time 15 --proxy "socks5h://127.0.0.1:$port" https://www.google.com/generate_204 -o /dev/null; then
      error="${label}_DESTINATION_FAILED"
    elif ! curl -4fsS --max-time 15 --proxy "socks5h://127.0.0.1:$port" https://cloudflare.com/cdn-cgi/trace -o /dev/null; then
      error="${label}_DESTINATION_FAILED"
    elif ! python3 "$PROBE_DIR/dns-over-socks.py" --socks-port "$port" --dns-host "$ADGUARD_IP" --dns-port "$ADGUARD_PORT" --name cloudflare.com --expect normal; then
      error="${label}_DNS_UPSTREAM_FAILURE"
    elif ! python3 "$PROBE_DIR/dns-over-socks.py" --socks-port "$port" --dns-host "$ADGUARD_IP" --dns-port "$ADGUARD_PORT" --name googleads.g.doubleclick.net --expect blocked; then
      error="${label}_DNS_FILTER_FAILURE"
    else
      success=true
    fi
  fi
  end=$(now_ms); duration=$((end-start))
  [[ $success == true ]] || { printf '%s\n' "$error" >&2; return 1; }
  printf '%s_OK duration_ms=%s\n' "$label" "$duration"
}
