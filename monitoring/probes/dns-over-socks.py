#!/usr/bin/env python3
import argparse
import ipaddress
import os
import socket
import struct


def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise RuntimeError("unexpected EOF")
        data += chunk
    return data


def encode_name(name):
    return b"".join(bytes((len(label),)) + label.encode("ascii") for label in name.rstrip(".").split(".")) + b"\0"


def skip_name(packet, offset):
    while True:
        length = packet[offset]
        if length & 0xC0 == 0xC0:
            return offset + 2
        offset += 1
        if length == 0:
            return offset
        offset += length


def answers(packet):
    _, flags, qd, an, _, _ = struct.unpack("!HHHHHH", packet[:12])
    if flags & 0x000F:
        raise RuntimeError(f"DNS rcode {flags & 0x000F}")
    offset = 12
    for _ in range(qd):
        offset = skip_name(packet, offset) + 4
    result = []
    for _ in range(an):
        offset = skip_name(packet, offset)
        rtype, _, _, length = struct.unpack("!HHIH", packet[offset:offset + 10])
        offset += 10
        value = packet[offset:offset + length]
        offset += length
        if rtype == 1 and length == 4:
            result.append(str(ipaddress.ip_address(value)))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socks-port", type=int, required=True)
    parser.add_argument("--dns-host", required=True)
    parser.add_argument("--dns-port", type=int, default=5353)
    parser.add_argument("--name", required=True)
    parser.add_argument("--expect", choices=("normal", "blocked"), required=True)
    args = parser.parse_args()

    query_id = int.from_bytes(os.urandom(2), "big")
    query = struct.pack("!HHHHHH", query_id, 0x0100, 1, 0, 0, 0) + encode_name(args.name) + struct.pack("!HH", 1, 1)
    with socket.create_connection(("127.0.0.1", args.socks_port), timeout=8) as sock:
        sock.sendall(b"\x05\x01\x00")
        if recv_exact(sock, 2) != b"\x05\x00":
            raise RuntimeError("SOCKS authentication failed")
        host = ipaddress.ip_address(args.dns_host)
        address = b"\x01" + host.packed if host.version == 4 else b"\x04" + host.packed
        # Pipeline the first DNS frame with SOCKS CONNECT. XHTTP stream-one can
        # otherwise finish an empty upload before a delayed first TCP payload.
        sock.sendall(b"\x05\x01\x00" + address + struct.pack("!H", args.dns_port) + struct.pack("!H", len(query)) + query)
        reply = recv_exact(sock, 4)
        if reply[1] != 0:
            raise RuntimeError(f"SOCKS connect failed: {reply[1]}")
        if reply[3] == 1:
            address_length = 4
        elif reply[3] == 4:
            address_length = 16
        elif reply[3] == 3:
            address_length = recv_exact(sock, 1)[0]
        else:
            raise RuntimeError("invalid SOCKS address type")
        recv_exact(sock, address_length)
        recv_exact(sock, 2)
        packet = recv_exact(sock, struct.unpack("!H", recv_exact(sock, 2))[0])
    found = answers(packet)
    if args.expect == "normal" and (not found or found == ["0.0.0.0"]):
        raise RuntimeError("normal name did not resolve")
    if args.expect == "blocked" and found != ["0.0.0.0"]:
        raise RuntimeError("filter response mismatch")


if __name__ == "__main__":
    main()
