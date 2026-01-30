"""
GUI Launcher for FreeQwenApi - Consolidates Node.js Proxy and Telegram Bot
into a single executable with dual log windows.
"""
import sys
import os
import subprocess
import threading
import queue
import signal
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox


class ServiceManager:
    """Manages Node.js and Python bot processes"""
    
    def __init__(self, log_callback_node, log_callback_telegram):
        self.node_process = None
        self.telegram_process = None
        self.log_callback_node = log_callback_node
        self.log_callback_telegram = log_callback_telegram
        self.running = False
        
        # Determine base path (works both in development and PyInstaller bundle)
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            self.base_path = Path(sys._MEIPASS)
        else:
            # Running in normal Python environment
            self.base_path = Path(__file__).parent.absolute()
    
    def start_services(self):
        """Start both Node.js and Telegram bot services"""
        if self.running:
            self.log_callback_node("⚠ Services are already running\n")
            return
        
        self.running = True
        
        # Start Node.js proxy first
        threading.Thread(target=self._start_node_service, daemon=True).start()
        
        # Wait a bit for Node.js to initialize, then start Telegram bot
        threading.Thread(target=self._delayed_telegram_start, daemon=True).start()
    
    def _delayed_telegram_start(self):
        """Start Telegram bot after a delay"""
        time.sleep(5)  # Wait 5 seconds for Node.js to start
        if self.running:
            self._start_telegram_service()
    
    def _start_node_service(self):
        """Start the Node.js proxy service"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_callback_node(f"[{timestamp}] 🚀 Starting Node.js Proxy Service...\n")
            
            # Determine Node.js executable path
            if getattr(sys, 'frozen', False):
                # In PyInstaller bundle
                node_exe = self.base_path / "nodejs" / "node.exe"
                project_root = self.base_path
            else:
                # Development mode - use system Node.js
                node_exe = "node"
                project_root = self.base_path
            
            # Prepare environment
            env = os.environ.copy()
            env['NODE_ENV'] = 'production'
            env['PATH'] = str(self.base_path / "nodejs") + os.pathsep + env.get('PATH', '')
            
            # Start Node.js process
            index_js = project_root / "index.js"
            
            if sys.platform == "win32":
                # Windows-specific: hide console window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            else:
                startupinfo = None
            
            self.node_process = subprocess.Popen(
                [str(node_exe), str(index_js)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(project_root),
                env=env,
                text=True,
                bufsize=1,
                universal_newlines=True,
                startupinfo=startupinfo
            )
            
            # Stream output
            for line in iter(self.node_process.stdout.readline, ''):
                if not self.running:
                    break
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log_callback_node(f"[{timestamp}] {line}")
            
            self.node_process.wait()
            
            if self.running:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log_callback_node(f"[{timestamp}] ❌ Node.js service stopped unexpectedly\n")
        
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_callback_node(f"[{timestamp}] ❌ Error starting Node.js service: {e}\n")
    
    def _start_telegram_service(self):
        """Start the Telegram bot service"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_callback_telegram(f"[{timestamp}] 🚀 Starting Telegram Bot Service...\n")
            
            # Determine Python executable and bot path
            if getattr(sys, 'frozen', False):
                # In PyInstaller bundle - use bundled Python
                python_exe = sys.executable
                bot_script = self.base_path / "telegram_bot" / "bot.py"
            else:
                # Development mode
                python_exe = sys.executable
                bot_script = self.base_path / "telegram_bot" / "bot.py"
            
            # Prepare environment
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'
            
            if sys.platform == "win32":
                # Windows-specific: hide console window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            else:
                startupinfo = None
            
            self.telegram_process = subprocess.Popen(
                [str(python_exe), str(bot_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(self.base_path),
                env=env,
                text=True,
                bufsize=1,
                universal_newlines=True,
                startupinfo=startupinfo
            )
            
            # Stream output
            for line in iter(self.telegram_process.stdout.readline, ''):
                if not self.running:
                    break
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log_callback_telegram(f"[{timestamp}] {line}")
            
            self.telegram_process.wait()
            
            if self.running:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log_callback_telegram(f"[{timestamp}] ❌ Telegram bot service stopped unexpectedly\n")
        
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_callback_telegram(f"[{timestamp}] ❌ Error starting Telegram bot: {e}\n")
    
    def stop_services(self):
        """Stop both services gracefully"""
        if not self.running:
            return
        
        self.running = False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Stop Telegram bot
        if self.telegram_process and self.telegram_process.poll() is None:
            self.log_callback_telegram(f"[{timestamp}] 🛑 Stopping Telegram Bot...\n")
            try:
                self.telegram_process.terminate()
                self.telegram_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.telegram_process.kill()
            self.log_callback_telegram(f"[{timestamp}] ✓ Telegram Bot stopped\n")
        
        # Stop Node.js proxy
        if self.node_process and self.node_process.poll() is None:
            self.log_callback_node(f"[{timestamp}] 🛑 Stopping Node.js Proxy...\n")
            try:
                self.node_process.terminate()
                self.node_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.node_process.kill()
            self.log_callback_node(f"[{timestamp}] ✓ Node.js Proxy stopped\n")


class LauncherGUI:
    """Main GUI application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("FreeQwenApi - Control Panel")
        self.root.geometry("1200x700")
        
        # Queues for thread-safe log updates
        self.node_queue = queue.Queue()
        self.telegram_queue = queue.Queue()
        
        # Service manager
        self.service_manager = ServiceManager(
            log_callback_node=self._enqueue_node_log,
            log_callback_telegram=self._enqueue_telegram_log
        )
        
        # Build GUI
        self._build_gui()
        
        # Setup periodic log update
        self._update_logs()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Auto-start services
        self.root.after(500, self.start_services)
    
    def _build_gui(self):
        """Build the GUI layout"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="🚀 FreeQwenApi - Node.js Proxy & Telegram Bot",
            font=("Helvetica", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        self.start_button = ttk.Button(
            control_frame,
            text="▶ Start Services",
            command=self.start_services
        )
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(
            control_frame,
            text="⏹ Stop Services",
            command=self.stop_services,
            state=tk.NORMAL
        )
        self.stop_button.grid(row=0, column=1, padx=5)
        
        ttk.Button(
            control_frame,
            text="🗑 Clear Node Logs",
            command=lambda: self.node_log.delete(1.0, tk.END)
        ).grid(row=0, column=2, padx=5)
        
        ttk.Button(
            control_frame,
            text="🗑 Clear Telegram Logs",
            command=lambda: self.telegram_log.delete(1.0, tk.END)
        ).grid(row=0, column=3, padx=5)
        
        # Node.js log panel
        node_label_frame = ttk.LabelFrame(main_frame, text="📡 Node.js Proxy Logs", padding="5")
        node_label_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self.node_log = scrolledtext.ScrolledText(
            node_label_frame,
            wrap=tk.WORD,
            width=60,
            height=25,
            font=("Consolas", 9)
        )
        self.node_log.pack(fill=tk.BOTH, expand=True)
        
        # Telegram bot log panel
        telegram_label_frame = ttk.LabelFrame(main_frame, text="🤖 Telegram Bot Logs", padding="5")
        telegram_label_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        self.telegram_log = scrolledtext.ScrolledText(
            telegram_label_frame,
            wrap=tk.WORD,
            width=60,
            height=25,
            font=("Consolas", 9)
        )
        self.telegram_log.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready to start services...")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def _enqueue_node_log(self, message):
        """Thread-safe method to add Node.js log message"""
        self.node_queue.put(message)
    
    def _enqueue_telegram_log(self, message):
        """Thread-safe method to add Telegram log message"""
        self.telegram_queue.put(message)
    
    def _update_logs(self):
        """Update log displays from queues"""
        # Update Node.js logs
        try:
            while True:
                message = self.node_queue.get_nowait()
                self.node_log.insert(tk.END, message)
                self.node_log.see(tk.END)
        except queue.Empty:
            pass
        
        # Update Telegram logs
        try:
            while True:
                message = self.telegram_queue.get_nowait()
                self.telegram_log.insert(tk.END, message)
                self.telegram_log.see(tk.END)
        except queue.Empty:
            pass
        
        # Schedule next update
        self.root.after(100, self._update_logs)
    
    def start_services(self):
        """Start both services"""
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("🟢 Services starting...")
        self.service_manager.start_services()
        self.status_var.set("🟢 Services running")
    
    def stop_services(self):
        """Stop both services"""
        self.status_var.set("🟡 Stopping services...")
        self.service_manager.stop_services()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("🔴 Services stopped")
    
    def _on_closing(self):
        """Handle window close event"""
        if self.service_manager.running:
            if messagebox.askokcancel("Quit", "Services are running. Stop and quit?"):
                self.stop_services()
                self.root.after(1000, self.root.destroy)
        else:
            self.root.destroy()


def main():
    """Main entry point"""
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nShutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and run GUI
    root = tk.Tk()
    app = LauncherGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
