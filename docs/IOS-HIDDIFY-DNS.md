# iPhone Hiddify DNS

Use this configuration to make DNS for globally proxied traffic leave through the active proxy instead of using the Wi-Fi resolver.

## Global test profile

Import an existing VLESS + REALITY profile, select it, then use these Hiddify settings before adding China split routing.

### Inbound

- `Service mode`: `VPN`
- `Strict route`: on
- `Tun implementation`: `System`
- `MTU`: `1400`, if the installed build exposes it

### DNS

- `Remote DNS`: `udp://<VPS_PRIVATE_IP>:5353`
- `Remote DNS domain strategy`: `IPv4 only`
- `Enable fake DNS`: off
- `Outbound server resolver (direct)`: `https://1.1.1.1/dns-query`
- `Outbound domain strategy`: `IPv4 only`

### Route general options

- `Region`: `Other`
- `IPv6 route`: `Disable`
- `Resolve destination`: off

Leave custom route rules and per-app bypass rules disabled for this test. Only add China-direct routing after global mode has passed.

Current Hiddify builds do not expose a separate `Enable DNS routing` control. Their generated sing-box configuration sends unmatched DNS to Remote DNS through the main proxy. If an older build shows `Enable DNS routing`, turn it on.

## Expected DNS path

```text
iPhone app
  -> Hiddify VPN/TUN DNS handler
  -> private AdGuard DNS, inside VLESS + REALITY
  -> VPS
  -> encrypted upstream DNS
  -> destination
```

The DNS query and the destination connection use the selected profile. AdGuard sends its upstream request over DoH. The Wi-Fi router and its local resolver should not receive the destination DNS query.

The server has no usable public IPv6 route. `IPv4 only` plus `IPv6 route: Disable` prevents an AAAA route from complicating this test.

## OpenDNS bypass test

1. Disconnect Hiddify and confirm the VPN indicator disappears.
2. On the same Wi-Fi, open a hostname blocked by the local DNS policy. Expect the block page or block result.
3. Connect the VLESS + REALITY profile in Hiddify and confirm a VPN indicator appears.
4. Close and reopen the browser, or use a new private tab after reconnecting Wi-Fi, so an old DNS result is not reused.
5. Open the same hostname. Expect the real site, not the block result.
6. Also open `https://icanhazip.com`. Expect the proxy server's public IPv4.

For a deterministic test, temporarily turn off iCloud Private Relay / `Limit IP Address Tracking` for that Wi-Fi. It is not required for normal use, but it prevents Safari's own privacy path from confusing the A/B result.

## If the block remains

1. Check that `Service mode` is `VPN`, not `Proxy service only` or `Set system proxy`.
2. Recheck every DNS and routing value above. In particular, use `Region: Other`; `China (cn)` deliberately creates direct-DNS rules for Chinese domains.
3. Remove custom direct rules, per-app bypasses, and any competing VPN/DNS application. iOS permits only one active VPN path.
4. Reconnect Wi-Fi and retry in a fresh browser tab. Cached answers can survive a profile change.
5. Confirm the visible IP from `icanhazip.com` is the proxy IP. If it is not, the VPN/TUN path is not active.
6. Update Hiddify before changing the server. Older iOS builds may have different DNS controls.
7. If `System` cannot establish the VPN, use `Mixed` once as an A/B test. It changes the local TUN implementation, not the DNS policy.

## REALITY and Hysteria2

DNS policy is client-side and is not encoded in the VLESS or Hysteria URI. The same private DNS setting applies when selecting Hysteria2, but test it independently after REALITY works.

The proxy server has one narrow route for its private DNS address and port. Do not expose DNS on the public address.
