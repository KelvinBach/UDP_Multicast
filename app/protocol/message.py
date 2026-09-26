"""
Network Protocol Message Definitions and Helpers.
Uses standard JSON over UDP payload.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any

# Protocol Message Types
TYPE_DISCOVERY = "DISCOVERY"
TYPE_HEARTBEAT = "HEARTBEAT"
TYPE_CHAT = "CHAT"
TYPE_GOODBYE = "GOODBYE"

# Chat Modes
MODE_UNICAST = "UNICAST"
MODE_BROADCAST = "BROADCAST"


def get_current_timestamp() -> str:
    """Returns human-readable local time (e.g., '14:32')."""
    return datetime.now().strftime("%H:%M")


def create_discovery_message(username: str, ip: str, port: int) -> Dict[str, Any]:
    """
    Creates a DISCOVERY message packet.
    Broadcast when client joins LAN or as periodic heartbeat.
    """
    return {
        "type": TYPE_DISCOVERY,
        "sender": username,
        "sender_ip": ip,
        "port": port,
        "timestamp": get_current_timestamp(),
    }


def create_heartbeat_message(username: str, ip: str, port: int) -> Dict[str, Any]:
    """Creates a lightweight HEARTBEAT message packet."""
    return {
        "type": TYPE_HEARTBEAT,
        "sender": username,
        "sender_ip": ip,
        "port": port,
        "timestamp": get_current_timestamp(),
    }


def create_chat_message(
    username: str,
    sender_ip: str,
    message: str,
    mode: str = MODE_UNICAST,
    target_ip: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a CHAT message packet.
    mode can be 'UNICAST' or 'BROADCAST'.
    """
    payload = {
        "type": TYPE_CHAT,
        "mode": mode,
        "sender": username,
        "sender_ip": sender_ip,
        "message": message,
        "timestamp": get_current_timestamp(),
    }
    if target_ip:
        payload["target_ip"] = target_ip
    return payload


def create_goodbye_message(username: str, ip: str) -> Dict[str, Any]:
    """Creates a GOODBYE packet broadcast when closing the app."""
    return {
        "type": TYPE_GOODBYE,
        "sender": username,
        "sender_ip": ip,
        "timestamp": get_current_timestamp(),
    }


def encode_message(data: Dict[str, Any]) -> bytes:
    """Serializes message dict to UTF-8 encoded JSON bytes."""
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def decode_message(raw_bytes: bytes) -> Optional[Dict[str, Any]]:
    """
    Deserializes raw UDP packet bytes into message dictionary.
    Returns None if decoding fails or JSON is malformed.
    """
    try:
        text = raw_bytes.decode("utf-8", errors="replace")
        data = json.loads(text)
        if isinstance(data, dict) and "type" in data:
            return data
    except Exception:
        pass
    return None
