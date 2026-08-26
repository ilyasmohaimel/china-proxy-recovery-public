# OCI emergency IP tool

Install the script as `oci-emergency-ip` and keep the live environment file outside Git.

```sh
oci-emergency-ip status
oci-emergency-ip rotate --dry-run
sudo oci-emergency-ip rotate --confirm
```

`status` and `--dry-run` are read-only. The confirmed path refuses to run unless discovery is unambiguous, the IP is ephemeral, the profiles parse, the backup succeeds, and the protected configuration deliberately arms rotation.

The tool authenticates via instance principal (`OCI_AUTH=instance_principal`) or a protected OCI CLI profile. IAM authorization must be configured before the status check can pass — see `docs/IP-ROTATION.md`.

**Failure window:** a confirmed rotation deletes the old ephemeral public IP before creating the replacement.

- old ephemeral IP will be permanently released first
- there is no guaranteed rollback to the same public IP
- failure after deletion can temporarily leave the VM without a public IP

`--dry-run` prints this warning and never modifies OCI resources. Do not rotate without out-of-band access (e.g., OCI Console).
