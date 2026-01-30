# FreeQwenApi Packaging Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      End User Experience                     │
├─────────────────────────────────────────────────────────────┤
│  1. Download FreeQwenApi.zip                                │
│  2. Extract to folder                                        │
│  3. Double-click FreeQwenApi.exe                            │
│  4. GUI opens → Services start → Ready to use               │
└─────────────────────────────────────────────────────────────┘
```

## Build-Time Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    build_exe.py (Builder)                     │
└──────────────────────────────────────────────────────────────┘
                              │
                              ├─► Step 1: Download Node.js v20.11.0
                              │   └─► nodejs_portable/ (30 MB)
                              │
                              ├─► Step 2: npm install
                              │   └─► node_modules/ (100-200 MB)
                              │
                              ├─► Step 3: pip install -r requirements.txt
                              │   └─► Python packages
                              │
                              ├─► Step 4: playwright install chromium
                              │   └─► Browser binaries
                              │
                              ├─► Step 5: Generate FreeQwenApi.spec
                              │   └─► PyInstaller configuration
                              │
                              ├─► Step 6: Run PyInstaller
                              │   └─► dist/FreeQwenApi/ (500-800 MB)
                              │
                              └─► Step 7: Package release
                                  └─► releases/FreeQwenApi/ + README.txt
```

## Runtime Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    FreeQwenApi.exe                           │
│                  (PyInstaller Bundle)                         │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ Unpacks to temp dir (sys._MEIPASS)
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                      launcher.py                             │
│                    (Main Entry Point)                         │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ Creates
                              ▼
         ┌────────────────────────────────────────┐
         │           LauncherGUI                  │
         │          (tkinter GUI)                 │
         ├────────────────────────────────────────┤
         │  ┌──────────────┐  ┌──────────────┐  │
         │  │ Node.js Logs │  │Telegram Logs │  │
         │  │   (Panel 1)  │  │  (Panel 2)   │  │
         │  └──────────────┘  └──────────────┘  │
         │  [Start] [Stop] [Clear] [Clear]      │
         │  Status: 🟢 Services running          │
         └────────────────────────────────────────┘
                              │
                              │ Manages
                              ▼
         ┌────────────────────────────────────────┐
         │         ServiceManager                 │
         │       (Process Controller)             │
         └────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
    ┌───────────────────┐       ┌───────────────────┐
    │  Node.js Process  │       │   Python Process  │
    │  (node.exe)       │       │   (python.exe)    │
    └───────────────────┘       └───────────────────┘
                │                           │
                ▼                           ▼
    ┌───────────────────┐       ┌───────────────────┐
    │   index.js        │       │  telegram_bot/    │
    │   (Express API)   │       │     bot.py        │
    │   Port: 3000      │       │  (Bot Logic)      │
    └───────────────────┘       └───────────────────┘
```

## Data Flow Diagram

### Process Startup Flow

```
User runs FreeQwenApi.exe
        │
        ▼
PyInstaller unpacks to %TEMP%
        │
        ▼
Python interpreter starts
        │
        ▼
launcher.py main() called
        │
        ▼
LauncherGUI() instantiated
        │
        ├─► Creates tkinter.Tk() root window
        │
        ├─► Builds GUI components
        │   ├─► Control buttons
        │   ├─► Log panels (ScrolledText)
        │   └─► Status bar
        │
        ├─► Creates ServiceManager
        │   ├─► Sets up log callbacks
        │   └─► Determines base_path
        │
        └─► Schedules auto-start (500ms delay)
                │
                ▼
        ServiceManager.start_services()
                │
                ├─► Thread 1: Start Node.js
                │   ├─► Finds nodejs/node.exe
                │   ├─► Popen([node.exe, index.js])
                │   ├─► Captures stdout/stderr
                │   └─► Streams to left log panel
                │
                └─► Thread 2: Start Telegram Bot (5s delay)
                    ├─► Uses bundled python.exe
                    ├─► Popen([python.exe, telegram_bot/bot.py])
                    ├─► Captures stdout/stderr
                    └─► Streams to right log panel
```

### Log Streaming Flow

```
Service Process (node.exe or python.exe)
        │
        │ stdout.write("log message\n")
        │
        ▼
subprocess.PIPE (captured by ServiceManager)
        │
        │ for line in process.stdout.readline()
        │
        ▼
log_callback_node() or log_callback_telegram()
        │
        │ Adds timestamp
        │ [2024-01-30 10:15:23] log message
        │
        ▼
Queue (thread-safe)
        │
        │ node_queue.put(message)
        │ or
        │ telegram_queue.put(message)
        │
        ▼
LauncherGUI._update_logs() [called every 100ms]
        │
        │ while not queue.empty():
        │     message = queue.get_nowait()
        │
        ▼
ScrolledText widget
        │
        │ insert(END, message)
        │ see(END)  # auto-scroll
        │
        ▼
User sees log in GUI panel
```

### Shutdown Flow

```
User clicks Stop or closes window
        │
        ▼
ServiceManager.stop_services()
        │
        │ self.running = False
        │
        ├─► Stop Telegram Bot first
        │   ├─► telegram_process.terminate()
        │   ├─► Wait 5 seconds
        │   └─► Force kill if still running
        │
        └─► Stop Node.js Proxy second
            ├─► node_process.terminate()
            ├─► Wait 5 seconds
            └─► Force kill if still running
                │
                ▼
        All processes terminated
                │
                ▼
        GUI closes (if window closed)
```

## Component Interaction Diagram

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ Double-click
       ▼
┌─────────────────────────────────┐
│     FreeQwenApi.exe             │
│  (PyInstaller Bootloader)       │
└─────────┬───────────────────────┘
          │ Unpacks & launches
          ▼
┌─────────────────────────────────┐
│      Python Interpreter         │
│     (Bundled in .exe)           │
└─────────┬───────────────────────┘
          │ Executes
          ▼
┌─────────────────────────────────┐
│       launcher.py               │
│  ┌───────────────────────────┐ │
│  │    import tkinter         │ │
│  │    import subprocess      │ │
│  │    import threading       │ │
│  └───────────────────────────┘ │
└─────────┬───────────────────────┘
          │ Instantiates
          ▼
┌─────────────────────────────────┐
│      LauncherGUI                │
│  ┌───────────────────────────┐ │
│  │  tkinter.Tk root window   │ │
│  │  - Buttons                │ │
│  │  - Log panels             │ │
│  │  - Status bar             │ │
│  └───────────────────────────┘ │
└─────────┬───────────────────────┘
          │ Creates & uses
          ▼
┌─────────────────────────────────┐
│     ServiceManager              │
│  ┌───────────────────────────┐ │
│  │  start_services()         │ │
│  │  stop_services()          │ │
│  │  _start_node_service()    │ │
│  │  _start_telegram_service()│ │
│  └───────────────────────────┘ │
└─────────┬───────────────────────┘
          │ Spawns via subprocess.Popen
          │
    ┌─────┴────────┐
    ▼              ▼
┌────────┐    ┌──────────┐
│node.exe│    │python.exe│
└───┬────┘    └────┬─────┘
    │              │
    ▼              ▼
┌────────┐    ┌──────────┐
│index.js│    │  bot.py  │
└───┬────┘    └────┬─────┘
    │              │
    │ Outputs      │ Outputs
    └────┬─────────┘
         │ stdout/stderr
         ▼
    Captured & displayed
         in GUI
```

## File System Layout

### Build-Time

```
/home/engine/project/
├── launcher.py              ← Source: GUI application
├── build_exe.py             ← Source: Build script
├── index.js                 ← Source: Node.js entry
├── telegram_bot/            ← Source: Bot code
├── src/                     ← Source: Proxy logic
├── node_modules/            ← Dependencies (npm)
├── requirements.txt         ← Dependencies (pip)
│
└── [After build_exe.py runs]
    ├── nodejs_portable/     ← Downloaded: Node.js runtime
    │   ├── node.exe
    │   └── npm.cmd
    │
    ├── build/               ← PyInstaller temp files
    │   └── FreeQwenApi/
    │
    ├── dist/                ← PyInstaller output
    │   └── FreeQwenApi/
    │       ├── FreeQwenApi.exe
    │       ├── python39.dll
    │       ├── [many DLLs]
    │       ├── nodejs/      (copied from nodejs_portable)
    │       ├── node_modules/ (copied)
    │       ├── src/         (copied)
    │       └── telegram_bot/ (copied)
    │
    └── releases/            ← Final package
        └── FreeQwenApi/
            ├── FreeQwenApi.exe ← Main executable
            ├── README.txt
            ├── uploads/
            ├── logs/
            └── session/
```

### Runtime (sys._MEIPASS)

When FreeQwenApi.exe runs, PyInstaller unpacks to temp:

```
%TEMP%/_MEI123456/           ← Temporary extraction
├── python39.dll
├── [many DLLs and dependencies]
├── launcher.py              ← Extracted
├── index.js                 ← Extracted
├── nodejs/                  ← Extracted
│   └── node.exe
├── node_modules/            ← Extracted
├── src/                     ← Extracted
└── telegram_bot/            ← Extracted
```

But working directory is:
```
C:/Users/Someone/FreeQwenApi/ ← Where .exe was run from
├── FreeQwenApi.exe
├── uploads/                  ← Writable data here
├── logs/                     ← Writable data here
└── session/                  ← Writable data here
```

## Process Hierarchy

```
FreeQwenApi.exe (PID: 1234)
└─ python.exe (bundled interpreter)
   └─ launcher.py (main script)
      ├─ tkinter GUI (main thread)
      │  └─ _update_logs() [100ms timer]
      │
      └─ ServiceManager
         ├─ Thread: _start_node_service()
         │  └─ subprocess: node.exe index.js (PID: 1235)
         │     └─ Express server on port 3000
         │
         └─ Thread: _start_telegram_service()
            └─ subprocess: python.exe bot.py (PID: 1236)
               └─ Telegram bot client
```

## Memory Layout

```
┌─────────────────────────────────────────┐
│  FreeQwenApi.exe Process Memory         │
├─────────────────────────────────────────┤
│  Python Interpreter (~50 MB)            │
│  - Standard library                     │
│  - Bundled modules                      │
├─────────────────────────────────────────┤
│  tkinter GUI (~20 MB)                   │
│  - Widgets                              │
│  - Log buffers                          │
├─────────────────────────────────────────┤
│  ServiceManager (~10 MB)                │
│  - Process handles                      │
│  - Thread stacks                        │
│  - Queues                               │
└─────────────────────────────────────────┘
         Total: ~80-100 MB

┌─────────────────────────────────────────┐
│  node.exe Process Memory                │
├─────────────────────────────────────────┤
│  Node.js Runtime (~100 MB)              │
│  - V8 engine                            │
│  - libuv                                │
├─────────────────────────────────────────┤
│  Application Code (~50 MB)              │
│  - Express                              │
│  - Playwright                           │
│  - All modules                          │
└─────────────────────────────────────────┘
         Total: ~150-200 MB

┌─────────────────────────────────────────┐
│  python.exe Process Memory              │
│  (Telegram Bot)                         │
├─────────────────────────────────────────┤
│  Python Interpreter (~50 MB)            │
│  - Standard library                     │
├─────────────────────────────────────────┤
│  Bot Libraries (~50 MB)                 │
│  - python-telegram-bot                  │
│  - aiohttp                              │
│  - Playwright                           │
└─────────────────────────────────────────┘
         Total: ~100-150 MB

═════════════════════════════════════════
Grand Total: ~330-450 MB
═════════════════════════════════════════
```

## Network Communication

```
┌─────────────────────────────────────────┐
│          External World                 │
└─────────────────────────────────────────┘
              │                │
              │ HTTP           │ Telegram API
              ▼                ▼
┌─────────────────┐  ┌────────────────────┐
│  localhost:3000 │  │  Telegram Servers  │
│  (Node.js API)  │  │  (Bot Polling)     │
└────────┬────────┘  └─────────┬──────────┘
         │                     │
         │                     │
    ┌────▼─────────────────────▼────┐
    │  Local Machine (Processes)    │
    │                                │
    │  ┌──────────┐  ┌───────────┐ │
    │  │  node.js │  │ telegram  │ │
    │  │  proxy   │  │   bot     │ │
    │  └──────────┘  └───────────┘ │
    │       ▲              ▲        │
    │       │              │        │
    │       └──────┬───────┘        │
    │              │                │
    │       ┌──────▼──────┐        │
    │       │ Service     │        │
    │       │ Manager     │        │
    │       └─────────────┘        │
    └────────────────────────────────┘
```

## Security Boundaries

```
┌──────────────────────────────────────────────┐
│           Operating System                   │
│  ┌────────────────────────────────────────┐ │
│  │  User Space (No Admin Required)        │ │
│  │  ┌──────────────────────────────────┐ │ │
│  │  │  FreeQwenApi.exe Process         │ │ │
│  │  │  - Read: Installation folder     │ │ │
│  │  │  - Write: logs/, uploads/        │ │ │
│  │  │  - Network: Port 3000 (localhost)│ │ │
│  │  └──────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────┐ │ │
│  │  │  node.exe Process                │ │ │
│  │  │  - Bind: Port 3000               │ │ │
│  │  │  - Internet: Qwen API            │ │ │
│  │  └──────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────┐ │ │
│  │  │  python.exe Process (Bot)        │ │ │
│  │  │  - Internet: Telegram API        │ │ │
│  │  └──────────────────────────────────┘ │ │
│  └────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘

Firewall allows:
- Inbound: Port 3000 (local only)
- Outbound: HTTPS (Telegram, Qwen)
```

## Dependency Graph

```
FreeQwenApi.exe
├─ Python 3.x (bundled)
│  ├─ tkinter (built-in)
│  ├─ subprocess (stdlib)
│  ├─ threading (stdlib)
│  ├─ queue (stdlib)
│  └─ pyinstaller (build-time only)
│
├─ Node.js v20.11.0 (bundled)
│  ├─ express
│  ├─ playwright
│  ├─ axios
│  ├─ winston
│  └─ [all from package.json]
│
└─ Python Packages (bundled)
   ├─ python-telegram-bot
   ├─ aiohttp
   ├─ playwright
   ├─ Pillow
   └─ [all from requirements.txt]
```

---

**Document Version**: 1.0
**Last Updated**: January 2024
**Purpose**: Technical architecture documentation for FreeQwenApi packaging
