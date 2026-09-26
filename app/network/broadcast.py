"""
LAN Broadcast Messaging Service.
Handles sending chat messages to all peers on the subnet using UDP broadcast.
"""

from typing import Tuple, Optional
from app.network.udp import UdpSocketManager
from app.protocol.message import (
    create_chat_message,
    encode_message,
    MODE_BROADCAST,
)


class BroadcastService:
    def __init__(self, udp_manager: UdpSocketManager):
        self.udp_manager = udp_manager

    def send_broadcast_message(
        self,
        username: str,
        sender_ip: str,
        broadcast_ip: str,
        port: int,
        message: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Sends a broadcast chat message to the entire local subnet.
        Destination: (broadcast_ip, port).
        """
        if not broadcast_ip:
            return False, "Broadcast address could not be resolved."

        chat_packet = create_chat_message(
            username=username,
            sender_ip=sender_ip,
            message=message,
            mode=MODE_BROADCAST
        )
        data = encode_message(chat_packet)
        return self.udp_manager.send(data, broadcast_ip, port, is_broadcast=True)
