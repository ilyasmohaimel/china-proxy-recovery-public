# Monitoring

Health checking is on-demand probe scripts under `monitoring/probes/` plus optional ntfy alert channels.

Local E2E checks prove each server transport can complete a real tunnel and reach the Internet. They do not prove another network — or mainland China — can reach the VPS.

On the VPS, run the checks with `proxyctl`:

```sh
proxyctl status        # xray/hysteria/adguardhome state + listeners
proxyctl test all      # REALITY, Hysteria2, XHTTP, AdGuard, server, backup probes
proxyctl monitor status
```

The scripts under `monitoring/probes/` can also run from a laptop, another VPS, or a machine in China. Set `CHINA_PROXY_PROBE_SCOPE=external` there so `probe-all` skips host-local service and backup checks. The probe output itself distinguishes a server failure from a China-path block; the probes only print results.

OCI checks need the instance-principal IAM grant: a dynamic group plus policy in the root compartment (see `IP-ROTATION.md`). Until that propagates, the probe scripts report `OCI_AUTH_FAILURE`.

## CrowdSec ntfy alerts

CrowdSec can post ban notices through a local dedup filter before ntfy:

```text
crowdsec -> notification-http (/etc/crowdsec/notifications/http.yaml)
        -> dedup filter 127.0.0.1:8481
        -> ntfy 127.0.0.1:8480 -> topic security
```

The filter (`monitoring/crowdsec-ntfy/`, deployed as `/usr/local/libexec/crowdsec-ntfy-dedup.py` plus `crowdsec-ntfy-dedup.service`) sends at most one alert per source IP per 4 hours, regardless of scenario. Different IPs always alert. Bans and decisions are untouched; the filter only suppresses duplicate notifications. Its state lives in `/var/lib/crowdsec-ntfy-dedup/state.json` and survives restarts.

The `http.yaml` template must keep bodies under ntfy's `message-max-size` (default `4096`); a larger body comes back as an `attachment.json` file instead of text.

```sh
sudo cscli notifications test ntfy_security
sudo journalctl -u crowdsec-ntfy-dedup -n 20 --no-pager   # shows suppressed duplicates
```

## Example ntfy topics

If you use ntfy, consider separate topics for different event classes:

- `security` — CrowdSec bans
- `updates` — container image updates (e.g., DIUN)
- `system` — storage guard, backup failures

Routine successful backups should be silent and only logged to the journal; failures alert to `system`.

## OCI probes

```sh
monitoring/probes/probe-oci-status
monitoring/probes/probe-oci-dry-run
```

These verify instance-principal auth and that the rotation preconditions are met without modifying anything.
