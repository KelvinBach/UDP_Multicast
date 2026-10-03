"""
Network Interface Detection and IP/Subnet/Broadcast Calculation.
Compliant with RFC 1918 Private Address Spaces:
- 10.0.0.0/8
- 172.16.0.0/12
- 192.168.0.0/16
"""

import ipaddress
import platform
import socket
import subprocess
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class NetworkInfo:
    interface_name: str
    ip_address: str
    subnet_mask: str
    network_address: str
    broadcast_address: str
    gateway: Optional[str]
    is_connected: bool
    status_text: str

    def to_display_dict(self) -> Dict[str, str]:
        return {
            "Interface": self.interface_name,
            "IP Address": self.ip_address,
            "Subnet Mask": self.subnet_mask,
            "Network": self.network_address,
            "Broadcast": self.broadcast_address,
            "Gateway": self.gateway or "N/A",
            "Status": self.status_text,
        }


def is_private_ipv4(ip_str: str) -> bool:
    """Checks whether an IPv4 address belongs to RFC 1918 private ranges."""
    try:
        ip = ipaddress.IPv4Address(ip_str)
        return ip.is_private and not ip.is_loopback and not ip.is_link_local
    except ValueError:
        return False


def get_default_gateway_windows() -> Optional[str]:
    """Retrieves default gateway on Windows using 'route print 0.0.0.0'."""
    try:
        output = subprocess.check_output(
            "route print 0.0.0.0", shell=True, text=True, stderr=subprocess.DEVNULL
        )
        for line in output.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                gw = parts[2]
                if gw != "On-link" and is_valid_ipv4(gw):
                    return gw
    except Exception:
        pass
    return None


def is_valid_ipv4(ip_str: str) -> bool:
    """Validates IPv4 string."""
    try:
        ipaddress.IPv4Address(ip_str)
        return True
    except ValueError:
        return False


def detect_best_route_ip() -> Optional[str]:
    """
    Connects a dummy UDP socket to a public IP to determine which local interface
    the OS routing table selects as the default outbound route.
    Does not actually send any packets over the wire.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return None


def get_all_interfaces() -> List[Dict[str, Any]]:
    """Returns a list of all detected IPv4 network interfaces."""
    interfaces = []
    if HAS_PSUTIL:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for iface_name, addr_list in addrs.items():
            stat = stats.get(iface_name)
            is_up = stat.isup if stat else False
            for addr in addr_list:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    interfaces.append({
                        "name": iface_name,
                        "ip": addr.address,
                        "netmask": addr.netmask or "255.255.255.0",
                        "is_up": is_up
                    })
    else:
        # Fallback using standard socket & ipconfig
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if not ip.startswith("127."):
                    interfaces.append({
                        "name": "Local Adapter",
                        "ip": ip,
                        "netmask": "255.255.255.0",
                        "is_up": True
                    })
        except Exception:
            pass

    return interfaces


def detect_network(preferred_interface: str = "Auto") -> NetworkInfo:
    """
    Automatically detects the active LAN network interface,
    calculates Network Address and Broadcast Address.
    """
    best_route_ip = detect_best_route_ip()
    gateway = get_default_gateway_windows() if platform.system() == "Windows" else None

    all_ifaces = get_all_interfaces()

    selected = None

    # 1. If user selected a specific interface name
    if preferred_interface and preferred_interface != "Auto":
        for iface in all_ifaces:
            if iface["name"].lower() == preferred_interface.lower():
                selected = iface
                break

    # 2. Try matching the outbound route IP
    if not selected and best_route_ip:
        for iface in all_ifaces:
            if iface["ip"] == best_route_ip:
                selected = iface
                break

    # 3. Look for active (Up) interface with private IPv4
    if not selected:
        for iface in all_ifaces:
            if iface.get("is_up") and is_private_ipv4(iface["ip"]):
                selected = iface
                break

    # 4. Any private IPv4
    if not selected:
        for iface in all_ifaces:
            if is_private_ipv4(iface["ip"]):
                selected = iface
                break

    # 5. Fallback to any non-loopback interface
    if not selected and all_ifaces:
        selected = all_ifaces[0]

    # If absolutely nothing found, create offline placeholder
    if not selected:
        return NetworkInfo(
            interface_name="None",
            ip_address="127.0.0.1",
            subnet_mask="255.0.0.0",
            network_address="127.0.0.0",
            broadcast_address="127.255.255.255",
            gateway=None,
            is_connected=False,
            status_text="No active LAN connection detected"
        )

    ip = selected["ip"]
    mask = selected.get("netmask") or "255.255.255.0"

    # Calculate network and broadcast using ipaddress
    try:
        net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
        network_addr = str(net.network_address)
        broadcast_addr = str(net.broadcast_address)
    except Exception:
        network_addr = "Unknown"
        broadcast_addr = "255.255.255.255"

    is_conn = is_private_ipv4(ip) or (selected.get("is_up") and not ip.startswith("169.254"))
    status_text = "● LAN Connected" if is_conn else "No active LAN connection detected"

    return NetworkInfo(
        interface_name=selected["name"],
        ip_address=ip,
        subnet_mask=mask,
        network_address=network_addr,
        broadcast_address=broadcast_addr,
        gateway=gateway,
        is_connected=is_conn,
        status_text=status_text
    )
