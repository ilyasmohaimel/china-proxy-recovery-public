# china-proxy-recovery

A recovery and maintenance toolkit for a self-hosted censorship-resistant proxy stack using Xray REALITY, Hysteria2, XHTTP, Oracle Cloud, and optional supporting services.

This is a **reference/template** — not a dump of a live server. All identifiers, credentials, and addresses are placeholders. Replace them with your own values before use.

## Architecture

```
                Oracle Cloud VM (Ubuntu 22.04 ARM64)
                ┌──────────────────────────────────────────┐
  Internet ───▶ │ TCP/443  VLESS + REALITY + Vision (RAW)  │
                │         └─► 127.0.0.1:8443 XHTTP REALITY  │
                │ UDP/443  Hysteria2 + Salamander           │
                │ 5353/udp Private AdGuard Home (VPC-only) │
                │ 3000/tcp AdGuard admin (localhost)       │
                │ 22/tcp   SSH                              │
                └──────────────────────────────────────────┘
         │
         │  private AdGuard ──► DoH upstream (Cloudflare / Google)
         │  OCI ephemeral public IP (rotatable)
```

| Transport | Protocol | Port | Purpose |
|-----------|----------|------|---------|
| VLESS + REALITY + Vision | RAW/TCP | 443 | Primary |
| Hysteria2 + Salamander | QUIC/UDP | 443 | Fallback 1 |
| VLESS + XHTTP + REALITY | XHTTP via 127.0.0.1:8443 | 443 (chained) | Fallback 2 |

All three transports share the same Oracle public IP and private AdGuard resolver (`<VPS_PRIVATE_IP>:5353`).

## Recovery philosophy

1. Try transports in order: REALITY → Hysteria2 → XHTTP.
2. If one transport fails, keep using whichever still works — do not rotate the IP.
3. If every transport fails on one carrier but works on another, treat it as a network problem first.
4. If every transport fails from the censored network while the VM is healthy from outside, check whether the Oracle public IP itself is blocked.
5. Only then consider ephemeral IP rotation. Do not rotate UUIDs, REALITY keys, or Hysteria credentials just because the IP changed — only the server address changes.

## Repository layout

```
.
├── README.md
├── docs/
│   ├── ADGUARD-DNS.md
│   ├── IOS-HIDDIFY-DNS.md
│   ├── IP-ROTATION.md
│   ├── MONITORING.md
│   ├── OCI-BLOCK-VOLUME.md
│   ├── SECURITY-MAINTENANCE.md
│   ├── SFTPGO-SFTP-SSHFS.md
│   ├── XHTTP.md
│   └── emergency-recovery.md
├── configs/
│   ├── adguard/AdGuardHome.yaml.example
│   └── xray/xhttp-same-port.json.example
├── monitoring/
│   ├── crowdsec-ntfy/
│   └── probes/
├── oci-emergency-ip/
│   ├── oci-emergency-ip
│   └── oci-rotation.env.example
└── scripts/
    ├── backup-deployment
    └── proxyctl
```

## OCI IP rotation

`oci-emergency-ip` (`oci-emergency-ip/`) is a guarded, instance-principal-based tool that can replace an **ephemeral** public IP on the same primary private IP:

```sh
oci-emergency-ip status
oci-emergency-ip rotate --dry-run
sudo oci-emergency-ip rotate --confirm
```

Guards: `status`/`--dry-run` are read-only; `--confirm` requires `ALLOW_ROTATION=yes`, `CONFIRM_ROTATION=<current public IP>`, unambiguous resource discovery, ephemeral IP verification, successful artifact validation and backup, and refuses to run if discovery is ambiguous. It preserves all proxy credentials and only rewrites the server address in approved artifacts. No scheduled rotation.

See `docs/IP-ROTATION.md` and `docs/emergency-recovery.md`.

## Monitoring / probes

`monitoring/probes/` contains on-demand end-to-end probes that exercise each transport through a real SOCKS tunnel and verify DNS and egress:

```sh
proxyctl status
proxyctl test all
```

Probes can run locally on the VM or externally (`CHINA_PROXY_PROBE_SCOPE=external` skips host-local checks). See `docs/MONITORING.md`.

## Security model

- SSH only; management ports (AdGuard admin, etc.) on localhost/SSH tunnel.
- UFW + OCI Security List / NSG restrict public ingress to required ports.
- Service credentials, TLS, and application data live on an OCI Block Volume at `/srv` (`docs/OCI-BLOCK-VOLUME.md`).
- Regular Ubuntu and service updates (`docs/SECURITY-MAINTENANCE.md`).
- CrowdSec with a local dedup filter forwarding to ntfy for operational alerts.

## What this repository does NOT contain

Live values are intentionally absent. You must supply your own:

- Public / private IPs, OCIDs, hostnames, domains
- VLESS UUIDs, REALITY keys / short IDs / SNI, XHTTP paths
- Hysteria2 auth secrets, Salamander secrets, certificate pins, `vless://` / `hysteria2://` URIs
- SSH keys, passwords, API keys, ntfy/Shlink/SFTPGo/Gokapi tokens, database secrets, `.env` contents, Terraform state

Example configs under `configs/` contain `<PLACEHOLDER>` values only.

## Quick start (template)

1. Provision an Oracle Cloud VM and install Xray, Hysteria2, AdGuard Home.
2. Copy `configs/xray/xhttp-same-port.json.example` and `configs/adguard/AdGuardHome.yaml.example`, replacing every `<PLACEHOLDER>` with your own generated values.
3. Copy `monitoring/probes/config.example` to a protected path (`chmod 600`) and fill in your server IP and private resolver address.
4. Copy `oci-emergency-ip/oci-rotation.env.example` to a protected env file and set your `COMPARTMENT_ID`; leave `ALLOW_ROTATION=no` until you intentionally arm rotation.
5. Review `docs/emergency-recovery.md` offline before you need it.

## License

MIT — see `LICENSE`.
