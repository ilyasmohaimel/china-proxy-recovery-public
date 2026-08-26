#!/usr/bin/env python3
"""CrowdSec -> ntfy per-IP deduplication filter (4 hour window).

Receives the CrowdSec notification-http POST, extracts the source IP from the
plain-text body ("IP: x.x.x.x" line), and forwards to ntfy only if that IP was
not already alerted within DEDUP_WINDOW seconds (4 hours). State is persisted in
STATE_FILE across restarts. Bans/decisions are untouched (the filter only
suppresses the notification).
"""
import http.server
import json
import os
import sys
import time
import urllib.request

STATE_DIR = "/var/lib/crowdsec-ntfy-dedup"
STATE_FILE = os.path.join(STATE_DIR, "state.json")
NTFY_TARGET = "http://127.0.0.1:8480"
DEDUP_WINDOW = 14400
PRUNE_AFTER = 21600


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    os.replace(tmp, STATE_FILE)
    os.chmod(STATE_FILE, 0o600)


def extract_ips(body):
    ips = []
    for line in body.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if line.startswith("IP:"):
            ip = line[3:].strip()
            if ip and ip not in ips:
                ips.append(ip)
    return ips


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length)
        ips = extract_ips(body)
        now = time.time()
        if ips:
            state = load_state()
            if all(now - state.get(ip, 0) < DEDUP_WINDOW for ip in ips):
                print("suppressed notification for IPs: %s" % ", ".join(ips), flush=True)
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            for ip in ips:
                state[ip] = now
            for ip in [k for k, t in state.items() if now - t > PRUNE_AFTER]:
                del state[ip]
            save_state(state)
        req = urllib.request.Request(NTFY_TARGET + self.path, data=body, method="POST")
        for header in ("Authorization", "Content-Type", "X-Priority", "X-Tags"):
            value = self.headers.get(header)
            if value:
                req.add_header(header, value)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "text/plain"))
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        except Exception as exc:
            print("forward failed: %s" % exc, flush=True)
            self.send_response(502)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write(fmt % args + "\n")


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 8481), Handler)
    server.serve_forever()
