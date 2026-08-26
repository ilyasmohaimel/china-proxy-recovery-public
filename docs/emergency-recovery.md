# Emergency recovery

Short offline procedure for a self-hosted proxy on Oracle Cloud.

## Current setup (template)

- OCI region: `<OCI_REGION>` (e.g., `eu-paris-1`)
- Public IPv4: recorded in `state/current-ip.env` (not in Git)
- Ubuntu 22.04 LTS ARM64
- `VM.Standard.A1.Flex`, 2 OCPU / 12 GB RAM (example)
- REALITY: VLESS + Vision, RAW/TCP, TCP/443
- Hysteria2: Salamander, UDP/443
- XHTTP: VLESS + REALITY, chained behind TCP/443 (127.0.0.1:8443)
- DNS: private AdGuard Home on the OCI private IPv4, port 5353
- SSH user: `ubuntu`
- Deployment: `/home/ubuntu/china-proxy-deployment/`
- Client configs: `/home/ubuntu/china-proxy-deployment/client-configs/`

All three transports should be tested independently and egress via the Oracle public IP.

## If something stops working

Try things in this order:

1. REALITY
2. Hysteria2
3. XHTTP
4. another Wi-Fi / mobile network
5. Server / service checks
6. OCI Console
7. IP rotation only if every transport fails from the censored network while the VM is still healthy elsewhere

If only one protocol fails, leave the Oracle IP alone.

If every transport fails on one carrier but works on another, treat it as a network-specific problem first.

If every transport fails from the censored network and the server still works from outside, check whether the public IP itself is blocked.

## Replacing an ephemeral OCI public IP

First confirm the current public IP is actually **ephemeral**.

OCI Console path:

1. `Compute` -> `Instances`
2. open the proxy VM
3. `Networking`
4. open the primary VNIC
5. `IP administration`
6. edit the primary private IP

To remove the current address:

1. set `Public IP type` to `No public IP`
2. save

To get a new address:

1. edit the same primary private IP again
2. set `Public IP type` to `Ephemeral public IP`
3. save
4. note the new IPv4

## After the IP changes

Only change the server address in client profiles.

Keep these the same:

- VLESS UUID
- REALITY key pair
- short ID
- SNI / target
- fingerprint
- Vision flow
- Hysteria2 auth
- certificate pin
- Salamander secret

For RAW REALITY, Hysteria2, and XHTTP, only replace `<OLD_PUBLIC_IP>` with `<NEW_PUBLIC_IP>`.

The generated files under:

```text
/home/ubuntu/china-proxy-deployment/client-configs/
```

may still have the old IP, so update/regenerate them after SSH works again.

## SSH after an IP change

```sh
ssh -i ~/.ssh/<KEY> ubuntu@<NEW_PUBLIC_IP>
```

Then:

```sh
sudo systemctl status xray hysteria-server adguardhome --no-pager
sudo ss -lntup
sudo ufw status verbose
systemctl --failed
```

Expected listeners:

- TCP/22: SSH
- TCP/443: RAW REALITY and chained XHTTP
- UDP/443: Hysteria2
- TCP/8443: XHTTP on localhost only
- TCP+UDP/5353: AdGuard on the OCI private IPv4 only
- TCP/3000: AdGuard on localhost only

## If SSH does not work

Check:

1. VM is `RUNNING`
2. a public IPv4 is attached
3. VCN route still has `0.0.0.0/0` -> Internet Gateway
4. OCI Security List / NSG still allows 22/TCP, 443/TCP, 443/UDP
5. UFW still allows the same ports
6. the new IP works from another network

## Offline kit to prepare before travel

- RAW REALITY profile
- Hysteria2 profile
- XHTTP profile
- profile QR codes
- SSH key
- OCI recovery info
- this guide
- at least one backup VPN/client

## Guarded rotation tool

The rotation tool is read-only unless explicitly armed and confirmed:

```sh
oci-emergency-ip status
oci-emergency-ip rotate --dry-run
sudo oci-emergency-ip rotate --confirm
```

It discovers the instance, primary VNIC, private IP, public IP object, and IP lifetime before changing anything. A confirmed rotation backs up private state, preserves credentials, updates approved artifacts, and runs the local end-to-end probes.

The tool uses instance-principal auth. It requires a dynamic group and policy in the OCI tenancy; without them it reports an auth failure (details in `IP-ROTATION.md`).

**Failure window:** rotation deletes the old ephemeral public IP before creating the replacement.

- old ephemeral IP will be permanently released first
- there is no guaranteed rollback to the same public IP
- failure after deletion can temporarily leave the VM without a public IP

`--dry-run` explains this window explicitly and never modifies OCI resources. Do not rotate without out-of-band access (e.g., OCI Console).

No scheduled IP rotation.

## Known-good diagnostics (examples)

- RAW REALITY, Hysteria2, and XHTTP pass independent real-client probes
- private AdGuard resolution and filtering work through each transport
- `fast.com` works through RAW REALITY and Hysteria2
- 5 MB transfers completed without stalls
- PMTU measured at 1500 bytes

## OCI docs

- https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm
- https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/deleting-ephemeral-public-ip-from-instance.htm
- https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/assigning-ephemeral-public-existing-private-ip.htm
- https://docs.oracle.com/en-us/iaas/Content/API/Concepts/cloudshellintro.htm
