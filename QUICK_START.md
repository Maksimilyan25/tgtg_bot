# FreeQwenApi - Quick Start Guide

## For Users (Standalone Executable)

### Installation

1. **Download** `FreeQwenApi.zip`
2. **Extract** to any folder (e.g., `C:\FreeQwenApi`)
3. **Run** `FreeQwenApi.exe`

That's it! No Python or Node.js installation required.

### First Launch

When you run `FreeQwenApi.exe`:

1. A window opens with two log panels
2. Services start automatically in 2-3 seconds
3. Left panel: Node.js Proxy logs
4. Right panel: Telegram Bot logs

### Using the GUI

```
┌──────────────────────────────────────────┐
│  [▶ Start] [⏹ Stop] [🗑 Clear] [🗑 Clear] │
├────────────────┬─────────────────────────┤
│  Node.js Logs  │  Telegram Bot Logs     │
│  (Port 3000)   │  (Telegram API)        │
└────────────────┴─────────────────────────┘
```

**Buttons:**
- `▶ Start Services` - Start both services
- `⏹ Stop Services` - Stop both services
- `🗑 Clear` - Clear log panels

### Accessing Services

- **Node.js Proxy**: http://localhost:3000
- **Telegram Bot**: Use your Telegram app

### Configuration

1. **For Node.js Proxy**: Edit files in installation folder
2. **For Telegram Bot**: Edit `telegram_bot/.env`
3. **Restart services**: Click Stop → Start in GUI

### Troubleshooting

**Services won't start?**
- Check logs for error messages
- Ensure port 3000 is not in use
- Configure Telegram bot token if using bot

**GUI doesn't open?**
- Allow through Windows Firewall
- Add antivirus exception
- Run as Administrator (if needed)

---

## For Developers (Build from Source)

### Build the Executable

```bash
# Quick build
build.bat

# Or manual
pip install -r requirements.txt
python build_exe.py
```

Output: `releases/FreeQwenApi/FreeQwenApi.exe`

### Test in Development

```bash
# Test GUI without building
python launcher.py

# Or use helper
python run_gui.py
```

### Run Tests

```bash
python test_launcher.py
```

---

## Documentation

- **For Users**: `LAUNCHER_GUIDE.md`
- **For Builders**: `BUILD_INSTRUCTIONS.md`
- **Overview**: `PACKAGING_OVERVIEW.md`
- **API Docs**: `README.md`

---

## Quick Commands

| Action | Command |
|--------|---------|
| Build .exe | `python build_exe.py` |
| Test GUI | `python launcher.py` |
| Run tests | `python test_launcher.py` |
| Quick build | `build.bat` |

---

## System Requirements

### For Running .exe:
- Windows 7/8/10/11
- 2 GB RAM minimum
- 1 GB free disk space
- Internet connection (for API calls)

### For Building .exe:
- Windows OS
- Python 3.8+
- Internet connection
- 3 GB free disk space

---

## Support

**Need help?**
1. Check the appropriate guide (above)
2. Review log panels for errors
3. See README.md for API documentation
4. Create an issue on GitHub

---

**Version**: 1.0
**License**: Same as main project
