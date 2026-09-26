"""
Chat View Component.
Renders active conversation header, scrollable message history, and message input bar.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from app.models.chat import Conversation, ChatMessage


class ChatView(ttk.Frame):
    def __init__(self, parent, on_send_callback: Callable[[str], None], **kwargs):
        super().__init__(parent, **kwargs)
        self.on_send_callback = on_send_callback
        self.current_conversation: Optional[Conversation] = None

        self._build_ui()

    def _build_ui(self):
        # Configure layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Message history expands

        # ==========================================
        # 1. Chat Header
        # ==========================================
        self.header_frame = tk.Frame(self, bg="#FFFFFF", padx=16, pady=12, highlightthickness=1, highlightbackground="#E5E7EB")
        self.header_frame.grid(row=0, column=0, sticky="ew")

        self.title_label = tk.Label(
            self.header_frame,
            text="Select a conversation",
            font=("Segoe UI", 13, "bold"),
            bg="#FFFFFF",
            fg="#111827",
            anchor="w"
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = tk.Label(
            self.header_frame,
            text="",
            font=("Segoe UI", 9),
            bg="#FFFFFF",
            fg="#6B7280",
            anchor="w"
        )
        self.subtitle_label.pack(anchor="w")

        # ==========================================
        # 2. Messages Canvas (Scrollable)
        # ==========================================
        self.history_container = tk.Frame(self, bg="#F9FAFB")
        self.history_container.grid(row=1, column=0, sticky="nsew")
        self.history_container.columnconfigure(0, weight=1)
        self.history_container.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.history_container, bg="#F9FAFB", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.history_container, orient="vertical", command=self.canvas.yview)
        
        self.messages_frame = tk.Frame(self.canvas, bg="#F9FAFB", padx=16, pady=16)
        self.messages_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Handle canvas resize to keep frame width matched
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        # Mouse wheel support
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # ==========================================
        # 3. Input Bar
        # ==========================================
        self.input_frame = tk.Frame(self, bg="#FFFFFF", padx=14, pady=10, highlightthickness=1, highlightbackground="#E5E7EB")
        self.input_frame.grid(row=2, column=0, sticky="ew")
        self.input_frame.columnconfigure(0, weight=1)

        self.message_var = tk.StringVar()
        self.entry_message = tk.Entry(
            self.input_frame,
            textvariable=self.message_var,
            font=("Segoe UI", 10),
            relief="flat",
            bg="#F3F4F6",
            fg="#111827",
            insertbackground="#111827",
            highlightthickness=1,
            highlightbackground="#D1D5DB",
            highlightcolor="#2563EB",
        )
        self.entry_message.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 10))
        self.entry_message.bind("<Return>", self._handle_send_event)

        self.send_button = tk.Button(
            self.input_frame,
            text="Send",
            font=("Segoe UI", 10, "bold"),
            bg="#0084FF",
            fg="#FFFFFF",
            activebackground="#0066CC",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=16,
            pady=4,
            cursor="hand2",
            command=self._handle_send
        )
        self.send_button.grid(row=0, column=1)

    def _on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_conversation(self, conv: Optional[Conversation]):
        """Sets and renders the active conversation."""
        self.current_conversation = conv
        self._clear_messages_ui()

        if not conv:
            self.title_label.config(text="Select a conversation")
            self.subtitle_label.config(text="")
            self.entry_message.config(state="disabled")
            self.send_button.config(state="disabled")
            return

        self.entry_message.config(state="normal")
        self.send_button.config(state="normal")
        self.entry_message.focus_set()

        # Update Header
        self.title_label.config(text=conv.title)
        if conv.mode == "BROADCAST":
            self.subtitle_label.config(
                text=f"Broadcast · {conv.target_ip}:{conv.target_port}",
                fg="#2563EB"
            )
        else:
            self.subtitle_label.config(
                text=f"● {conv.target_ip}:{conv.target_port} · Unicast",
                fg="#16A34A"
            )

        # Render all past messages
        for msg in conv.messages:
            self._render_message_item(msg)

        self._scroll_to_bottom()

    def add_message(self, msg: ChatMessage):
        """Adds a new message to the active view."""
        self._render_message_item(msg)
        self._scroll_to_bottom()

    def _clear_messages_ui(self):
        for widget in self.messages_frame.winfo_children():
            widget.destroy()

    def _render_message_item(self, msg: ChatMessage):
        """Renders an individual message item according to user specification."""
        is_self = msg.is_self

        item_container = tk.Frame(self.messages_frame, bg="#F9FAFB", pady=4)
        item_container.pack(fill="x", expand=True)

        align = "e" if is_self else "w"
        sub_frame = tk.Frame(item_container, bg="#F9FAFB")
        sub_frame.pack(anchor=align)

        # Header: Name, IP, Timestamp
        # Example format:
        # MinhChien
        # 172.20.10.2 · 14:32
        header_text = f"{msg.sender}  ({msg.sender_ip} · {msg.timestamp})"
        meta_label = tk.Label(
            sub_frame,
            text=header_text,
            font=("Segoe UI", 8),
            fg="#6B7280",
            bg="#F9FAFB",
            anchor=align
        )
        meta_label.pack(anchor=align, padx=4, pady=(0, 2))

        # Bubble
        bubble_bg = "#0084FF" if is_self else "#E4E6EB"
        bubble_fg = "#FFFFFF" if is_self else "#050505"

        msg_body = tk.Label(
            sub_frame,
            text=msg.message,
            font=("Segoe UI", 10),
            bg=bubble_bg,
            fg=bubble_fg,
            padx=12,
            pady=8,
            wraplength=450,
            justify="left",
            relief="flat"
        )
        msg_body.pack(anchor=align)

    def _scroll_to_bottom(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _handle_send_event(self, event):
        self._handle_send()
        return "break"

    def _handle_send(self):
        text = self.message_var.get().strip()
        if text and self.on_send_callback:
            self.on_send_callback(text)
            self.message_var.set("")
