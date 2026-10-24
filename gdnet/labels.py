"""Label definitions for GDNet.

The class order below is the training order stored in the released
checkpoints. Do not reorder: the product head and prototype matrix are
indexed by this order.
"""

from __future__ import annotations

PRODUCTS: list[str] = [
    "windows_defender",
    "clamav_freshclam_win",
    "clamav_freshclam",
    "velociraptor",
    "velociraptor_win",
    "osquery",
    "wazuh_agent",
    "wireguard",
    "openvpn",
    "stunnel",
    "squid_proxy",
    "ntopng",
    "guacamole_mgmt",
    "waf_modsecurity",
    "suricata_update",
    "web_http",
    "ssh",
    "ftp",
]

PRODUCT_TO_TYPE: dict[str, int] = {
    "waf_modsecurity": 0,
    "squid_proxy": 1,
    "guacamole_mgmt": 2,
    "ntopng": 3,
    "suricata_update": 3,
    "stunnel": 4,
    "wireguard": 4,
    "openvpn": 4,
    "velociraptor": 5,
    "velociraptor_win": 5,
    "wazuh_agent": 5,
    "osquery": 5,
    "windows_defender": 6,
    "clamav_freshclam": 6,
    "clamav_freshclam_win": 6,
    "web_http": 7,
    "ftp": 8,
    "ssh": 9,
}

PRODUCT_TO_TIER: dict[str, int] = {
    "waf_modsecurity": 0,
    "squid_proxy": 0,
    "guacamole_mgmt": 0,
    "ntopng": 0,
    "suricata_update": 0,
    "stunnel": 0,
    "wireguard": 0,
    "openvpn": 0,
    "velociraptor": 1,
    "velociraptor_win": 1,
    "wazuh_agent": 1,
    "osquery": 1,
    "windows_defender": 1,
    "clamav_freshclam": 1,
    "clamav_freshclam_win": 1,
    "web_http": 2,
    "ftp": 2,
    "ssh": 2,
}

TYPE_NAMES_ZH: list[str] = [
    "WAF",
    "AC 上网行为管理",
    "堡垒机",
    "NDR 流量探测",
    "零信任 / VPN",
    "EDR / HIDS",
    "杀毒",
    "浏览器",
    "文件传输",
    "远程管理",
]

TYPE_NAMES_EN: list[str] = [
    "WAF",
    "Internet behavior management",
    "Bastion host",
    "NDR",
    "Zero trust / VPN",
    "EDR / HIDS",
    "Antivirus",
    "Browser",
    "File transfer",
    "Remote administration",
]

TIER_NAMES_ZH: list[str] = ["安全设备", "安全软件", "正常软件"]
TIER_NAMES_EN: list[str] = ["Security appliance", "Security software", "Productivity software"]

DISPLAY_NAMES: dict[str, str] = {
    "windows_defender": "Windows Defender",
    "clamav_freshclam_win": "ClamAV freshclam (Windows)",
    "clamav_freshclam": "ClamAV freshclam",
    "velociraptor": "Velociraptor",
    "velociraptor_win": "Velociraptor (Windows)",
    "osquery": "osquery",
    "wazuh_agent": "Wazuh agent",
    "wireguard": "WireGuard",
    "openvpn": "OpenVPN",
    "stunnel": "stunnel",
    "squid_proxy": "Squid proxy",
    "ntopng": "ntopng",
    "guacamole_mgmt": "Apache Guacamole",
    "waf_modsecurity": "ModSecurity WAF",
    "suricata_update": "Suricata update",
    "web_http": "Web browsing",
    "ssh": "SSH",
    "ftp": "FTP",
}


def describe(product: str, lang: str = "zh") -> dict[str, str]:
    """Return tier, type and display name for a product label."""
    if product not in PRODUCT_TO_TIER:
        raise KeyError(f"unknown product: {product}")
    type_id = PRODUCT_TO_TYPE[product]
    tier_id = PRODUCT_TO_TIER[product]
    type_names = TYPE_NAMES_ZH if lang == "zh" else TYPE_NAMES_EN
    tier_names = TIER_NAMES_ZH if lang == "zh" else TIER_NAMES_EN
    return {
        "product": product,
        "display": DISPLAY_NAMES.get(product, product),
        "type": type_names[type_id],
        "tier": tier_names[tier_id],
    }
