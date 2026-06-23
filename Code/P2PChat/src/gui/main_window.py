import customtkinter as ctk
import threading
import time
from transfer_panel import TransferPanel
from sidebar import Sidebar
from statusbar import StatusBar
from trust_dialog import TrustDialog

# Set up standard dark mode interface
ctk.set_appearance_mode("dark")

class ChatApp(ctk.CTk):
    def __init__(self, listen_port=5000):
        super().__init__()
        self.title("💬 P2P Chat v2.0")
        self.geometry("900x650")
        self.minsize(700, 500)
        self.listen_port = listen_port 
        self.trusted_peers = {}
        self.chat_history = {}

        # --- Set up Responsive Grid ---
        # Column 0 (Chat) will expand (weight=1), Column 1 (Sidebar) stays fixed (weight=0)
        self.grid_columnconfigure(0, weight=1)  
        self.grid_columnconfigure(1, weight=0)  
        self.grid_rowconfigure(0, weight=1)     #_rows will expand
        self.grid_rowconfigure(1, weight=0)     # Status bar row stays fixed

        self._build_ui()

    def _build_ui(self):
        # ================= LEFT AREA (MAIN CHAT) =================
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1e1e2e")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1) # Chat box expands automatically

        # 1. Connection bar (UX Non-tech: Hides IP/Port)
        self.top_bar = ctk.CTkFrame(self.main_frame, height=50, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

        self.nick_entry = ctk.CTkEntry(self.top_bar, placeholder_text="Enter nickname...", width=150, font=("Consolas", 12))
        self.nick_entry.pack(side="left", padx=(0, 10))

        self.connect_btn = ctk.CTkButton(
            self.top_bar, text="🔗 Start Chat", 
            font=("Consolas", 12, "bold"), fg_color="#89b4fa", text_color="#11111b",
            command=self._start_connect_thread # Call the function to start connection in a new thread
        )
        self.connect_btn.pack(side="left")

        # 2. Chat box (Disabled until conected)
        self.chat_box = ctk.CTkTextbox(
            self.main_frame, state="disabled", wrap="word", 
            font=("Consolas", 13), fg_color="#181825", text_color="#cdd6f4"
        )
        self.chat_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # 3. Message input area (Disabled by default)
        self.input_frame = ctk.CTkFrame(self.main_frame, height=50, fg_color="transparent")
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.msg_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Enter message...", state="disabled", font=("Consolas", 13))
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.send_btn = ctk.CTkButton(
            self.input_frame, text="▶ Send", width=80, state="disabled",
            font=("Consolas", 12, "bold"), fg_color="#a6e3a1", text_color="#11111b"
        )
        self.send_btn.pack(side="left")

        # ================= LEFT AREA (SIDEBAR) =================
        self.sidebar = Sidebar(self)
        self.sidebar.grid(row=0, column=1, sticky="ns")
        self.transfer_panel = TransferPanel(master=self.sidebar,  controller=self)
        self.transfer_panel.pack(fill="both", expand=True, padx=5, pady=10)

        # ================= BOTTOM AREA (STATUS BAR) =================
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

    # ================= Logic (preventing GUI freeze)=================
    def _start_connect_thread(self):
        """Start a separate network thread to avoid freezing the interface."""
        # Lock the button to prevent multiple clicks.
        self.connect_btn.configure(state="disabled")
        self.status_bar.set_status("⏳ Setting up P2P network...", "#f9e2af")
        
        # Move the network waiting process to a different thread.
        threading.Thread(target=self._network_connect_task, daemon=True).start()

    def _network_connect_task(self):
        """Simulating socket handling functions (Running in the background)"""
        # TODO: Place the actual socket.bind() or socket.connect() code here.
        time.sleep(1.5) # Simulate 1.5s delay to open port
        
        # After the network is ready, request the main thread to update the UI
        self.after(0, self._on_connected)

    def _on_connected(self):
        """Update UI after the network is ready"""
        self.status_bar.set_status("✅ Ready to send and receive messages", "#a6e3a1")
        
        # Change the connect button to a disconnect button
        self.connect_btn.configure(
            text="✂️ Disconnect", state="normal", 
            fg_color="#f38ba8", hover_color="#d76f8c"
        )
        
        # Unlock message input field (clear UX)
        self.msg_entry.configure(state="normal")
        self.send_btn.configure(state="normal")

    # Network event handlers
    def on_peer_discovered(self, peer_info):
        """When another machine is found: Check for TOFU security."""
        peer_id = peer_info.get("peer_id")
        new_fp = peer_info.get("fingerprint")
        if peer_id not in self.trusted_peers:
            TrustDialog(self, mode="new_peer", peer_info=peer_info, 
                        callback=lambda res: self._handle_trust(res, peer_info))
        elif self.trusted_peers[peer_id] != new_fp:
            peer_info["known_fingerprint"] = self.trusted_peers[peer_id]
            peer_info["current_fingerprint"] = new_fp
            TrustDialog(self, mode="warning", peer_info=peer_info,
                        callback=lambda res: self._handle_trust(res, peer_info))

    def _handle_trust(self, action, peer_info):
        if action in ["trust", "update"]:
            self.trusted_peers[peer_info["peer_id"]] = peer_info["fingerprint"]
            self.sidebar.update_peers([peer_info["username"]])

    def on_message_received(self, peer_id, username, message):
        """When a message is received: Save to history and display on screen"""
        msg = f"[{time.strftime('%H:%M')}] {username}: {message}"
        if peer_id not in self.chat_history: self.chat_history[peer_id] = []
        self.chat_history[peer_id].append(msg)
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", msg + "\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def on_transfer_progress(self, tid, progress):
        self.transfer_panel.update_transfer(tid, progress)

    def on_transfer_started(self, tid, filename, peer, direction):
        self.transfer_panel.add_transfer(tid, filename, peer, direction)

    def on_transfer_complete(self, tid):
        self.transfer_panel.remove_transfer(tid)

    def send_file(self, path):
        """Function that runs when you click the 'Send File' button"""
        print(f"Sending file: {path}")

    def cancel_transfer(self, tid):
        """Function that runs when you click the 'Cancel' button"""
        print(f"Transfer canceled: {tid}")
        self.on_transfer_complete(tid)
    

        # Simulate loading a list of peers to display in the sidebar.
        self.sidebar.update_peers(["James", "Alice"])

if __name__ == "__main__":
    app = ChatApp(listen_port=5000)
    app.mainloop()