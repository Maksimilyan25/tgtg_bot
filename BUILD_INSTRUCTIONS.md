# Building FreeQwenApi Standalone Executable

This guide explains how to build a standalone `.exe` file that bundles both the Node.js proxy and Python Telegram bot into a single distributable application.

## What Gets Built

The build process creates a **single executable package** (`FreeQwenApi.exe`) that includes:

- ✅ Python runtime (bundled, no Python installation needed)
- ✅ Node.js runtime (portable, no Node.js installation needed)
- ✅ All Node.js dependencies (node_modules)
- ✅ All Python dependencies (packages)
- ✅ Complete source code (Node.js proxy + Telegram bot)
- ✅ GUI launcher with dual log windows
- ✅ Playwright Chromium browser (for automation)

## Prerequisites

### On the Build Machine (Where You Build the .exe)

You need:

1. **Python 3.8+** installed
2. **Internet connection** (to download Node.js and dependencies)
3. **Windows OS** (for building Windows .exe)

That's it! The build script handles everything else.

## Build Steps

### Option 1: Quick Build (Recommended)

1. Open Command Prompt in the project directory
2. Run:
   ```bat
   build.bat
   ```

3. Wait for the build to complete (may take 10-20 minutes)
4. Find your executable in `releases/FreeQwenApi/`

### Option 2: Manual Build

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the build script:
   ```bash
   python build_exe.py
   ```

3. The script will:
   - Download Node.js portable runtime (~30 MB)
   - Install all Node.js dependencies
   - Install all Python dependencies
   - Install Playwright browsers
   - Create PyInstaller spec file
   - Build the executable with PyInstaller
   - Package everything into `releases/FreeQwenApi/`

## Build Output

After a successful build, you'll have:

```
releases/
└── FreeQwenApi/
    ├── FreeQwenApi.exe          ← The main executable
    ├── nodejs/                   ← Bundled Node.js runtime
    ├── node_modules/             ← All Node.js dependencies
    ├── src/                      ← Node.js proxy source
    ├── telegram_bot/             ← Telegram bot source
    ├── index.js                  ← Main Node.js entry point
    ├── package.json
    ├── uploads/                  ← Upload directory
    ├── logs/                     ← Logs directory
    ├── session/                  ← Session storage
    ├── README.txt                ← User guide
    └── [many other bundled files]
```

## Distribution

To distribute the application:

1. **Zip the entire `FreeQwenApi` folder** from `releases/`
2. Send the zip to users
3. Users extract and run `FreeQwenApi.exe`

⚠️ **Important**: Users must receive the **entire folder**, not just the .exe file!

## Running the Built Application

### For End Users (No Python/Node.js Required)

1. Extract the `FreeQwenApi` folder
2. Double-click `FreeQwenApi.exe`
3. The GUI will launch with two log panels
4. Services start automatically

### GUI Features

The launcher provides:

- **Dual Log Windows**: 
  - Left panel: Node.js Proxy logs
  - Right panel: Telegram Bot logs
- **Control Buttons**:
  - Start/Stop services
  - Clear logs for each panel
- **Real-time Logging**: All output captured with timestamps
- **Graceful Shutdown**: Properly stops both services on exit

## Application Architecture

```
FreeQwenApi.exe (Python + tkinter GUI)
    │
    ├─► Spawns: node.exe index.js (Node.js Proxy)
    │   └─► Logs to: Left panel
    │
    └─► Spawns: python.exe telegram_bot/bot.py (Telegram Bot)
        └─► Logs to: Right panel
```

## Configuration

After building, users can configure:

1. **Node.js Proxy**: Edit files in `src/` directory
2. **Telegram Bot**: Edit `.env` or configuration in `telegram_bot/`

Configuration files are in plain text and can be edited before or after distribution.

## Troubleshooting Build Issues

### "Python not found"
- Install Python 3.8+ from python.org
- Ensure Python is in your PATH

### "pip install failed"
- Run: `python -m pip install --upgrade pip`
- Retry the build

### "Node.js download failed"
- Check your internet connection
- The script needs to download ~30 MB from nodejs.org

### "PyInstaller failed"
- Ensure you have enough disk space (need ~2-3 GB)
- Try: `pip install --upgrade pyinstaller`

### Build is very slow
- Normal! First build takes 10-20 minutes
- PyInstaller needs to bundle hundreds of MB of dependencies
- Subsequent builds are faster (caches some data)

## Size Expectations

- **Build directory**: ~2 GB (temporary, can be deleted)
- **Final executable folder**: ~500-800 MB
- **Zipped distribution**: ~200-300 MB

This is normal for bundled applications that include:
- Complete Node.js runtime
- Complete Python runtime  
- All npm packages (node_modules)
- All Python packages
- Chromium browser for Playwright

## Advanced: Customizing the Build

### Reducing Size

Edit `build_exe.py` to:

1. Use `--onefile` in PyInstaller (creates single .exe, but slower startup)
2. Exclude unnecessary node_modules
3. Use UPX compression more aggressively

### Changing Node.js Version

Edit `build_exe.py`:

```python
self.node_version = "v20.11.0"  # Change to desired version
```

### Adding Custom Resources

Edit the `datas` section in the generated `FreeQwenApi.spec`:

```python
datas = [
    ('your_custom_file.txt', '.'),
    # ... other files
]
```

## Development vs. Production

### Development (Before Building)

Run normally:
```bash
# Terminal 1
npm start

# Terminal 2  
cd telegram_bot
python bot.py
```

### Production (After Building)

Distribute and run:
```
FreeQwenApi.exe
```

## CI/CD Integration

To integrate into CI/CD:

```yaml
# GitHub Actions example
- name: Build Executable
  run: |
    pip install -r requirements.txt
    python build_exe.py
    
- name: Upload Release
  uses: actions/upload-artifact@v2
  with:
    name: FreeQwenApi
    path: releases/FreeQwenApi
```

## Security Notes

- The built executable contains all source code
- Sensitive data (API keys, tokens) should use environment variables
- Users should configure secrets in their local installation
- Do not hardcode secrets before building

## Support

For build issues:

1. Check this document
2. Review error messages in build output
3. Ensure prerequisites are met
4. Try a clean build (`python build_exe.py` after deleting `build/` and `dist/`)

## License

Same as the main project.
