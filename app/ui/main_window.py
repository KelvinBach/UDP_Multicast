"""
Main Application Window for LAN Messenger.
Implements the Messenger/Zalo sidebar layout, conversation manager,
and integrates UDP networking, discovery, and chat dispatching.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional

from app.config import load_config, save_config
from app.models.user import User
from app.models.chat import Conversation, ChatMessage
from app.network.interface import detect_network, NetworkInfo
from app.network.udp import UdpSocketManager
from app.network.discovery import DiscoveryService
from app.network.broadcast import BroadcastService
from app.protocol.message import (
    TYPE_CHAT,
    MODE_BROADCAST,
    MODE_UNICAST,
    create_chat_message,
    encode_message,
    decode_message,
    get_current_timestamp,
)
from app.ui.chat_view import ChatView
from app.ui.settings import SettingsDialog, FirstLaunchDialog


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LAN Messenger")
        self.geometry("960x650")
        self.minsize(800, 520)

        # 1. State and Config
        self.config = load_config()
        self.network_info: NetworkInfo = detect_network(self.config.get("interface", "Auto"))

        self.conversations: Dict[str, Conversation] = {}
        self.active_conv_id: Optional[str] = None
        self.online_users: Dict[str, User] = {}

        # 2. Services
        self.udp_manager: Optional[UdpSocketManager] = None
        self.discovery_service: Optional[DiscoveryService] = None
        self.broadcast_service: Optional[BroadcastService] = None

        # 3. Setup UI
        self._setup_styles()
        self._build_layout()

        # 4. Initialize Default "Everyone" Broadcast Conversation
        self._init_broadcast_conversation()

        # 5. Handle First Launch (Username Prompt)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._check_first_launch)

    def _setup_styles(self):
        self.configure(bg="#F0F2F5")
        style = ttk.Style(self)
        style.theme_use("clam")

    def _build_layout(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ====================================================
        # LEFT SIDEBAR
        # ====================================================
        self.sidebar = tk.Frame(self, bg="#F0F2F5", width=280, highlightthickness=1, highlightbackground="#E5E7EB")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # 1. Sidebar Header (App Title & Connection Status)
        header_frame = tk.Frame(self.sidebar, bg="#F0F2F5", padx=16, pady=12)
        header_frame.pack(fill="x")

        tk.Label(
            header_frame,
            text="LAN MESSENGER",
            font=("Segoe UI", 11, "bold"),
            fg="#1F2937",
            bg="#F0F2F5"
        ).pack(anchor="w")

        self.status_badge = tk.Label(
            header_frame,
            text=self.network_info.status_text,
            font=("Segoe UI", 8),
            fg="#16A34A" if self.network_info.is_connected else "#DC2626",
            bg="#F0F2F5"
        )
        self.status_badge.pack(anchor="w", pady=(2, 0))

        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=12, pady=4)

        # 2. MY PROFILE
        profile_frame = tk.Frame(self.sidebar, bg="#F0F2F5", padx=16, pady=8)
        profile_frame.pack(fill="x")

        tk.Label(
            profile_frame,
            text="MY PROFILE",
            font=("Segoe UI", 8, "bold"),
            fg="#6B7280",
            bg="#F0F2F5"
        ).pack(anchor="w")

        self.profile_name_label = tk.Label(
            profile_frame,
            text=self.config.get("username") or "Unnamed User",
            font=("Segoe UI", 11, "bold"),
            fg="#111827",
            bg="#F0F2F5"
        )
        self.profile_name_label.pack(anchor="w", pady=(2, 0))

        self.profile_ip_label = tk.Label(
            profile_frame,
            text=f"{self.network_info.ip_address}:{self.config.get('port', 5000)}",
            font=("Segoe UI", 9),
            fg="#4B5563",
            bg="#F0F2F5"
        )
        self.profile_ip_label.pack(anchor="w")

        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=12, pady=6)

        # 3. Scrollable Middle Section (CHATS & ONLINE)
        scroll_container = tk.Frame(self.sidebar, bg="#F0F2F5")
        scroll_container.pack(fill="both", expand=True)

        self.sidebar_canvas = tk.Canvas(scroll_container, bg="#F0F2F5", highlightthickness=0)
        self.sidebar_scroll = ttk.Scrollbar(scroll_container, orient="vertical", command=self.sidebar_canvas.yview)

        self.sidebar_content = tk.Frame(self.sidebar_canvas, bg="#F0F2F5", padx=8)
        self.sidebar_content.bind(
            "<Configure>",
            lambda e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))
        )

        self.sidebar_window = self.sidebar_canvas.create_window((0, 0), window=self.sidebar_content, anchor="nw")
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scroll.set)

        self.sidebar_canvas.pack(side="left", fill="both", expand=True)
        self.sidebar_scroll.pack(side="right", fill="y")

        self.sidebar_canvas.bind(
            "<Configure>",
            lambda e: self.sidebar_canvas.itemconfig(self.sidebar_window, width=e.width)
        )

        # Section: CHATS
        tk.Label(
            self.sidebar_content,
            text="CHATS",
            font=("Segoe UI", 8, "bold"),
            fg="#6B7280",
            bg="#F0F2F5"
        ).pack(anchor="w", padx=8, pady=(8, 4))

        self.chats_frame = tk.Frame(self.sidebar_content, bg="#F0F2F5")
        self.chats_frame.pack(fill="x")

        # Section: ONLINE
        self.online_header_label = tk.Label(
            self.sidebar_content,
            text="ONLINE",
            font=("Segoe UI", 8, "bold"),
            fg="#6B7280",
            bg="#F0F2F5"
        )
        self.online_header_label.pack(anchor="w", padx=8, pady=(16, 4))

        self.online_users_frame = tk.Frame(self.sidebar_content, bg="#F0F2F5")
        self.online_users_frame.pack(fill="x")

        # 4. Sidebar Bottom (Settings & Network Info Buttons)
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=12, pady=4)
        bottom_bar = tk.Frame(self.sidebar, bg="#F0F2F5", padx=12, pady=10)
        bottom_bar.pack(fill="x")

        btn_settings = tk.Button(
            bottom_bar,
            text="⚙ Settings",
            font=("Segoe UI", 9),
            bg="#E5E7EB",
            fg="#374151",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._open_settings
        )
        btn_settings.pack(side="left")

        btn_net_info = tk.Button(
            bottom_bar,
            text="ℹ Network",
            font=("Segoe UI", 9),
            bg="#E5E7EB",
            fg="#374151",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._show_network_info_dialog
        )
        btn_net_info.pack(side="right")

        # ====================================================
        # RIGHT PANEL: CHAT VIEW
        # ====================================================
        self.chat_view = ChatView(self, on_send_callback=self._handle_send_message)
        self.chat_view.grid(row=0, column=1, sticky="nsew")

    def _check_first_launch(self):
        """Prompts user for username if not yet configured, otherwise boots networking."""
        username = self.config.get("username", "").strip()
        if not username:
            FirstLaunchDialog(self, on_submit_callback=self._on_first_username_submitted)
        else:
            self._start_networking()

    def _on_first_username_submitted(self, username: str):
        self.config["username"] = username
        save_config(self.config)
        self.profile_name_label.config(text=username)
        self._start_networking()

    def _start_networking(self):
        """Initializes and starts UDP manager, broadcast service, and discovery service."""
        # Stop existing services if running
        if self.discovery_service:
            self.discovery_service.stop()
        if self.udp_manager:
            self.udp_manager.stop()

        # Refresh network interface information
        self.network_info = detect_network(self.config.get("interface", "Auto"))
        self._refresh_network_ui()

        port = int(self.config.get("port", 5000))
        username = self.config.get("username", "User")

        # Create UDP Manager
        self.udp_manager = UdpSocketManager(
            port=port,
            on_receive_callback=self._handle_incoming_packet
        )

        success, err = self.udp_manager.start()
        if not success:
            messagebox.showerror(
                "Network Error",
                f"{err}\nPlease choose another port in Settings.",
                parent=self
            )
            return

        # Broadcast service
        self.broadcast_service = BroadcastService(self.udp_manager)

        # Discovery service
        self.discovery_service = DiscoveryService(
            udp_manager=self.udp_manager,
            username=username,
            local_ip=self.network_info.ip_address,
            broadcast_ip=self.network_info.broadcast_address,
            port=port,
            on_users_updated=lambda users: self.after(0, self._on_users_updated, users)
        )
        self.discovery_service.start()

    def _refresh_network_ui(self):
        """Updates UI elements that depend on IP or network connection."""
        self.status_badge.config(
            text=self.network_info.status_text,
            fg="#16A34A" if self.network_info.is_connected else "#DC2626"
        )
        self.profile_name_label.config(text=self.config.get("username") or "Unnamed User")
        self.profile_ip_label.config(text=f"{self.network_info.ip_address}:{self.config.get('port', 5000)}")

        # Update broadcast conversation destination
        if "BROADCAST" in self.conversations:
            b_conv = self.conversations["BROADCAST"]
            b_conv.target_ip = self.network_info.broadcast_address
            b_conv.target_port = int(self.config.get("port", 5000))
            if self.active_conv_id == "BROADCAST":
                self.chat_view.set_conversation(b_conv)

    def _init_broadcast_conversation(self):
        """Initializes the default 'Everyone' broadcast chat."""
        conv = Conversation(
            id="BROADCAST",
            title="Everyone",
            mode=MODE_BROADCAST,
            target_ip=self.network_info.broadcast_address,
            target_port=int(self.config.get("port", 5000))
        )
        self.conversations["BROADCAST"] = conv
        self.select_conversation("BROADCAST")
        self._render_chats_list()

    def select_conversation(self, conv_id: str):
        """Switches active conversation displayed in ChatView."""
        if conv_id not in self.conversations:
            return
        self.active_conv_id = conv_id
        conv = self.conversations[conv_id]
        conv.mark_read()
        self.chat_view.set_conversation(conv)
        self._render_chats_list()

    def _render_chats_list(self):
        """Renders the CHATS list in the sidebar."""
        for widget in self.chats_frame.winfo_children():
            widget.destroy()

        for cid, conv in self.conversations.items():
            is_active = (cid == self.active_conv_id)
            bg_color = "#E4E6EB" if is_active else "#F0F2F5"

            btn_frame = tk.Frame(self.chats_frame, bg=bg_color, padx=10, pady=6, cursor="hand2")
            btn_frame.pack(fill="x", pady=1)

            # Sub-widgets click handler
            def make_click_handler(conv_id=cid):
                return lambda e: self.select_conversation(conv_id)

            btn_frame.bind("<Button-1>", make_click_handler())

            title_text = conv.title
            if conv.unread_count > 0:
                title_text += f" ({conv.unread_count})"

            lbl_title = tk.Label(
                btn_frame,
                text=title_text,
                font=("Segoe UI", 9, "bold" if is_active or conv.unread_count > 0 else "normal"),
                fg="#111827",
                bg=bg_color,
                anchor="w"
            )
            lbl_title.pack(anchor="w")
            lbl_title.bind("<Button-1>", make_click_handler())

            subtitle_text = "Broadcast" if conv.mode == MODE_BROADCAST else "Unicast"
            lbl_sub = tk.Label(
                btn_frame,
                text=subtitle_text,
                font=("Segoe UI", 8),
                fg="#6B7280",
                bg=bg_color,
                anchor="w"
            )
            lbl_sub.pack(anchor="w")
            lbl_sub.bind("<Button-1>", make_click_handler())

    def _on_users_updated(self, users: Dict[str, User]):
        """Callback from DiscoveryService when online users change."""
        self.online_users = users
        self._render_online_users_list()

    def _render_online_users_list(self):
        """Renders the ONLINE users list in the sidebar."""
        for widget in self.online_users_frame.winfo_children():
            widget.destroy()

        online_count = sum(1 for u in self.online_users.values() if u.is_online())
        self.online_header_label.config(text=f"ONLINE ({online_count})")

        if not self.online_users:
            empty_lbl = tk.Label(
                self.online_users_frame,
                text="Scanning LAN...",
                font=("Segoe UI", 8, "italic"),
                fg="#9CA3AF",
                bg="#F0F2F5"
            )
            empty_lbl.pack(anchor="w", padx=8, pady=4)
            return

        # Sort: online users first, then alphabetically
        sorted_users = sorted(
            self.online_users.values(),
            key=lambda u: (not u.is_online(), u.username.lower())
        )

        for user in sorted_users:
            is_on = user.is_online()
            status_dot = "●" if is_on else "○"
            dot_color = "#16A34A" if is_on else "#9CA3AF"
            status_desc = user.ip if is_on else "Offline"

            item_frame = tk.Frame(self.online_users_frame, bg="#F0F2F5", padx=8, pady=4, cursor="hand2")
            item_frame.pack(fill="x", pady=1)

            def open_unicast_chat(target_user=user):
                return lambda e: self._open_or_create_unicast(target_user)

            item_frame.bind("<Button-1>", open_unicast_chat())

            # Top line: Dot + Name
            top_line = tk.Frame(item_frame, bg="#F0F2F5")
            top_line.pack(fill="x")
            top_line.bind("<Button-1>", open_unicast_chat())

            dot_lbl = tk.Label(top_line, text=status_dot, font=("Segoe UI", 9, "bold"), fg=dot_color, bg="#F0F2F5")
            dot_lbl.pack(side="left")
            dot_lbl.bind("<Button-1>", open_unicast_chat())

            name_lbl = tk.Label(top_line, text=f" {user.username}", font=("Segoe UI", 9, "bold"), fg="#111827", bg="#F0F2F5")
            name_lbl.pack(side="left")
            name_lbl.bind("<Button-1>", open_unicast_chat())

            # Bottom line: IP or Offline
            sub_lbl = tk.Label(item_frame, text=f"   {status_desc}", font=("Segoe UI", 8), fg="#6B7280", bg="#F0F2F5")
            sub_lbl.pack(anchor="w")
            sub_lbl.bind("<Button-1>", open_unicast_chat())

    def _open_or_create_unicast(self, user: User):
        """Opens existing unicast conversation with peer or creates a new one."""
        peer_ip = user.ip
        if peer_ip not in self.conversations:
            conv = Conversation(
                id=peer_ip,
                title=user.username,
                mode=MODE_UNICAST,
                target_ip=peer_ip,
                target_port=user.port
            )
            self.conversations[peer_ip] = conv
        else:
            # Update title in case username changed
            self.conversations[peer_ip].title = user.username
            self.conversations[peer_ip].target_port = user.port

        self.select_conversation(peer_ip)

    def _handle_send_message(self, text: str):
        """Sends chat message to the active conversation destination."""
        if not self.active_conv_id or self.active_conv_id not in self.conversations:
            return

        conv = self.conversations[self.active_conv_id]
        username = self.config.get("username", "User")
        sender_ip = self.network_info.ip_address
        timestamp = get_current_timestamp()

        # Build ChatMessage model
        local_msg = ChatMessage(
            sender=username,
            sender_ip=sender_ip,
            message=text,
            timestamp=timestamp,
            mode=conv.mode,
            is_self=True
        )

        if conv.mode == MODE_BROADCAST:
            # Broadcast send
            success, err = self.broadcast_service.send_broadcast_message(
                username=username,
                sender_ip=sender_ip,
                broadcast_ip=self.network_info.broadcast_address,
                port=int(self.config.get("port", 5000)),
                message=text
            )
            if not success:
                messagebox.showerror("Send Error", f"Broadcast failed: {err}", parent=self)
                return
        else:
            # Unicast send
            # Check if user is still online or warning
            peer = self.online_users.get(conv.target_ip)
            if peer and not peer.is_online():
                messagebox.showwarning(
                    "Notice",
                    "User is no longer available or offline.",
                    parent=self
                )

            packet = create_chat_message(
                username=username,
                sender_ip=sender_ip,
                message=text,
                mode=MODE_UNICAST,
                target_ip=conv.target_ip
            )
            data = encode_message(packet)
            success, err = self.udp_manager.send(data, conv.target_ip, conv.target_port, is_broadcast=False)
            if not success:
                messagebox.showerror("Send Error", f"Unicast failed: {err}", parent=self)
                return

        # Add message to active conversation history
        conv.add_message(local_msg, is_active_view=True)
        self.chat_view.add_message(local_msg)
        self._render_chats_list()

    def _handle_incoming_packet(self, data: bytes, sender_addr: tuple):
        """Directs raw UDP packets to appropriate handlers on the UI thread."""
        packet = decode_message(data)
        if not packet:
            return

        msg_type = packet.get("type")
        if msg_type in ("DISCOVERY", "HEARTBEAT", "GOODBYE"):
            if self.discovery_service:
                self.discovery_service.handle_packet(packet, sender_addr)
        elif msg_type == TYPE_CHAT:
            self.after(0, self._process_chat_packet, packet, sender_addr)

    def _process_chat_packet(self, packet: dict, sender_addr: tuple):
        """Processes an incoming chat packet and dispatches to conversation."""
        sender = packet.get("sender", "Unknown")
        sender_ip = packet.get("sender_ip") or sender_addr[0]
        message = packet.get("message", "")
        timestamp = packet.get("timestamp", get_current_timestamp())
        mode = packet.get("mode", MODE_UNICAST)

        # Ignore echo of our own broadcast packets
        if sender_ip == self.network_info.ip_address and sender == self.config.get("username"):
            return

        chat_msg = ChatMessage(
            sender=sender,
            sender_ip=sender_ip,
            message=message,
            timestamp=timestamp,
            mode=mode,
            is_self=False
        )

        if mode == MODE_BROADCAST:
            conv = self.conversations.get("BROADCAST")
            if conv:
                is_active = (self.active_conv_id == "BROADCAST")
                conv.add_message(chat_msg, is_active_view=is_active)
                if is_active:
                    self.chat_view.add_message(chat_msg)
                self._render_chats_list()
        else:
            # Unicast packet
            # Check or create conversation with sender_ip
            if sender_ip not in self.conversations:
                conv = Conversation(
                    id=sender_ip,
                    title=sender,
                    mode=MODE_UNICAST,
                    target_ip=sender_ip,
                    target_port=sender_addr[1]
                )
                self.conversations[sender_ip] = conv
            else:
                conv = self.conversations[sender_ip]
                conv.title = sender  # update display name if changed

            is_active = (self.active_conv_id == sender_ip)
            conv.add_message(chat_msg, is_active_view=is_active)
            if is_active:
                self.chat_view.add_message(chat_msg)
            self._render_chats_list()

    def _open_settings(self):
        """Opens Settings dialog."""
        SettingsDialog(
            self,
            current_config=self.config,
            network_info=self.network_info,
            on_save_callback=self._on_settings_saved
        )

    def _on_settings_saved(self, new_config: dict):
        """Applies updated settings and restarts networking."""
        self.config.update(new_config)
        save_config(self.config)
        self.profile_name_label.config(text=self.config.get("username"))
        self._start_networking()

    def _show_network_info_dialog(self):
        """Displays full Network Information modal."""
        top = tk.Toplevel(self)
        top.title("Network Information")
        top.geometry("400x340")
        top.resizable(False, False)
        top.transient(self)
        top.grab_set()

        top.configure(bg="#F9FAFB")
        box = tk.Frame(top, bg="#F9FAFB", padx=20, pady=20)
        box.pack(fill="both", expand=True)

        tk.Label(
            box,
            text="LAN Network Details",
            font=("Segoe UI", 12, "bold"),
            bg="#F9FAFB",
            fg="#111827"
        ).pack(anchor="w", pady=(0, 14))

        info_dict = self.network_info.to_display_dict()
        for k, v in info_dict.items():
            row = tk.Frame(box, bg="#F9FAFB")
            row.pack(fill="x", pady=2)
            tk.Label(
                row,
                text=k,
                width=16,
                anchor="w",
                font=("Segoe UI", 9),
                bg="#F9FAFB",
                fg="#6B7280"
            ).pack(side="left")
            tk.Label(
                row,
                text=v,
                anchor="w",
                font=("Segoe UI", 9, "bold"),
                bg="#F9FAFB",
                fg="#16A34A" if k == "Status" and self.network_info.is_connected else "#111827"
            ).pack(side="left", fill="x", expand=True)

        btn = tk.Button(
            box,
            text="Close",
            font=("Segoe UI", 9),
            bg="#E5E7EB",
            fg="#374151",
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
            command=top.destroy
        )
        btn.pack(side="bottom", pady=(14, 0))

    def _on_close(self):
        """Gracefully shuts down discovery, UDP sockets, and closes app."""
        if self.discovery_service:
            try:
                self.discovery_service.stop()
            except Exception:
                pass
        if self.udp_manager:
            try:
                self.udp_manager.stop()
            except Exception:
                pass
        self.destroy()
