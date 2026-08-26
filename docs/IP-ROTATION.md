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
- Policy `china-proxy-recovery-policy` (or your chosen name) in the compartment that contains the VM:
  ```
  Allow dynamic-group china-proxy-recovery to read instances in compartment id <COMPARTMENT_OCID>
  Allow dynamic-group china-proxy-recovery to inspect vnic-attachments in compartment id <COMPARTMENT_OCID>
  Allow dynamic-group china-proxy-recovery to inspect vnics in compartment id <COMPARTMENT_OCID>
  Allow dynamic-group china-proxy-recovery to inspect private-ips in compartment id <COMPARTMENT_OCID>
  Allow dynamic-group china-proxy-recovery to use private-ips in compartment id <COMPARTMENT_OCID>
  ```

Minimum required per operation (Oracle docs):

- `compute instance get` requires `read instances` (`inspect` only lists, does not get).
- `compute vnic-attachment list` requires `inspect vnic-attachments` (+ `inspect instances` for the list variant).
- `network vnic get` requires `inspect vnics`.
- `network private-ip list` and `network public-ip get --private-ip-id` for ephemeral IPs require `inspect private-ips`.
- `network public-ip delete` and `network public-ip create` for ephemeral IPs require `use private-ips` (`PRIVATE_IP_ASSIGN_PUBLIC_IP` / `UNASSIGN`). `use public-ips` is **not** required for this ephemeral workflow; `manage public-ips` is only for reserved IPs.

`use private-ips` already implies `inspect private-ips`; the separate `inspect` line is kept to document the read-only status path. All statements are compartment-scoped — avoid `in tenancy` unless you need cross-compartment access. If IAM changes, `compute instance get` returns `NotAuthorizedOrNotFound` until the change propagates (usually < 5 min). The Dynamic Groups list shows the rule's matching resource count; 0 means the rule does not match this instance.

Replace `<INSTANCE_OCID>`, `<COMPARTMENT_OCID>`, and group/policy names with your own values.

## Failure window

Rotation is **not** atomic. The tool must delete the old ephemeral public IP before the replacement can be assigned to the same private IP:

- old ephemeral IP will be permanently released first
- there is no guaranteed rollback to the same public IP
- failure after deletion can temporarily leave the VM without a public IP

If the subsequent `public-ip create` fails (quota, capacity, timeout, or network error), the VM stays without a public IP until a new create succeeds or you restore via the console. `--dry-run` reports this window explicitly and does not modify OCI resources. `--confirm` still requires an ephemeral IP, unambiguous discovery, valid artifacts, and `ALLOW_ROTATION=yes` / `CONFIRM_ROTATION` matching the current IP, but it cannot eliminate the delete-then-create window. Plan for out-of-band access (e.g., OCI Console) before rotating from a censored network.

## Post-rotation server-side updates

The tool auto-updates `client-configs/`, `monitoring/probes/private/config.env`, and `state/current-ip.env`. These may still reference the old IP and must be updated manually after a real rotation if you use them:

- `/etc/nginx/sites-available/<service>` — `server_name` for any IP-based vhosts
- `/srv/apps/<service>/.env`, `/srv/apps/<service>/compose.yaml` — embedded public-IP URLs
- TLS cert under `/etc/letsencrypt/live/<domain-or-ip>` — re-issue for the new IP if IP-based
- Client-side bookmarks / SSH `known_hosts` for `https://<SERVER_IP>:<PORT>`

## Safety guards

- `status` and `--dry-run` never modify OCI resources; `--dry-run` explicitly warns about the failure window above.
- `--confirm` requires `ALLOW_ROTATION=yes` and `CONFIRM_ROTATION` to exactly match the current public IP.
- Refuses to run if VNIC or private-IP discovery is ambiguous (more than one match).
- Verifies the public IP is `EPHEMERAL` before deleting it. Reserved IPs are never touched.
- Backs up `client-configs/`, `private/`, and `monitoring/` before any mutation.
- Preserves proxy credentials — only the server address is rewritten.
- Aborts if client artifacts fail to parse or do not contain the current IP.
- No automatic scheduled rotation — manual emergency action only.
