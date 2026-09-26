"""
Chat and Message Models.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ChatMessage:
    sender: str
    sender_ip: str
    message: str
    timestamp: str
    mode: str  # "UNICAST" or "BROADCAST"
    is_self: bool = False


@dataclass
class Conversation:
    id: str  # e.g., "BROADCAST" or peer IP "10.133.17.54"
    title: str  # e.g., "Everyone" or "An"
    mode: str  # "BROADCAST" or "UNICAST"
    target_ip: str  # Calculated broadcast address or peer IP
    target_port: int = 5000
    messages: List[ChatMessage] = field(default_factory=list)
    unread_count: int = 0

    def add_message(self, msg: ChatMessage, is_active_view: bool = False):
        self.messages.append(msg)
        if not is_active_view and not msg.is_self:
            self.unread_count += 1

    def mark_read(self):
        self.unread_count = 0
