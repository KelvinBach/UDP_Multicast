# LAN Networking Concepts & Technical Deep Dive

This document explains the core networking concepts implemented in **LAN Messenger**, designed for Computer Networks students and instructors.

---

## 1. Network Topology & Peer-to-Peer (P2P) Architecture

Unlike typical Internet messengers (WhatsApp, Facebook Messenger, Zalo) that rely on centralized servers and databases, **LAN Messenger** is completely **serverless and decentralized**:

```text
                           Local Area Network (LAN) / Wi-Fi Subnet
                                (e.g., 10.133.17.0/24)
                                          │
       ┌──────────────────────────────────┼──────────────────────────────────┐
       │                                  │                                  │
       ▼                                  ▼                                  ▼
┌──────────────┐                   ┌──────────────┐                   ┌──────────────┐
│  Computer A  │                   │  Computer B  │                   │  Computer C  │
│10.133.17.147 │                   │ 10.133.17.54 │                   │ 10.133.17.88 │
│  (Port 5000) │                   │  (Port 5000) │                   │  (Port 5000) │
└──────────────┘                   └──────────────┘                   └──────────────┘
```

* **No Central Server**: Every client acts as both a **sender (client)** and a **receiver (server)**.
* **No External Internet Access Required**: All packets stay strictly inside the local broadcast domain.

---

## 2. IP Addressing & Broadcast Calculation

### Private IP Address Ranges (RFC 1918)
Private networks utilize reserved address spaces that are not routed on the public Internet:
* **Class A**: `10.0.0.0` - `10.255.255.255` (`10.0.0.0/8`)
* **Class B**: `172.16.0.0` - `172.31.255.255` (`172.16.0.0/12`)
* **Class C**: `192.168.0.0` - `192.168.255.255` (`192.168.0.0/16`)

### Automatic Broadcast Calculation
To send a packet to all hosts in the local subnet without hardcoding IP addresses, the application calculates:

$$\text{Network Address} = \text{Local IP} \ \& \ \text{Subnet Mask}$$

$$\text{Broadcast Address} = \text{Local IP} \ | \ (\sim\text{Subnet Mask})$$

#### Real Calculation Example:
* **Local IP:** `10.133.17.147` $\rightarrow$ `00001010 . 10000101 . 00010001 . 10010011`
* **Subnet Mask:** `255.255.255.0` $\rightarrow$ `11111111 . 11111111 . 11111111 . 00000000`
* **Network:** `10.133.17.0` $\rightarrow$ `00001010 . 10000101 . 00010001 . 00000000`
* **Broadcast:** `10.133.17.255` $\rightarrow$ `00001010 . 10000101 . 00010001 . 11111111`

In Python, this is executed using the standard `ipaddress.IPv4Network` module:
```python
net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
broadcast_address = str(net.broadcast_address)
```

---

## 3. Communication Modes: Unicast vs. Broadcast

| Metric | Unicast Chat | Broadcast ("Everyone") |
| :--- | :--- | :--- |
| **Transmission Type** | One-to-One (Point-to-Point) | One-to-All (Subnet-wide) |
| **Target Address** | Specific peer IP (e.g., `10.133.17.54`) | Directed broadcast IP (e.g., `10.133.17.255`) |
| **Socket Call** | `sock.sendto(data, (target_ip, port))` | `sock.setsockopt(SO_BROADCAST, 1)`<br>`sock.sendto(data, (bcast_ip, port))` |
| **Network Impact** | Packets routed only to the target MAC address | Replicated by switches/access points to all hosts |

---

## 4. Peer Discovery & Liveness Protocol

### Discovery Flow
1. **Startup Announcement:**
   When Client A starts up, it broadcasts a `DISCOVERY` packet to the subnet:
   ```json
   {
       "type": "DISCOVERY",
       "sender": "MinhChien",
       "sender_ip": "10.133.17.147",
       "port": 5000,
       "timestamp": "15:30"
   }
   ```
2. **Immediate Discovery Reply:**
   When existing Client B receives this `DISCOVERY` packet, Client B immediately sends a unicast discovery response back to Client A. This ensures both peers see each other instantly without waiting for the next periodic cycle.

3. **Periodic Heartbeat (Liveness):**
   * Every **5 seconds**, each client broadcasts a `HEARTBEAT` packet.
   * If a client receives no heartbeat from a peer for **15 seconds** (timeout), the peer is marked as `○ Offline`.

4. **Graceful Exit:**
   When closing the application, a `GOODBYE` packet is broadcast, instantly marking the user as offline on all peers' screens without waiting for the 15-second timeout.

---

## 5. Windows Firewall & Network Category

When running UDP socket applications on Windows:

1. **Network Profile (Private vs. Public):**
   * By default, Wi-Fi networks in Windows are categorized as **Public**, which silently drops incoming UDP packets and ICMP Echo requests (Ping).
   * Setting the connection to **Private** allows inbound connections for applications on the same subnet.

2. **UDP Port Unreachable (WSAECONNRESET / 10054):**
   * On Windows, if a UDP packet is sent to a closed port, an ICMP "Port Unreachable" packet is sent back.
   * Windows delivers this error to subsequent `recvfrom()` calls as `WSAECONNRESET` (10054).
   * In `app/network/udp.py`, we disable this behavior using socket IOCTL:
     ```python
     SIO_UDP_CONNRESET = 0x9800000C
     sock.ioctl(SIO_UDP_CONNRESET, False)
     ```
