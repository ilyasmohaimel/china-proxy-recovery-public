# XHTTP fallback

The third transport in this template is VLESS + XHTTP + REALITY.

The public port remains TCP/443. The existing RAW REALITY listener is the outer listener. Valid RAW clients terminate there; unmatched REALITY traffic is forwarded to an XHTTP REALITY listener on localhost.

```text
TCP/443 RAW REALITY
  |-- known RAW client -> existing Vision inbound
  `-- unmatched auth -> 127.0.0.1:8443 XHTTP REALITY
```

The localhost port is not public and needs no UFW or OCI rule.

## Transport choices

- XHTTP mode: upstream default under REALITY (`stream-one`)
- VLESS flow: empty; Vision stays on the RAW profile only
- XMUX and download separation: defaults
- Identity, REALITY key, short ID, and path: separate from RAW

This gives transport diversity on the same public IP. It does not help if the IP itself is blocked.

Xray-core is the reference client for this profile. Keep RAW REALITY and Hysteria2 for clients that do not support this exact XHTTP profile.

The full Xray client JSON puts the exact private AdGuard address and port on the proxy outbound before its generic private-network direct rule. A VLESS URI cannot carry this DNS routing rule, so reproduce it in the client after URI import.

Current v2rayN and v2rayNG builds parse XHTTP profiles and use Xray-core for them. sing-box does not implement Xray XHTTP, so do not use this profile with Hiddify/sing-box.

## Future CDN design

A future domain/CDN path would be:

```text
Censored network -> CDN/domain -> XHTTP -> origin
```

That needs a suitable domain, CDN support for the selected XHTTP mode, origin authentication, and a separate tested rollout. It is not part of the direct-IP deployment.
