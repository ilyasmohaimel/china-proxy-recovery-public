# Emergency OCI IP rotation

The rotation tool is guarded and read-only by default.

```sh
oci-emergency-ip status
oci-emergency-ip rotate --dry-run
sudo oci-emergency-ip rotate --confirm
```

Do not run `--confirm` during normal maintenance. A real rotation requires unambiguous OCI discovery, an ephemeral public IP, successful backups, parseable client artifacts, and `ALLOW_ROTATION=yes` in the protected runtime config.

The tool preserves proxy credentials. It changes the public IP assignment on the same primary private IP, updates approved local artifacts, records the new canonical IP, and runs post-rotation checks.

## OCI instance-principal auth

The tool authenticates as the instance itself (no API keys; `OCI_AUTH=instance_principal` in `private/oci-rotation.env`). For that to work, two IAM objects must exist in the tenancy:

- Dynamic group `china-proxy-recovery` (or your chosen name), rule (this VM only, not compartment-wide):
  `ALL {instance.id = '<INSTANCE_OCID>'}`
- Policy `china-proxy-recovery-policy` (or your chosen name) in the root compartment:
  ```
  Allow dynamic-group china-proxy-recovery to inspect instances in tenancy
  Allow dynamic-group china-proxy-recovery to read vnic-attachments in tenancy
  Allow dynamic-group china-proxy-recovery to read vnics in tenancy
  Allow dynamic-group china-proxy-recovery to read private-ips in tenancy
  Allow dynamic-group china-proxy-recovery to use public-ips in tenancy
  ```

`use public-ips` covers the get/create/delete the rotation needs; nothing grants tenant-wide manage. If IAM changes, `compute instance get` returns `NotAuthorizedOrNotFound` until the change propagates (usually < 5 min). The Dynamic Groups list shows the rule's matching resource count; 0 means the rule does not match this instance.

Replace `<INSTANCE_OCID>`, `<COMPARTMENT_OCID>`, and group/policy names with your own values.

## Post-rotation server-side updates

The tool auto-updates `client-configs/`, `monitoring/probes/private/config.env`, and `state/current-ip.env`. These may still reference the old IP and must be updated manually after a real rotation if you use them:

- `/etc/nginx/sites-available/<service>` — `server_name` for any IP-based vhosts
- `/srv/apps/<service>/.env`, `/srv/apps/<service>/compose.yaml` — embedded public-IP URLs
- TLS cert under `/etc/letsencrypt/live/<domain-or-ip>` — re-issue for the new IP if IP-based
- Client-side bookmarks / SSH `known_hosts` for `https://<SERVER_IP>:<PORT>`

## Safety guards

- `status` and `--dry-run` never modify OCI resources.
- `--confirm` requires `ALLOW_ROTATION=yes` and `CONFIRM_ROTATION` to exactly match the current public IP.
- Refuses to run if VNIC or private-IP discovery is ambiguous (more than one match).
- Verifies the public IP is `EPHEMERAL` before deleting it. Reserved IPs are never touched.
- Backs up `client-configs/`, `private/`, and `monitoring/` before any mutation.
- Preserves proxy credentials — only the server address is rewritten.
- Aborts if client artifacts fail to parse or do not contain the current IP.
- No automatic scheduled rotation — manual emergency action only.
