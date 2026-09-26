"""
User Model representing discovered LAN peers.
"""

import time
from dataclasses import dataclass, field


@dataclass
class User:
    username: str
    ip: str
    port: int = 5000
    last_seen: float = field(default_factory=time.time)
    explicit_offline: bool = False

    def is_online(self, timeout_seconds: float = 15.0) -> bool:
        """Determines online status based on time elapsed since last heartbeat."""
        if self.explicit_offline:
            return False
        return (time.time() - self.last_seen) <= timeout_seconds

    def update_seen(self, username: str = None, port: int = None):
        """Refreshes last seen timestamp and attributes."""
        self.last_seen = time.time()
        self.explicit_offline = False
        if username:
            self.username = username
        if port:
            self.port = port

    def mark_offline(self):
        """Marks user as explicitly logged out or offline."""
        self.explicit_offline = True
