# Security maintenance

Treat vendor advisories, Ubuntu updates, and proxy-service releases as separate maintenance tracks.

## Vendor advisory triage

Running on OCI does not mean every Oracle CPU or CSPU applies to the guest. First read the official affected-product table, then check installed packages, snaps, processes, and manual software under `/opt` and `/usr/local`.

Ubuntu packages named `linux-oracle` are Ubuntu's OCI kernel family. They are not Oracle Database, Java, WebLogic, VirtualBox, or another Oracle CSPU product.

## Ubuntu updates

Create a backup before changing packages:

```sh
sudo /home/ubuntu/china-proxy-deployment/scripts/backup-deployment
```

Refresh metadata, inspect the proposed transaction, and check whether Ubuntu Pro reports any unavailable ESM updates:

```sh
sudo apt update
apt list --upgradable
apt-mark showhold
sudo apt-get -s --with-new-pkgs upgrade
sudo pro security-status
```

If the simulation has no removals or unexpected dependency changes, apply it:

```sh
sudo apt-get --with-new-pkgs upgrade
```

Reboot once only when `/var/run/reboot-required` exists or a new kernel must be loaded. Unattended security upgrades stay enabled, but automatic reboot stays disabled.

## Service releases

Compare Xray, Hysteria2, AdGuard Home, ntfy, and installed CrowdSec collections/scenarios against their official release feeds. Upgrade a service for a relevant security fix or support problem, not only because a feature release exists. Configs and credentials are preserved and validated before restart.

Refresh CrowdSec detection content with `sudo cscli hub update && sudo cscli hub upgrade`, then `sudo systemctl restart crowdsec`. The Nginx `deny` bouncer (if used) refreshes on its own timer; only reload Nginx if its whitelist changes.

## Validation

After updates and any reboot, check:

```sh
systemctl --failed
sudo systemctl status xray hysteria-server adguardhome crowdsec crowdsec-nginx-bouncer.timer --no-pager
sudo xray run -test -config /usr/local/etc/xray/config.json
sudo cscli decisions list
sudo docker ps
sudo ss -lntup
sudo nginx -t
sudo ufw status verbose
/usr/local/bin/proxyctl test all
```

Also confirm the running kernel, BBR and `fq`, private AdGuard filtering, localhost-only management ports, expected public egress, and normal HTTPS through RAW REALITY, Hysteria2, and XHTTP.
