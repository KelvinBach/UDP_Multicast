"""
Settings and Network Information Dialogs.
Allows configuring Username, UDP Port, and Network Interface selection.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Any, List
from app.network.interface import NetworkInfo, get_all_interfaces


class SettingsDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        current_config: Dict[str, Any],
        network_info: NetworkInfo,
        on_save_callback: Callable[[Dict[str, Any]], None]
    ):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("420x460")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.current_config = current_config
        self.network_info = network_info
        self.on_save_callback = on_save_callback

        self._build_ui()
        self.center_window(parent)

    def center_window(self, parent):
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _build_ui(self):
        self.configure(bg="#F9FAFB")
        container = tk.Frame(self, bg="#F9FAFB", padx=20, pady=20)
        container.pack(fill="both", expand=True)

        # Title
        title_lbl = tk.Label(
            container,
            text="Settings",
            font=("Segoe UI", 14, "bold"),
            bg="#F9FAFB",
            fg="#111827"
        )
        title_lbl.pack(anchor="w", pady=(0, 16))

        # 1. Username
        tk.Label(
            container,
            text="Username",
            font=("Segoe UI", 9, "bold"),
            bg="#F9FAFB",
            fg="#374151"
        ).pack(anchor="w", pady=(4, 2))

        self.username_var = tk.StringVar(value=self.current_config.get("username", ""))
        self.username_entry = ttk.Entry(container, textvariable=self.username_var, font=("Segoe UI", 10))
        self.username_entry.pack(fill="x", pady=(0, 12))

        # 2. Network Interface Selection
        tk.Label(
            container,
            text="Network Interface",
            font=("Segoe UI", 9, "bold"),
            bg="#F9FAFB",
            fg="#374151"
        ).pack(anchor="w", pady=(4, 2))

        iface_options = ["Auto"]
        for iface in get_all_interfaces():
            iface_options.append(iface["name"])

        # Deduplicate while preserving order
        seen = set()
        deduped_ifaces = []
        for opt in iface_options:
            if opt not in seen:
                seen.add(opt)
                deduped_ifaces.append(opt)

        self.iface_var = tk.StringVar(value=self.current_config.get("interface", "Auto"))
        self.iface_combo = ttk.Combobox(
            container,
            textvariable=self.iface_var,
            values=deduped_ifaces,
            state="readonly",
            font=("Segoe UI", 10)
        )
        self.iface_combo.pack(fill="x", pady=(0, 12))

        # 3. UDP Port
        tk.Label(
            container,
            text="UDP Port",
            font=("Segoe UI", 9, "bold"),
            bg="#F9FAFB",
            fg="#374151"
        ).pack(anchor="w", pady=(4, 2))

        self.port_var = tk.StringVar(value=str(self.current_config.get("port", 5000)))
        self.port_entry = ttk.Entry(container, textvariable=self.port_var, font=("Segoe UI", 10))
        self.port_entry.pack(fill="x", pady=(0, 16))

        # 4. Active Network Info Preview Box
        info_frame = tk.LabelFrame(
            container,
            text="Current Network Status",
            font=("Segoe UI", 9, "bold"),
            bg="#F9FAFB",
            fg="#4B5563",
            padx=12,
            pady=8
        )
        info_frame.pack(fill="x", pady=(0, 20))

        net_dict = self.network_info.to_display_dict()
        for k, v in net_dict.items():
            row = tk.Frame(info_frame, bg="#F9FAFB")
            row.pack(fill="x", pady=1)
            tk.Label(
                row,
                text=k,
                width=14,
                anchor="w",
                font=("Segoe UI", 8),
                bg="#F9FAFB",
                fg="#6B7280"
            ).pack(side="left")
            tk.Label(
                row,
                text=v,
                anchor="w",
                font=("Segoe UI", 8, "bold" if k in ("IP Address", "Broadcast") else "normal"),
                bg="#F9FAFB",
                fg="#111827" if k != "Status" else ("#16A34A" if self.network_info.is_connected else "#DC2626")
            ).pack(side="left", fill="x", expand=True)

        # Buttons
        btn_frame = tk.Frame(container, bg="#F9FAFB")
        btn_frame.pack(fill="x", side="bottom")

        save_btn = tk.Button(
            btn_frame,
            text="Save Settings",
            font=("Segoe UI", 10, "bold"),
            bg="#0084FF",
            fg="#FFFFFF",
            activebackground="#0066CC",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._handle_save
        )
        save_btn.pack(side="right", padx=(8, 0))

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            font=("Segoe UI", 10),
            bg="#E5E7EB",
            fg="#374151",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.destroy
        )
        cancel_btn.pack(side="right")

    def _handle_save(self):
        username = self.username_var.get().strip()
        if not username:
            messagebox.showerror("Validation Error", "Username cannot be empty.", parent=self)
            return

        port_str = self.port_var.get().strip()
        try:
            port = int(port_str)
            if port < 1024 or port > 65535:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "UDP Port must be a number between 1024 and 65535.", parent=self)
            return

        new_config = {
            "username": username,
            "port": port,
            "interface": self.iface_var.get().strip()
        }

        self.on_save_callback(new_config)
        self.destroy()


class FirstLaunchDialog(tk.Toplevel):
    """Modal prompt on initial launch asking user to choose a username."""
    def __init__(self, parent, on_submit_callback: Callable[[str], None]):
        super().__init__(parent)
        self.title("Welcome to LAN Messenger")
        self.geometry("380x230")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.on_submit_callback = on_submit_callback
        self.result_username = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        self.configure(bg="#F9FAFB")
        box = tk.Frame(self, bg="#F9FAFB", padx=24, pady=20)
        box.pack(fill="both", expand=True)

        tk.Label(
            box,
            text="Welcome to LAN Messenger",
            font=("Segoe UI", 13, "bold"),
            bg="#F9FAFB",
            fg="#111827"
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            box,
            text="Please enter a username to identify yourself on the LAN.",
            font=("Segoe UI", 9),
            bg="#F9FAFB",
            fg="#6B7280",
            wraplength=330,
            justify="left"
        ).pack(anchor="w", pady=(0, 14))

        tk.Label(
            box,
            text="Username:",
            font=("Segoe UI", 9, "bold"),
            bg="#F9FAFB",
            fg="#374151"
        ).pack(anchor="w", pady=(0, 4))

        self.username_var = tk.StringVar()
        self.entry = ttk.Entry(box, textvariable=self.username_var, font=("Segoe UI", 11))
        self.entry.pack(fill="x", pady=(0, 18))
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self._submit())

        btn = tk.Button(
            box,
            text="Get Started",
            font=("Segoe UI", 10, "bold"),
            bg="#0084FF",
            fg="#FFFFFF",
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self._submit
        )
        btn.pack(fill="x")

    def _submit(self):
        name = self.username_var.get().strip()
        if not name:
            messagebox.showwarning("Notice", "Please enter a valid username.", parent=self)
            return
        self.result_username = name
        self.on_submit_callback(name)
        self.destroy()

    def _on_close(self):
        name = self.username_var.get().strip()
        if not name:
            # Default fallback if user closed modal
            name = "User_" + str(hash(self))[-4:]
        self.on_submit_callback(name)
        self.destroy()
