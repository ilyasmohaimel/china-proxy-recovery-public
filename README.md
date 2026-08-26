# china-proxy-recovery

Public, sanitized version of my private [`china-proxy-recovery`](https://github.com/ilyasmohaimel/china-proxy-recovery) repository.

The private repository contains deployment-specific recovery data for a live server. This public version keeps only the reusable tooling, example configs, and documentation — with all secrets, infrastructure identifiers, personal paths, and live configuration removed. All values that look like credentials or identifiers are placeholders.

Use it as a template/reference for a similar self-hosted stack; replace every placeholder with your own generated values.

## Stack

- **Xray** — VLESS + REALITY + Vision (RAW/TCP, `443`) as primary
- **Hysteria2 + Salamander** (UDP `443`) as fallback 1
- **VLESS + XHTTP + REALITY** (chained via `127.0.0.1:8443`) as fallback 2
- **Oracle Cloud** — ephemeral public IP with guarded emergency rotation
- **AdGuard Home** — private resolver on the OCI private address, DoH upstream
- **Probes / monitoring** — real-client end-to-end checks per transport
- **Recovery & maintenance** — offline recovery guide, block-volume layout, update runbook

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

All three transports share the same Oracle public IP and private AdGuard resolver (`<VPS_PRIVATE_IP>:5353`).

## Recovery order

1. Try `REALITY` → `Hysteria2` → `XHTTP`.
2. If one transport fails, keep using whichever still works — do not rotate the IP.
3. If every transport fails on one carrier but works on another, treat it as a carrier/network problem.
4. If every transport fails from the censored network while the VM is healthy from outside, check whether the public IP itself is blocked.
5. Only then consider ephemeral IP rotation. Credentials stay the same — only the server address changes.

## Repository structure

```
.
├── README.md
├── configs/
│   ├── adguard/AdGuardHome.yaml.example
│   └── xray/xhttp-same-port.json.example
├── docs/
│   ├── ADGUARD-DNS.md
│   ├── IOS-HIDDIFY-DNS.md
│   ├── IP-ROTATION.md
│   ├── MONITORING.md
│   ├── OCI-BLOCK-VOLUME.md
│   ├── OPTIONAL-SERVICES.md
│   ├── SECURITY-MAINTENANCE.md
│   ├── SFTPGO-SFTP-SSHFS.md
│   ├── XHTTP.md
│   └── emergency-recovery.md
├── monitoring/
│   ├── crowdsec-ntfy/crowdsec-ntfy-dedup.py
│   └── probes/  (probe-reality, probe-hysteria2, probe-xhttp, probe-adguard, ...)
├── oci-emergency-ip/
│   ├── oci-emergency-ip
│   └── oci-rotation.env.example
└── scripts/
    ├── backup-deployment
    └── proxyctl
```

## Documentation

| Doc | Covers |
|-----|--------|
| [docs/emergency-recovery.md](docs/emergency-recovery.md) | Offline recovery — transport order, IP replacement, post-rotation checks |
| [docs/IP-ROTATION.md](docs/IP-ROTATION.md) | Instance-principal IAM, guards, and manual console steps |
| [docs/ADGUARD-DNS.md](docs/ADGUARD-DNS.md) | Private AdGuard on `<VPS_PRIVATE_IP>:5353`, upstream, routing rule |
| [docs/IOS-HIDDIFY-DNS.md](docs/IOS-HIDDIFY-DNS.md) | Hiddify/Sing-box DNS profile for iOS |
| [docs/XHTTP.md](docs/XHTTP.md) | Same-port XHTTP chaining behind REALITY |
| [docs/MONITORING.md](docs/MONITORING.md) | Probes and CrowdSec→ntfy dedup filter |
| [docs/SECURITY-MAINTENANCE.md](docs/SECURITY-MAINTENANCE.md) | Ubuntu + service update flow and validation |
| [docs/OCI-BLOCK-VOLUME.md](docs/OCI-BLOCK-VOLUME.md) | Persistent `/srv` block volume |
| [docs/SFTPGO-SFTP-SSHFS.md](docs/SFTPGO-SFTP-SSHFS.md) | SFTPGo + SSHFS example |
| [docs/OPTIONAL-SERVICES.md](docs/OPTIONAL-SERVICES.md) | Generic pattern for extra services |

Example configs are under [configs/](configs/) and contain `<PLACEHOLDER>` values only.

## Use

This is a reference, not an installer. Provision your own VM, install Xray/Hysteria/AdGuard, then adapt the examples.

```sh
# Copy and fill in example configs
cp configs/xray/xhttp-same-port.json.example /usr/local/etc/xray/config.json   # replace <VLESS_UUID>, <REALITY_PRIVATE_KEY>, ...
cp configs/adguard/AdGuardHome.yaml.example /etc/adguardhome/AdGuardHome.yaml # replace <VPS_PRIVATE_IP>, <ADMIN_USER>, ...

# Private probe config (chmod 600, outside Git)
cp monitoring/probes/config.example /home/ubuntu/china-proxy-deployment/monitoring/probes/private/config.env
# set CURRENT_IP, VPS_PRIVATE_IP, client JSON/YAML paths

# OCI rotation env (chmod 600, outside Git)
cp oci-emergency-ip/oci-rotation.env.example /home/ubuntu/china-proxy-deployment/private/oci-rotation.env
# set COMPARTMENT_ID; leave ALLOW_ROTATION=no until intentionally armed

# Health checks
sudo systemctl status xray hysteria-server adguardhome --no-pager
sudo ss -lntup
proxyctl status
proxyctl test all
```

Review [docs/emergency-recovery.md](docs/emergency-recovery.md) offline before you need it.

### OCI emergency IP rotation

Guarded, instance-principal tool at [oci-emergency-ip/oci-emergency-ip](oci-emergency-ip/oci-emergency-ip):

```sh
oci-emergency-ip status
oci-emergency-ip rotate --dry-run
sudo oci-emergency-ip rotate --confirm
```

`status` and `--dry-run` are read-only. `--confirm` requires `ALLOW_ROTATION=yes`, `CONFIRM_ROTATION` matching the current IP, unambiguous discovery, ephemeral-IP verification, valid client artifacts, and a successful backup. It preserves all proxy credentials and only rewrites the server address in approved artifacts. No scheduled rotation. See [docs/IP-ROTATION.md](docs/IP-ROTATION.md).

### Probes

```sh
proxyctl test reality
proxyctl test hysteria2
proxyctl test xhttp
CHINA_PROXY_PROBE_SCOPE=external monitoring/probes/probe-all  # from outside the VM
```

Each transport probe starts a SOCKS listener, verifies egress equals `EXPECTED_EGRESS_IP`, and checks private AdGuard resolution/filtering. See [docs/MONITORING.md](docs/MONITORING.md).

## Security

- SSH only; admin UIs on `127.0.0.1` via SSH tunnel.
- UFW + OCI Security List/NSG restrict public ingress to `22/TCP`, `443/TCP`, `443/UDP` (plus any optional service ports you add).
- App data, credentials, and TLS state on an OCI Block Volume at `/srv` ([docs/OCI-BLOCK-VOLUME.md](docs/OCI-BLOCK-VOLUME.md)).
- Regular update triage for Ubuntu and all services ([docs/SECURITY-MAINTENANCE.md](docs/SECURITY-MAINTENANCE.md)).
- CrowdSec with a local 4h-per-IP dedup filter → ntfy for operational alerts.
- Change all default credentials before exposing any service; store secrets outside Git (`chmod 600`).

## What is intentionally excluded

No live values are committed. You must supply your own:

- Public/private IPs, OCIDs, hostnames, domains
- VLESS UUIDs, REALITY key pairs/short IDs/SNI, XHTTP paths
- Hysteria2 auth/Salamander secrets, certificate pins, `vless://`/`hysteria2://` URIs, QR codes
- SSH keys, passwords, API keys, ntfy/Shlink/SFTPGo/Gokapi tokens, database secrets, `.env` contents, Terraform state

The `.gitignore` blocks `*.key`, `*.pem`, `.env`, `client-configs/`, `.oci/`, `terraform.tfstate`, and other runtime secrets. Review it before committing.
