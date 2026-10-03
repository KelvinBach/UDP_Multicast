"""
UDP Socket Manager for LAN Messenger.
Direct UDP sockets handling Unicast and Broadcast sending and receiving.
"""

import socket
import threading
import platform
from typing import Callable, Optional, Tuple


class UdpSocketManager:
    def __init__(self, port: int = 5000, on_receive_callback: Optional[Callable[[bytes, Tuple[str, int]], None]] = None):
        self.port = port
        self.on_receive_callback = on_receive_callback
        self.socket: Optional[socket.socket] = None
        self._is_running = False
        self._receive_thread: Optional[threading.Thread] = None

    def start(self) -> Tuple[bool, Optional[str]]:
        """
        Binds UDP socket to the configured port and starts background listening thread.
        Returns (success, error_message).
        """
        self.stop()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Allow socket reuse
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Enable UDP broadcast permission
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Fix Windows WSAECONNRESET (10054) error when remote UDP port is unreachable
            if platform.system() == "Windows":
                try:
                    SIO_UDP_CONNRESET = 0x9800000C
                    self.socket.ioctl(SIO_UDP_CONNRESET, False)
                except Exception:
                    pass

            # Bind to all interfaces to listen for both Unicast and Broadcast packets
            self.socket.bind(("", self.port))
            
            self._is_running = True
            self._receive_thread = threading.Thread(
                target=self._listen_loop,
                name="udp-listener-thread",
                daemon=True
            )
            self._receive_thread.start()
            return True, None
        except OSError as e:
            self.stop()
            # Friendly error handling for port collisions
            if hasattr(e, "winerror") and e.winerror == 10048:
                return False, f"UDP port {self.port} is already in use."
            elif e.errno in (48, 98):  # EADDRINUSE on Unix
                return False, f"UDP port {self.port} is already in use."
            return False, f"Failed to bind UDP port {self.port}: {e.strerror or str(e)}"
        except Exception as e:
            self.stop()
            return False, f"Unexpected network error: {str(e)}"

    def _listen_loop(self):
        """Continuously receives incoming UDP packets and dispatches to callback."""
        while self._is_running and self.socket:
            try:
                # Buffer size 65535 (maximum possible UDP payload length)
                data, addr = self.socket.recvfrom(65535)
                if not data:
                    continue
                if self.on_receive_callback:
                    self.on_receive_callback(data, addr)
            except OSError:
                # Socket was closed or encountered network interruption
                break
            except Exception:
                if not self._is_running:
                    break

    def send(self, data: bytes, target_ip: str, target_port: int, is_broadcast: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Sends raw bytes to target IP and port using UDP.
        Uses the internal socket or creates an ephemeral sender socket.
        """
        try:
            # We can use our bound socket or an ephemeral socket for sending
            sock = self.socket
            created_temp = False
            if not sock or not self._is_running:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                created_temp = True

            if is_broadcast:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Core networking call: UDP sendto
            sock.sendto(data, (target_ip, target_port))

            if created_temp:
                sock.close()

            return True, None
        except socket.gaierror:
            return False, f"Invalid destination address: {target_ip}"
        except OSError as e:
            return False, f"Network transmission error: {e.strerror or str(e)}"
        except Exception as e:
            return False, f"Failed to send: {str(e)}"

    def stop(self):
        """Closes the socket and stops the background listener."""
        self._is_running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        if self._receive_thread and self._receive_thread.is_alive():
            # Thread will terminate because socket is closed and _is_running is False
            pass
        self._receive_thread = None

    @property
    def is_running(self) -> bool:
        return self._is_running
