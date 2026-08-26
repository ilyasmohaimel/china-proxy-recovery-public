#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import urllib.parse

os.umask(0o077)


def one(values, name, default=None):
    found = values.get(name)
    return found[0] if found else default


def private_dns_rule(dns_host):
    return {"type": "field", "ip": [f"{dns_host}/32"], "port": "5353", "network": "tcp,udp", "outboundTag": "proxy"}


def reality_config(uri_path, server, port, dns_host=None):
    parsed = urllib.parse.urlsplit(uri_path.read_text().strip())
    if parsed.scheme != "vless":
        raise ValueError("expected vless URI")
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{"tag": "socks", "listen": "127.0.0.1", "port": port, "protocol": "socks", "settings": {"udp": True}}],
        "outbounds": [{
            "tag": "proxy",
            "protocol": "vless",
            "settings": {"vnext": [{"address": server, "port": parsed.port, "users": [{
                "id": urllib.parse.unquote(parsed.username),
                "encryption": one(query, "encryption", "none"),
                "flow": one(query, "flow", ""),
            }]}]},
            "streamSettings": {
                "network": "raw" if one(query, "type", "tcp") in ("tcp", "raw") else one(query, "type"),
                "security": one(query, "security", "reality"),
                "realitySettings": {
                    "serverName": one(query, "sni"),
                    "fingerprint": one(query, "fp", "chrome"),
                    "publicKey": one(query, "pbk"),
                    "shortId": one(query, "sid", ""),
                    "spiderX": one(query, "spx", "/"),
                },
            },
        }],
    }
    if dns_host:
        config["routing"] = {"domainStrategy": "AsIs", "rules": [private_dns_rule(dns_host)]}
    return config


def hysteria_config(uri_path, server, socks_port):
    parsed = urllib.parse.urlsplit(uri_path.read_text().strip())
    if parsed.scheme not in ("hysteria2", "hy2"):
        raise ValueError("expected hysteria2 URI")
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if "@" not in parsed.netloc:
        raise ValueError("Hysteria URI is missing authentication")
    userinfo = parsed.netloc.rsplit("@", 1)[0]
    auth = urllib.parse.unquote(userinfo)
    if not auth or parsed.port is None:
        raise ValueError("Hysteria URI is missing authentication or port")
    if one(query, "obfs") != "salamander" or not one(query, "obfs-password"):
        raise ValueError("Hysteria URI is missing Salamander settings")
    return {
        "server": f"{server}:{parsed.port}",
        "auth": auth,
        "obfs": {"type": one(query, "obfs"), "salamander": {"password": one(query, "obfs-password")}},
        "tls": {
            "sni": one(query, "sni"),
            "insecure": one(query, "insecure", "0") in ("1", "true"),
            "pinSHA256": one(query, "pinSHA256"),
        },
        "socks5": {"listen": f"127.0.0.1:{socks_port}", "disableUDP": False},
    }


def hysteria_yaml(config):
    obfs = config["obfs"]
    tls = config["tls"]
    socks = config["socks5"]
    return "\n".join([
        f"server: {json.dumps(config['server'])}",
        f"auth: {json.dumps(config['auth'])}",
        "obfs:",
        f"  type: {json.dumps(obfs['type'])}",
        "  salamander:",
        f"    password: {json.dumps(obfs['salamander']['password'])}",
        "tls:",
        f"  sni: {json.dumps(tls['sni'])}",
        f"  insecure: {str(tls['insecure']).lower()}",
        f"  pinSHA256: {json.dumps(tls['pinSHA256'])}",
        "socks5:",
        f"  listen: {json.dumps(socks['listen'])}",
        f"  disableUDP: {str(socks['disableUDP']).lower()}",
        "",
    ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--dns-host", required=True)
    parser.add_argument("--reality-port", type=int, default=19101)
    parser.add_argument("--hysteria-port", type=int, default=19102)
    parser.add_argument("--xhttp-port", type=int, default=19103)
    args = parser.parse_args()
    source = pathlib.Path(args.client_dir)
    output = pathlib.Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _safe_write(path, data):
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(data)
        tmp.chmod(0o600)
        tmp.replace(path)

    reality = reality_config(source / "xray-vless-reality-uri.txt", args.server, args.reality_port, args.dns_host)
    _safe_write(output / "reality-client.json", json.dumps(reality, indent=2) + "\n")

    hysteria = hysteria_config(source / "hysteria2-uri.txt", args.server, args.hysteria_port)
    _safe_write(output / "hysteria-client.yaml", hysteria_yaml(hysteria))

    xhttp_path = source / "xray-xhttp-reality-client.json"
    xhttp = json.loads(xhttp_path.read_text())
    xhttp["inbounds"][0]["listen"] = "127.0.0.1"
    xhttp["inbounds"][0]["port"] = args.xhttp_port
    settings = xhttp["outbounds"][0]["settings"]
    if "vnext" in settings:
        settings["vnext"][0]["address"] = args.server
    else:
        settings["address"] = args.server
    routing = xhttp.setdefault("routing", {"domainStrategy": "AsIs", "rules": []})
    rule = private_dns_rule(args.dns_host)
    routing["rules"] = [rule] + [existing for existing in routing.get("rules", []) if existing != rule]
    _safe_write(output / "xhttp-client.json", json.dumps(xhttp, indent=2) + "\n")


if __name__ == "__main__":
    main()
