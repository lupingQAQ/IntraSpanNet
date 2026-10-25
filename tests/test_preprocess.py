import socket

import numpy as np
import pytest

from quietspan.preprocess import FLOW_LEN, flows_from_pcap

dpkt = pytest.importorskip("dpkt")


def _write_pcap(path):
    packets = []
    for i in range(6):
        tcp = dpkt.tcp.TCP(
            sport=40000,
            dport=443,
            seq=1000 + i,
            data=bytes([65 + i]) * 300,
        )
        ip = dpkt.ip.IP(
            src=socket.inet_aton("192.0.2.1"),
            dst=socket.inet_aton("192.0.2.2"),
            p=dpkt.ip.IP_PROTO_TCP,
            data=tcp,
        )
        ip.len = len(ip)
        eth = dpkt.ethernet.Ethernet(
            src=b"\x00\x11\x22\x33\x44\x55",
            dst=b"\x66\x77\x88\x99\xaa\xbb",
            type=dpkt.ethernet.ETH_TYPE_IP,
            data=ip,
        )
        packets.append(bytes(eth))
    with open(path, "wb") as fh:
        writer = dpkt.pcap.Writer(fh)
        for i, buf in enumerate(packets):
            writer.writepkt(buf, ts=1000 + i)
        writer.close()


def test_flow_shape_and_ip_masking(tmp_path):
    path = tmp_path / "sample.pcap"
    _write_pcap(path)
    flows = flows_from_pcap(str(path))
    assert len(flows) == 1
    flow = flows[0]
    assert flow.shape == (FLOW_LEN,)
    assert flow.dtype == np.uint8
    assert flow[12:20].tolist() == [0] * 8
    assert flow[20:24].sum() > 0


def test_empty_capture(tmp_path):
    path = tmp_path / "empty.pcap"
    with open(path, "wb") as fh:
        writer = dpkt.pcap.Writer(fh)
        writer.close()
    assert flows_from_pcap(str(path)) == []

