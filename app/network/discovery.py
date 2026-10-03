"""
Peer-to-Peer LAN Discovery and Heartbeat Service.
Uses UDP Broadcast over LAN to discover peers and track online status.
"""

import threading
import time
from typing import Dict, Callable, Optional
from app.models.user import User
from app.protocol.message import (
    TYPE_DISCOVERY,
    TYPE_HEARTBEAT,
    TYPE_GOODBYE,
    create_discovery_message,
    create_heartbeat_message,
    create_goodbye_message,
    encode_message,
)
from app.network.udp import UdpSocketManager


class DiscoveryService:
    def __init__(
        self,
        udp_manager: UdpSocketManager,
        username: str,
        local_ip: str,
        broadcast_ip: str,
        port: int = 5000,
        heartbeat_interval: float = 5.0,
        offline_timeout: float = 15.0,
        on_users_updated: Optional[Callable[[Dict[str, User]], None]] = None,
    ):
        self.udp_manager = udp_manager
        self.username = username
        self.local_ip = local_ip
        self.broadcast_ip = broadcast_ip
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        self.offline_timeout = offline_timeout
        self.on_users_updated = on_users_updated

        self.users: Dict[str, User] = {}
        self._lock = threading.Lock()
        self._is_running = False
        self._timer_thread: Optional[threading.Thread] = None

    def start(self):
        """Starts periodic discovery broadcast and offline sweep."""
        self._is_running = True
        # Send initial discovery announcement immediately
        self.broadcast_announcement()

        self._timer_thread = threading.Thread(
            target=self._run_heartbeat_loop,
            name="discovery-heartbeat-thread",
            daemon=True,
        )
        self._timer_thread.start()

    def stop(self):
        """Sends goodbye announcement and stops discovery service."""
        self._is_running = False
        self.broadcast_goodbye()

    def update_identity(self, username: str, local_ip: str, broadcast_ip: str, port: int):
        """Updates local peer identity and broadcasts refreshed discovery packet."""
        self.username = username
        self.local_ip = local_ip
        self.broadcast_ip = broadcast_ip
        self.port = port
        self.broadcast_announcement()

    def broadcast_announcement(self):
        """Broadcasts a DISCOVERY message to the local subnet."""
        if not self.broadcast_ip or self.broadcast_ip == "255.255.255.255" and not self.local_ip:
            return
        msg = create_discovery_message(self.username, self.local_ip, self.port)
        data = encode_message(msg)
        self.udp_manager.send(data, self.broadcast_ip, self.port, is_broadcast=True)

    def broadcast_heartbeat(self):
        """Broadcasts a periodic HEARTBEAT message to maintain online presence."""
        msg = create_heartbeat_message(self.username, self.local_ip, self.port)
        data = encode_message(msg)
        self.udp_manager.send(data, self.broadcast_ip, self.port, is_broadcast=True)

    def broadcast_goodbye(self):
        """Broadcasts a GOODBYE packet so peers can immediately show offline status."""
        msg = create_goodbye_message(self.username, self.local_ip)
        data = encode_message(msg)
        self.udp_manager.send(data, self.broadcast_ip, self.port, is_broadcast=True)

    def handle_packet(self, packet: dict, sender_addr: tuple):
        """Processes incoming discovery, heartbeat, and goodbye packets."""
        sender_ip = packet.get("sender_ip") or sender_addr[0]
        # Ignore our own discovery broadcast packets
        if sender_ip == self.local_ip:
            return

        msg_type = packet.get("type")
        username = packet.get("sender", "Unknown")
        port = packet.get("port", self.port)

        changed = False
        with self._lock:
            if msg_type in (TYPE_DISCOVERY, TYPE_HEARTBEAT):
                if sender_ip in self.users:
                    user = self.users[sender_ip]
                    was_online = user.is_online(self.offline_timeout)
                    user.update_seen(username=username, port=port)
                    if not was_online:
                        changed = True
                else:
                    self.users[sender_ip] = User(
                        username=username,
                        ip=sender_ip,
                        port=port,
                        last_seen=time.time(),
                    )
                    changed = True

                # If this was a new discovery from a peer, reply directly with unicast discovery
                # so the newly joined peer immediately knows about us without waiting 5 seconds!
                if msg_type == TYPE_DISCOVERY:
                    reply_msg = create_discovery_message(self.username, self.local_ip, self.port)
                    self.udp_manager.send(
                        encode_message(reply_msg),
                        sender_ip,
                        port,
                        is_broadcast=False
                    )

            elif msg_type == TYPE_GOODBYE:
                if sender_ip in self.users:
                    self.users[sender_ip].mark_offline()
                    changed = True

        if changed and self.on_users_updated:
            self.on_users_updated(self.get_users_snapshot())

    def _run_heartbeat_loop(self):
        """Background loop executing heartbeats and timeout checks."""
        last_heartbeat = time.time()
        while self._is_running:
            time.sleep(1.0)
            now = time.time()

            # 1. Periodic Heartbeat Broadcast
            if now - last_heartbeat >= self.heartbeat_interval:
                self.broadcast_heartbeat()
                last_heartbeat = now

            # 2. Check for timed out offline users
            changed = False
            with self._lock:
                for ip, user in list(self.users.items()):
                    if not user.explicit_offline and not user.is_online(self.offline_timeout):
                        user.mark_offline()
                        changed = True

            if changed and self.on_users_updated:
                self.on_users_updated(self.get_users_snapshot())

    def get_users_snapshot(self) -> Dict[str, User]:
        """Returns a thread-safe shallow copy of current user dictionary."""
        with self._lock:
            return dict(self.users)
