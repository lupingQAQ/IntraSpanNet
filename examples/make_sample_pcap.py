#!/usr/bin/env python3
"""Generate a small synthetic capture for pipeline testing.

The capture contains three short flows with random-looking payloads. It is
not a product sample and is not intended to produce a meaningful label.
"""

from __future__ import annotations

import argparse
import os
import socket

import dpkt


def tcp_packet(src: str, dst: str, sport: int, dport: int, seq: int, payload: bytes) -> bytes:
    tcp = dpkt.tcp.TCP(sport=sport, dport=dport, seq=seq, flags=dpkt.tcp.TH_PUSH | dpkt.tcp.TH_ACK, data=payload)
    ip = dpkt.ip.IP(
        src=socket.inet_aton(src),
        dst=socket.inet_aton(dst),
        p=dpkt.ip.IP_PROTO_TCP,
        data=tcp,
    )
    ip.len = len(ip)
    return bytes(
        dpkt.ethernet.Ethernet(
            src=b"\x00\x11\x22\x33\x44\x55",
            dst=b"\x66\x77\x88\x99\xaa\xbb",
            type=dpkt.ethernet.ETH_TYPE_IP,
            data=ip,
        )
    )


def udp_packet(src: str, dst: str, sport: int, dport: int, payload: bytes) -> bytes:
    udp = dpkt.udp.UDP(sport=sport, dport=dport, data=payload)
    udp.ulen = len(udp)
    ip = dpkt.ip.IP(
        src=socket.inet_aton(src),
        dst=socket.inet_aton(dst),
        p=dpkt.ip.IP_PROTO_UDP,
        data=udp,
    )
    ip.len = len(ip)
    return bytes(
        dpkt.ethernet.Ethernet(
            src=b"\x00\x11\x22\x33\x44\x55",
            dst=b"\x66\x77\x88\x99\xaa\xbb",
            type=dpkt.ethernet.ETH_TYPE_IP,
            data=ip,
        )
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "sample.pcap"))
    args = ap.parse_args()

    packets = []
    ts = 1_700_000_000.0
    for i in range(5):
        payload = bytes([0x16, 0x03, 0x01, 0x00, 0x40]) + bytes((i * 17 + j) % 256 for j in range(200))
        packets.append((ts + i * 0.01, tcp_packet("192.0.2.10", "192.0.2.20", 41000, 443, 1000 + i * 200, payload)))
    for i in range(5):
        payload = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00" + b"example" + b"\x00\x00\x01\x00\x01"
        packets.append((ts + 1 + i * 0.02, udp_packet("192.0.2.10", "192.0.2.53", 52000, 53, payload)))
    for i in range(5):
        payload = b"GET / HTTP/1.1\r\nHost: example.test\r\n\r\n"
        packets.append((ts + 2 + i * 0.03, tcp_packet("192.0.2.10", "192.0.2.80", 43000, 80, 5000 + i * 100, payload)))

    with open(args.out, "wb") as fh:
        writer = dpkt.pcap.Writer(fh)
        for stamp, buf in packets:
            writer.writepkt(buf, ts=stamp)
        writer.close()
    print(f"wrote {args.out} ({os.path.getsize(args.out)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

