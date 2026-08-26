# Private AdGuard DNS

Run AdGuard Home on the OCI private IPv4 at port `5353`. The admin UI listens on localhost only.

```text
client -> encrypted proxy -> private AdGuard -> encrypted upstream -> Internet
```

## Resolver policy

- Primary: Cloudflare DoH
- Fallback: Google DoH
- Bootstrap: IPv4 resolvers only
- DNSSEC: enabled
- IPv6 answers: disabled
- ECS: disabled
- Query and statistics retention: one day
- Main filter: HaGeZi Multi PRO
- Security filter: HaGeZi TIF Medium

Use one primary upstream and one fallback so normal queries are not copied to several providers.

## Client setting

Set remote DNS to:

```text
udp://<VPS_PRIVATE_IP>:5353
```

That address must be routed through the selected proxy outbound. It is not reachable from the public Internet.

If a client has a generic private/LAN direct rule, add this narrower rule before it:

```text
<VPS_PRIVATE_IP>/32, port 5353, TCP+UDP -> PROXY
```

RAW REALITY, Hysteria2, and XHTTP all use the same private resolver. The URI alone cannot encode this policy.

## Admin access

```sh
ssh -L 3000:127.0.0.1:3000 -i ~/.ssh/<KEY> ubuntu@<SERVER_IP>
```

Then open `http://127.0.0.1:3000`.

## Checks

```sh
dig @<VPS_PRIVATE_IP> -p 5353 cloudflare.com A
dig @<VPS_PRIVATE_IP> -p 5353 googleads.g.doubleclick.net A
```

The normal query must return a public IPv4. The filter test must return `0.0.0.0`. These commands only work on the VPS or through a proxy tunnel that can reach the private address.
