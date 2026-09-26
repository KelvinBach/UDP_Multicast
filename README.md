# LAN Messenger — Computer Networks Practical Project

A lightweight, clean, serverless **LAN Messenger** desktop application built in Python for Computer Networks practical coursework.

It demonstrates essential networking fundamentals: **automatic network interface detection**, **broadcast IP calculation**, **UDP broadcast peer discovery**, **periodic heartbeats**, and **direct UDP unicast & broadcast chat**.

---

## 1. What the Project Does

* **Zero-Configuration Network Detection**: Automatically discovers your local IPv4 address, subnet mask, default gateway, and calculates the network and broadcast addresses.
* **Automatic Peer Discovery**: Announces your presence across the local network using UDP broadcast (`255.255.255.255` or subnet broadcast `10.133.17.255`).
* **Live Online Presence**: Maintains peer liveness via a 5-second heartbeat; marks disconnected users offline after 15 seconds.
* **Everyone Chat (Broadcast)**: Sends messages to all peers on the LAN via UDP broadcast.
* **Direct Chat (Unicast)**: Click any discovered peer to start a private 1-to-1 conversation via direct UDP unicast.
* **Clean Messenger/Zalo UI**: Intuitive sidebar layout with your profile, active chats, online user list, and settings.
* **No Database & No Internet Required**: Fully decentralized and peer-to-peer.

---

## 2. LAN-Only Architecture

```text
PC A (MinhChien)
10.133.17.147
     │
     │ UDP Broadcast (:5000)
     ▼
10.133.17.255:5000 (Subnet Broadcast)
     │
     ├───► PC B (An)       10.133.17.54:5000
     │
     └───► PC C (Nam)      10.133.17.88:5000
```

There is **no central server**, **no cloud backend**, and **no database**. Every computer running the application binds to a local UDP port (default `5000`) and acts simultaneously as:
* A **UDP Receiver** (listening thread continuously calling `recvfrom`).
* A **UDP Sender** (transmitting unicast or broadcast datagrams using `sendto`).

---

## 3. Project Structure

```text
lan-messenger/
│
├── README.md                  # Complete documentation and testing guide
├── requirements.txt           # Python dependencies (psutil)
├── .gitignore                 # Git ignore file
├── run.py                     # Convenience launcher
│
├── app/
│   ├── main.py                # Main application entry point
│   ├── config.py              # Local JSON configuration manager
│   │
│   ├── network/
│   │   ├── interface.py       # Auto-detects IP, subnet, broadcast & gateway
│   │   ├── udp.py             # UDP socket manager (sendto/recvfrom, threading)
│   │   ├── discovery.py       # P2P discovery, heartbeats, and timeout liveness
│   │   └── broadcast.py       # Subnet-wide broadcast chat transmission
│   │
│   ├── protocol/
│   │   └── message.py         # JSON-over-UDP protocol packets and encoders
│   │
│   ├── models/
│   │   ├── user.py            # Peer model with online status evaluation
│   │   └── chat.py            # Message and Conversation data models
│   │
│   └── ui/
│       ├── main_window.py     # Main Messenger/Zalo window and event dispatcher
│       ├── chat_view.py       # Scrollable chat messages and input controls
│       └── settings.py        # Settings dialog and first-launch username prompt
│
└── docs/
    └── networking.md          # In-depth technical theory on IP and UDP
```

---

## 4. Installation & Requirements

### Prerequisites
* **Python 3.8+** (tested on Python 3.10, 3.11, 3.12, 3.13)
* Standard Python Tkinter (included with standard Python on Windows and macOS)

### Quick Setup

1. Open PowerShell or Terminal in the project directory:
   ```bash
   cd lan-messenger
   ```

2. (Optional but recommended) Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 5. How to Run

Launch the application:
```bash
python run.py
```
*(Or alternatively: `python app/main.py`)*

On first launch, you will be prompted to enter your display name (e.g. `MinhChien`). The username is saved locally in `config.json` so you only have to enter it once.

---

## 6. Connecting Multiple Computers on the Same LAN / Wi-Fi

1. Connect both computers (e.g., Computer A and Computer B) to the **same Wi-Fi router or mobile hotspot**.
2. **Important Windows Firewall Settings:**
   * On Windows, make sure your Wi-Fi network profile is set to **Private** (not Public):
     * *Settings* $\rightarrow$ *Network & internet* $\rightarrow$ *Wi-Fi* $\rightarrow$ Select network $\rightarrow$ Set to **Private network**.
   * If a Windows Defender Firewall popup appears when running the app, check **Private networks** and click **Allow access**.
   * Or allow UDP port 5000 in PowerShell (Admin):
     ```powershell
     netsh advfirewall firewall add rule name="LAN_Messenger_5000" dir=in action=allow protocol=UDP localport=5000
     ```
3. Run `python run.py` on Computer A and Computer B.
4. Both users will automatically appear in each other's **ONLINE** sidebar list within seconds!

---

## 7. How Network Operations Work

### A. Automatic Network Discovery
1. Computer A launches and sends a UDP broadcast packet to `10.133.17.255:5000`:
   ```json
   {
       "type": "DISCOVERY",
       "sender": "MinhChien",
       "sender_ip": "10.133.17.147",
       "port": 5000
   }
   ```
2. Computer B (`10.133.17.54`) receives the packet and adds `MinhChien` to its **ONLINE** list.
3. Computer B immediately replies with its own discovery packet so Computer A discovers Computer B right away.
4. Every 5 seconds, each node broadcasts a lightweight `HEARTBEAT`. If no heartbeat is heard for 15 seconds, the user is marked `○ Offline`.

### B. Broadcast Chat ("Everyone")
1. In the sidebar, click **Everyone**.
2. Type a message and click **Send**.
3. The message is transmitted to the subnet broadcast address (`10.133.17.255:5000`):
   ```json
   {
       "type": "CHAT",
       "mode": "BROADCAST",
       "sender": "MinhChien",
       "sender_ip": "10.133.17.147",
       "message": "Hello everyone!",
       "timestamp": "15:35"
   }
   ```
4. All running clients receive and display the message in their "Everyone" conversation.

### C. Direct Unicast Chat
1. In the **ONLINE** list, click on a user (e.g., **An** at `10.133.17.54`).
2. A direct chat tab opens showing:
   ```text
   An
   ● 10.133.17.54:5000 · Unicast
   ```
3. Type a message and send. The packet is sent directly to `10.133.17.54:5000` via:
   ```python
   socket.sendto(data, ("10.133.17.54", 5000))
   ```
4. Only Computer B receives this packet.

---

## 8. UDP Packet Structure

All messages are UTF-8 encoded JSON strings packed directly into UDP datagrams:

### 1. Discovery Packet
```json
{
    "type": "DISCOVERY",
    "sender": "MinhChien",
    "sender_ip": "10.133.17.147",
    "port": 5000,
    "timestamp": "15:30"
}
```

### 2. Broadcast Chat Packet
```json
{
    "type": "CHAT",
    "mode": "BROADCAST",
    "sender": "MinhChien",
    "sender_ip": "10.133.17.147",
    "message": "Hello everyone!",
    "timestamp": "15:32"
}
```

### 3. Unicast Chat Packet
```json
{
    "type": "CHAT",
    "mode": "UNICAST",
    "sender": "MinhChien",
    "sender_ip": "10.133.17.147",
    "message": "Hey An, are you ready for the presentation?",
    "timestamp": "15:33",
    "target_ip": "10.133.17.54"
}
```

---

## 9. How to Test Using Wireshark

Wireshark is the standard tool to inspect LAN packets in Computer Networks labs.

### Step-by-Step Packet Capture:
1. Open **Wireshark** and select your active network adapter (**Wi-Fi** or **Ethernet**).
2. In the display filter toolbar at the top, enter:
   ```text
   udp.port == 5000
   ```
   and press **Enter**.
3. Send a message in **Broadcast** mode ("Everyone"):
   * Look at the packet in Wireshark:
     * **Source IP:** Your machine's IP (e.g., `10.133.17.147`)
     * **Destination IP:** Broadcast IP (e.g., `10.133.17.255`)
     * **Protocol:** UDP
     * **Data length:** Size of the JSON string
4. Send a message in **Unicast** mode:
   * Look at the packet in Wireshark:
     * **Source IP:** Your machine's IP (e.g., `10.133.17.147`)
     * **Destination IP:** Peer's machine IP (e.g., `10.133.17.54`)
5. Click on the packet and expand the **Data** or **JavaScript Object Notation (JSON)** pane at the bottom to inspect the raw JSON payload in real time!
