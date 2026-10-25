"""Capture preprocessing: pcap/pcapng to 1600-byte flow vectors.

Format (same as the training pipeline):
  - first 5 packets of each unidirectional flow
  - per packet: 80 bytes of IPv4 header + L4 header, then 240 bytes of payload
  - zero padding to 320 bytes per packet, zero padding to 1600 bytes per flow
  - IPv4 source and destination addresses are zeroed (bytes 12:20)

The parser uses dpkt (BSD-3-Clause). It supports Ethernet, VLAN, and raw IPv4
link types in pcap and pcapng files.
"""

from __future__ import annotations

import glob
import os
from collections.abc import Iterable, Iterator

import numpy as np

HDR = 80
PAY = 240
NPKT = 5
PKT_LEN = HDR + PAY
FLOW_LEN = NPKT * PKT_LEN


def _dpkt():
    try:
        import dpkt
        import dpkt.ethernet
        import dpkt.ip
        import dpkt.pcap
        import dpkt.pcapng
        import dpkt.tcp
        import dpkt.udp
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "pcap preprocessing requires dpkt. Install it with: pip install dpkt"
        ) from exc
    return dpkt


def _reader(path: str):
    dpkt = _dpkt()
    fh = open(path, "rb")
    try:
        try:
            return fh, dpkt.pcap.Reader(fh), "pcap"
        except Exception:
            fh.seek(0)
            try:
                return fh, dpkt.pcapng.Reader(fh), "pcapng"
            except Exception as exc:
                fh.close()
                raise ValueError(f"{path}: not a readable pcap or pcapng file") from exc
    except Exception:
        fh.close()
        raise


def _unwrap_ip(dpkt, buf: bytes):
    try:
        eth = dpkt.ethernet.Ethernet(buf)
        layer = eth.data
        while layer.__class__.__name__ == "VLAN":
            layer = layer.data
        if isinstance(layer, dpkt.ip.IP):
            return layer
    except Exception:
        pass
    try:
        ip = dpkt.ip.IP(buf)
        if ip.v == 4:
            return ip
    except Exception:
        pass
    return None


def flows_from_pcap(path: str, min_pkts: int = 1) -> list[np.ndarray]:
    """Extract unidirectional flows from one capture file."""
    dpkt = _dpkt()
    fh, reader, _ = _reader(path)
    flows: dict[tuple, list[bytes]] = {}
    try:
        for _, buf in reader:
            ip = _unwrap_ip(dpkt, buf)
            if ip is None:
                continue
            if isinstance(ip.data, dpkt.tcp.TCP):
                l4 = ip.data
            elif isinstance(ip.data, dpkt.udp.UDP):
                l4 = ip.data
            else:
                continue
            key = (bytes(ip.src), int(l4.sport), bytes(ip.dst), int(l4.dport), int(ip.p))
            blocks = flows.setdefault(key, [])
            if len(blocks) >= NPKT:
                continue
            header = (bytes(ip) + bytes(l4))[:HDR]
            header = header + b"\x00" * (HDR - len(header))
            payload = bytes(l4.data)[:PAY]
            payload = payload + b"\x00" * (PAY - len(payload))
            blocks.append(header + payload)
    finally:
        fh.close()

    out: list[np.ndarray] = []
    for blocks in flows.values():
        if len(blocks) < min_pkts:
            continue
        raw = b"".join(blocks)
        raw = raw + b"\x00" * (FLOW_LEN - len(raw))
        arr = np.frombuffer(raw, dtype=np.uint8).copy()
        arr[12:20] = 0
        out.append(arr)
    return out


def flow_vectors_from_pcap(path: str, min_pkts: int = 1) -> np.ndarray:
    flows = flows_from_pcap(path, min_pkts=min_pkts)
    if not flows:
        return np.zeros((0, FLOW_LEN), dtype=np.uint8)
    return np.stack(flows).astype(np.uint8, copy=False)


def flow_vectors_from_paths(paths: Iterable[str], min_pkts: int = 1) -> np.ndarray:
    arrays: list[np.ndarray] = []
    for path in paths:
        arrays.append(flow_vectors_from_pcap(path, min_pkts=min_pkts))
    arrays = [a for a in arrays if len(a)]
    if not arrays:
        return np.zeros((0, FLOW_LEN), dtype=np.uint8)
    return np.concatenate(arrays, axis=0)


def expand_paths(patterns: Iterable[str]) -> list[str]:
    files: list[str] = []
    for pattern in patterns:
        if os.path.isdir(pattern):
            files.extend(
                glob.glob(os.path.join(pattern, "*.pcap"))
                + glob.glob(os.path.join(pattern, "*.pcapng"))
                + glob.glob(os.path.join(pattern, "*.cap"))
            )
        else:
            files.extend(glob.glob(pattern))
    return sorted(set(files))


def read_flow_bin(path: str) -> np.ndarray:
    arr = np.fromfile(path, dtype=np.uint8)
    if len(arr) != FLOW_LEN:
        raise ValueError(f"{path}: expected {FLOW_LEN} bytes, got {len(arr)}")
    return arr


def iter_flow_bins(directory: str) -> Iterator[tuple[str, np.ndarray]]:
    for path in sorted(glob.glob(os.path.join(directory, "flow_*.bin"))):
        yield path, read_flow_bin(path)


def write_flow_bins(directory: str, flows: np.ndarray, prefix: str = "flow") -> list[str]:
    os.makedirs(directory, exist_ok=True)
    paths = []
    for i, flow in enumerate(flows):
        path = os.path.join(directory, f"{prefix}_{i:06d}.bin")
        flow.astype(np.uint8, copy=False).tofile(path)
        paths.append(path)
    return paths
