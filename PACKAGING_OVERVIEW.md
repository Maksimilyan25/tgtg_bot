# FreeQwenApi - Packaging & Distribution Overview

## Executive Summary

FreeQwenApi can now be packaged as a **standalone Windows executable** that bundles both the Node.js proxy and Python Telegram bot into a single distributable application with a user-friendly GUI.

## What's Included

### 📦 New Files

| File | Purpose |
|------|---------|
| `launcher.py` | Main GUI application with dual log windows |
| `build_exe.py` | Automated build script to create the .exe |
| `build.bat` | Quick Windows batch script to run the build |
| `run_gui.py` | Helper script to test GUI in development |
| `test_launcher.py` | Automated tests for launcher components |
| `BUILD_INSTRUCTIONS.md` | Complete guide for building the executable |
| `LAUNCHER_GUIDE.md` | User guide for the GUI application |
| `PACKAGING_OVERVIEW.md` | This document |

### 🎯 Key Features

1. **Single Executable Distribution**
   - One `.exe` file contains everything
   - Python runtime bundled (no installation needed)
   - Node.js runtime bundled (portable version)
   - All dependencies pre-installed

2. **Dual Log Windows GUI**
   - Real-time Node.js proxy logs (left panel)
   - Real-time Telegram bot logs (right panel)
   - Timestamps on every log entry
   - Start/Stop/Clear controls

3. **Process Management**
   - Automatic startup of both services
   - 5-second delay between service starts
   - Graceful shutdown handling
   - No orphaned processes

4. **Zero-Configuration Startup**
   - Just run `FreeQwenApi.exe`
   - Services start automatically
   - GUI displays all output
   - Clean exit on close

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                FreeQwenApi.exe                      │
│         (Python + tkinter GUI + PyInstaller)        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────┐    ┌──────────────────┐     │
│  │  ServiceManager  │    │   LauncherGUI    │     │
│  │                  │    │                  │     │
│  │  - Spawns procs  │◄──►│  - Dual panels  │     │
│  │  - Captures I/O  │    │  - Controls     │     │
│  │  - Manages life  │    │  - Status bar   │     │
│  └──────────────────┘    └──────────────────┘     │
│           │                                         │
└───────────┼─────────────────────────────────────────┘
            │
            ├──► nodejs/node.exe index.js
            │    (Node.js Proxy on port 3000)
            │
            └──► python.exe telegram_bot/bot.py
                 (Telegram Bot)
```

## Build Process

### Prerequisites

- Python 3.8+
- Internet connection (for Node.js download)
- Windows (for .exe output)

### Steps

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Run build script
python build_exe.py
# OR
build.bat

# 3. Find output in releases/FreeQwenApi/
```

### What Happens During Build

1. **Cleanup** - Removes old build artifacts
2. **Download Node.js** - Fetches portable Node.js v20.11.0 (~30 MB)
3. **Install npm packages** - Runs `npm install` for node_modules
4. **Install Python packages** - Installs from requirements.txt
5. **Install Playwright** - Downloads Chromium browser
6. **Generate PyInstaller spec** - Creates build configuration
7. **Run PyInstaller** - Bundles everything into .exe
8. **Create release package** - Packages with docs and directories

### Build Output

```
releases/FreeQwenApi/
├── FreeQwenApi.exe          ← Main executable (GUI launcher)
├── nodejs/                   ← Portable Node.js runtime
│   ├── node.exe
│   └── npm.cmd
├── node_modules/             ← All npm packages
├── src/                      ← Node.js proxy source
├── telegram_bot/             ← Telegram bot source
├── index.js                  ← Main Node.js entry
├── package.json
├── examples/
├── scripts/
├── uploads/                  ← Upload directory
├── logs/                     ← Logs directory
├── session/                  ← Session storage
├── README.txt                ← User instructions
└── [many PyInstaller files]
```

### Size Expectations

- **Uncompressed**: ~500-800 MB
- **Compressed (.zip)**: ~200-300 MB
- **Build time**: 10-20 minutes (first time)

## Distribution

### For End Users

1. Download `FreeQwenApi.zip` from releases
2. Extract to any folder
3. Run `FreeQwenApi.exe`
4. Done!

**No installation required. No Python or Node.js needed.**

### For Distributors

```bash
# After building, create distribution package:
cd releases
zip -r FreeQwenApi.zip FreeQwenApi/

# Upload FreeQwenApi.zip to:
# - GitHub Releases
# - File sharing service
# - Direct download link
```

## Usage Scenarios

### Scenario 1: Development

**Before**: Two separate terminals
```bash
# Terminal 1
npm start

# Terminal 2
cd telegram_bot && python bot.py
```

**After**: Single GUI
```bash
python launcher.py
```

### Scenario 2: Testing

**Before**: Manual setup
```bash
# Install Node.js
# Install Python
# npm install
# pip install -r requirements.txt
# Start services manually
```

**After**: Just run
```bash
FreeQwenApi.exe
```

### Scenario 3: Client Delivery

**Before**: Complex instructions
- Install Python 3.8+
- Install Node.js 16+
- Clone repository
- Install dependencies
- Configure environment
- Start services

**After**: Simple instructions
- Extract zip
- Run exe

## Technical Details

### Process Management

```python
# ServiceManager handles:
- Process spawning (subprocess.Popen)
- Output capture (stdout/stderr pipes)
- Real-time streaming (line-by-line)
- Graceful termination (SIGTERM → SIGKILL)
- Cleanup on exit
```

### GUI Implementation

```python
# LauncherGUI provides:
- tkinter-based interface (built into Python)
- ScrolledText widgets for logs
- Queue-based thread-safe updates
- Auto-scroll to latest logs
- Control buttons (Start/Stop/Clear)
```

### PyInstaller Configuration

```python
# FreeQwenApi.spec includes:
- All source files as datas
- Node.js runtime as datas
- node_modules as datas
- Hidden imports for dependencies
- Console=False for GUI-only mode
- UPX compression enabled
```

## Configuration

### Node.js Proxy

Edit files in installation directory:
- Environment: `.env` or system environment
- Config: `src/` directory files
- Tokens: `session/` directory

### Telegram Bot

Edit files in installation directory:
- Bot token: `telegram_bot/.env`
- Settings: `telegram_bot/config.py`

**Changes take effect after restarting services via GUI.**

## Troubleshooting Build

### Common Issues

| Issue | Solution |
|-------|----------|
| "Python not found" | Install Python 3.8+ and add to PATH |
| "pip install failed" | Run `python -m pip install --upgrade pip` |
| "Node.js download failed" | Check internet connection |
| "PyInstaller failed" | Ensure 2-3 GB free disk space |
| Build very slow | Normal for first build (10-20 min) |

### Clean Build

```bash
# Remove all build artifacts
rm -rf build/ dist/ releases/ *.spec nodejs_portable/

# Rebuild
python build_exe.py
```

## Advanced Customization

### Change Node.js Version

Edit `build_exe.py`:
```python
self.node_version = "v20.11.0"  # Change here
```

### Change Startup Delay

Edit `launcher.py`:
```python
def _delayed_telegram_start(self):
    time.sleep(5)  # Change delay here
```

### Add Custom Files

Edit `build_exe.py` in `create_pyinstaller_spec()`:
```python
datas = [
    ('your_custom_file.txt', '.'),
    # ...
]
```

### Single-File Executable

Edit PyInstaller spec:
```python
exe = EXE(
    # ...
    onefile=True,  # Add this (creates single .exe, slower startup)
)
```

## Testing

### Pre-Build Tests

```bash
# Run component tests
python test_launcher.py
```

### Development Testing

```bash
# Test GUI without building .exe
python launcher.py
```

### Post-Build Testing

1. Run `FreeQwenApi.exe`
2. Verify both log panels show output
3. Check Node.js listening on port 3000
4. Test Telegram bot connection
5. Try Stop/Start buttons
6. Verify graceful shutdown

## Performance

### Resource Usage

- **RAM**: ~200-300 MB (both services)
- **CPU**: Low during idle, moderate during requests
- **Disk**: Minimal (logs only)
- **Network**: Required for API calls

### Optimization

- Clear logs regularly (prevents memory buildup)
- Close when not in use
- Monitor Task Manager for issues

## Security Considerations

### Data Protection

- Logs may contain sensitive data
- API keys should be in environment variables
- Don't hardcode secrets before building
- Distribute .exe securely

### Antivirus

- PyInstaller executables may trigger antivirus
- Add exception if needed
- Sign the executable for production (optional)

### Firewall

- Allow port 3000 for Node.js proxy
- Telegram bot uses outbound connections only

## Maintenance

### Updates

To update the application:

1. Make code changes
2. Rebuild: `python build_exe.py`
3. Distribute new .exe
4. Users replace entire folder

### Version Control

Recommended `.gitignore` entries (already added):
```
build/
dist/
releases/
*.spec
nodejs_portable/
*.zip
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build Executable

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Build executable
        run: python build_exe.py
      
      - name: Create release
        uses: actions/upload-artifact@v2
        with:
          name: FreeQwenApi-Windows
          path: releases/FreeQwenApi
```

## Documentation Reference

| Document | Purpose |
|----------|---------|
| `PACKAGING_OVERVIEW.md` | This document - high-level overview |
| `BUILD_INSTRUCTIONS.md` | Step-by-step build guide |
| `LAUNCHER_GUIDE.md` | End-user GUI guide |
| `README.md` | Main project documentation |

## Support

For packaging-related issues:

1. Check `BUILD_INSTRUCTIONS.md`
2. Run `python test_launcher.py`
3. Review error messages
4. Create issue on repository

## Future Enhancements

Possible improvements:

- [ ] System tray icon and minimize to tray
- [ ] Log rotation and size limits
- [ ] Configuration editor in GUI
- [ ] Update checker
- [ ] Multiple language support
- [ ] macOS and Linux builds
- [ ] Installer (NSIS, Inno Setup)
- [ ] Code signing for production

## License

Same as main project.

## Credits

**Built with:**
- Python 3.x
- tkinter (GUI)
- PyInstaller (packaging)
- Node.js (portable)
- Playwright (automation)

---

**Version**: 1.0
**Date**: January 2024
**Status**: Production Ready
