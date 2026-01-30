# FreeQwenApi Launcher GUI - User Guide

## Overview

The FreeQwenApi Launcher is a graphical user interface (GUI) that consolidates the Node.js Proxy and Python Telegram Bot into a single, easy-to-use application with dual log windows.

## Features

### 🎯 Core Features

- **Dual Log Windows**: Separate real-time log panels for each service
- **Automatic Startup**: Both services start automatically when the application launches
- **Process Management**: Clean start/stop controls for both services
- **Real-time Monitoring**: Watch both services' output in real-time with timestamps
- **Graceful Shutdown**: Properly terminates both processes when closing the application
- **No Console Windows**: Clean GUI experience without command-line windows

### 📊 Log Panels

#### Left Panel: Node.js Proxy Logs
- Shows all output from the Express server
- API request/response logs
- Browser automation events
- Error messages and stack traces

#### Right Panel: Telegram Bot Logs
- Telegram bot startup messages
- User interaction logs
- Command processing
- Error handling

## User Interface

```
┌─────────────────────────────────────────────────────────────┐
│         🚀 FreeQwenApi - Node.js Proxy & Telegram Bot       │
├─────────────────────────────────────────────────────────────┤
│  [▶ Start] [⏹ Stop] [🗑 Clear Node] [🗑 Clear Telegram]    │
├──────────────────────────┬──────────────────────────────────┤
│  📡 Node.js Proxy Logs   │  🤖 Telegram Bot Logs           │
│ ┌────────────────────────┼──────────────────────────────┐  │
│ │ [2024-01-30 10:15:23]  │ [2024-01-30 10:15:28]        │  │
│ │ Starting proxy...      │ Starting Telegram bot...     │  │
│ │ Server listening on    │ Bot connected successfully    │  │
│ │ port 3000...           │ Ready to receive commands     │  │
│ │                        │                               │  │
│ └────────────────────────┴──────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│ Status: 🟢 Services running                                 │
└─────────────────────────────────────────────────────────────┘
```

## Controls

### Buttons

| Button | Function |
|--------|----------|
| **▶ Start Services** | Starts both Node.js proxy and Telegram bot |
| **⏹ Stop Services** | Gracefully stops both services |
| **🗑 Clear Node Logs** | Clears the Node.js log panel |
| **🗑 Clear Telegram Logs** | Clears the Telegram bot log panel |

### Status Indicators

- 🟢 **Green**: Services running normally
- 🟡 **Yellow**: Services starting or stopping
- 🔴 **Red**: Services stopped

## Startup Sequence

When you start the application:

1. **Node.js Proxy starts first** (0 seconds)
   - Initializes Express server
   - Sets up browser automation
   - Starts listening on port 3000

2. **5-second delay** (gives Node.js time to initialize)

3. **Telegram Bot starts** (5 seconds)
   - Connects to Telegram API
   - Registers command handlers
   - Ready to receive messages

## Shutdown Sequence

When you stop services or close the application:

1. **Telegram Bot stops first**
   - Disconnects from Telegram API
   - Cleans up handlers

2. **Node.js Proxy stops second**
   - Closes active connections
   - Shuts down Express server
   - Closes browser instances

Both processes are given 5 seconds to shut down gracefully before being force-terminated.

## Log Format

All logs include timestamps:

```
[YYYY-MM-DD HH:MM:SS] Log message here
```

Example:
```
[2024-01-30 14:30:45] 🚀 Starting Node.js Proxy Service...
[2024-01-30 14:30:47] Server listening on http://localhost:3000
[2024-01-30 14:30:50] 🚀 Starting Telegram Bot Service...
[2024-01-30 14:30:52] Bot connected successfully
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Graceful shutdown (when focused on terminal) |
| `Alt+F4` | Close application (prompts if services running) |

## Common Scenarios

### Starting the Application

1. Double-click `FreeQwenApi.exe`
2. Wait for GUI to load
3. Services start automatically
4. Watch logs for "Server listening" and "Bot connected" messages

### Stopping the Application

1. Click "Stop Services" button
2. Wait for services to shut down
3. Close the window, or
4. Click "X" to close (prompts for confirmation if services running)

### Viewing Real-time Logs

- Logs automatically scroll to show the latest entries
- Use the scroll bar to view earlier logs
- Clear logs using the "Clear" buttons when needed

### Troubleshooting Errors

1. Check the appropriate log panel for error messages
2. Common issues:
   - **Port already in use**: Another application is using port 3000
   - **Bot token not configured**: Set up Telegram bot token in config
   - **Network errors**: Check internet connection

## Development Mode

For developers, you can test the GUI without building the .exe:

```bash
# Option 1: Direct
python launcher.py

# Option 2: Using helper script
python run_gui.py
```

This runs the GUI using your system's Python and Node.js installations.

## Configuration

### Node.js Proxy Configuration

Edit configuration files in the installation directory:
- Environment variables in `.env`
- Configuration in `src/` directory

### Telegram Bot Configuration

Edit configuration files:
- `telegram_bot/.env` for bot token and settings
- `telegram_bot/config.py` for advanced settings

Changes take effect after restarting services.

## Performance

### System Requirements

- **RAM**: ~200-300 MB when running
- **CPU**: Low usage during idle
- **Disk**: Minimal write (logs only)
- **Network**: Required for Telegram API and web requests

### Optimization Tips

1. **Clear logs regularly** to prevent memory buildup
2. **Close when not in use** to free system resources
3. **Monitor log panels** for excessive error messages

## Troubleshooting

### GUI doesn't start

- **Windows Security**: Allow the application through firewall
- **Antivirus**: Add exception for FreeQwenApi.exe
- **Dependencies**: Ensure all files from the distribution are present

### Services fail to start

**Node.js Proxy fails:**
- Port 3000 already in use → close other applications
- Missing files → ensure complete installation
- Configuration errors → check syntax in config files

**Telegram Bot fails:**
- Bot token not set → configure in `.env`
- Network issues → check internet connection
- API rate limits → wait and retry

### Logs not updating

- This is rare; usually indicates process crash
- Check if process is still running in Task Manager
- Restart the application

### High memory usage

- Clear logs regularly (each log panel keeps history)
- Restart application periodically
- Check for memory leaks in log messages

## Advanced Features

### Custom Startup Delay

The Telegram bot starts 5 seconds after the Node.js proxy. To change this, edit `launcher.py`:

```python
def _delayed_telegram_start(self):
    time.sleep(5)  # Change this value (seconds)
    if self.running:
        self._start_telegram_service()
```

### Log File Size Limits

Currently, GUI logs are unlimited. For production, consider:
- Implementing log rotation
- Adding max-lines limit to log panels
- Periodic auto-clear

### Process Priority

To change process priority, edit the `Popen` calls in `launcher.py`:

```python
# Windows example
import psutil
process = psutil.Process(self.node_process.pid)
process.nice(psutil.NORMAL_PRIORITY_CLASS)
```

## Integration

### Using with Other Tools

The launcher is standalone but services can be accessed:

- **Node.js Proxy API**: http://localhost:3000/api
- **Telegram Bot**: Through Telegram app
- **Logs**: Written to `logs/` directory

### Monitoring

External monitoring can:
- Check port 3000 for proxy health
- Read log files in `logs/` directory
- Query status endpoint: http://localhost:3000/api/status

## Security

### Running as Non-Admin

The application doesn't require administrator privileges.

### Firewall

Allow incoming connections on port 3000 for the Node.js proxy.

### Data Protection

- Logs may contain sensitive data
- Store the application securely
- Clear logs before sharing screenshots

## FAQ

**Q: Can I run multiple instances?**
A: No, port 3000 is single-use. Modify configuration for different ports.

**Q: Can I minimize to system tray?**
A: Not in the current version. Minimize normally to taskbar.

**Q: How do I update?**
A: Replace the entire installation folder with the new version.

**Q: Where are persistent logs stored?**
A: In the `logs/` directory within the installation folder.

**Q: Can I run this on Linux/Mac?**
A: The .exe is Windows-only. Use `python launcher.py` on other platforms.

## Support

For issues:

1. Check log panels for error messages
2. Review this guide
3. Check BUILD_INSTRUCTIONS.md for build-related issues
4. Create an issue on the project repository

## Credits

Built with:
- **tkinter**: GUI framework (built into Python)
- **PyInstaller**: Executable packaging
- **Node.js**: JavaScript runtime
- **Python**: Application logic
