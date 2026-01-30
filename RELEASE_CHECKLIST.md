# FreeQwenApi - Release Checklist

## Pre-Build Checklist

### Code Verification
- [ ] All tests pass: `python test_launcher.py`
- [ ] No syntax errors in launcher.py
- [ ] No syntax errors in build_exe.py
- [ ] Git status is clean (or changes committed)
- [ ] Version numbers updated (if applicable)

### Dependencies
- [ ] `requirements.txt` is up to date
- [ ] `package.json` is up to date
- [ ] All npm packages install correctly: `npm install`
- [ ] All pip packages install correctly: `pip install -r requirements.txt`

### Documentation
- [ ] README.md updated with latest features
- [ ] LAUNCHER_GUIDE.md accurate
- [ ] BUILD_INSTRUCTIONS.md current
- [ ] CHANGELOG updated (if using)

## Build Process

### Environment Setup
- [ ] Running on Windows (required for .exe build)
- [ ] Python 3.8+ installed and in PATH
- [ ] Internet connection active
- [ ] At least 3 GB free disk space
- [ ] Antivirus temporarily disabled (optional, prevents false positives during build)

### Build Steps
```bash
# Clean previous builds (optional but recommended)
rm -rf build/ dist/ releases/ *.spec nodejs_portable/

# Run tests
python test_launcher.py

# Build
python build_exe.py
# OR
build.bat
```

### Build Verification
- [ ] Build completed without errors
- [ ] No warnings in build output (or acceptable warnings noted)
- [ ] Output directory exists: `releases/FreeQwenApi/`
- [ ] Executable exists: `releases/FreeQwenApi/FreeQwenApi.exe`
- [ ] File size reasonable (~500-800 MB folder)

## Post-Build Testing

### Basic Functionality
- [ ] Executable runs (double-click FreeQwenApi.exe)
- [ ] GUI window appears
- [ ] No error dialogs on startup
- [ ] Window title correct: "FreeQwenApi - Control Panel"
- [ ] Both log panels visible

### Service Startup
- [ ] Node.js service starts automatically
- [ ] Node.js logs appear in left panel
- [ ] Telegram bot starts after ~5 seconds
- [ ] Telegram bot logs appear in right panel
- [ ] Both services show "started" or "listening" messages

### Service Functionality
- [ ] Node.js proxy accessible: http://localhost:3000
- [ ] API status endpoint works: http://localhost:3000/api/status
- [ ] Telegram bot connects (if token configured)
- [ ] No error messages in logs
- [ ] Services remain running (no crashes)

### GUI Controls
- [ ] "Stop Services" button works
- [ ] Services stop gracefully
- [ ] "Start Services" button works
- [ ] Services restart successfully
- [ ] "Clear Node Logs" button works
- [ ] "Clear Telegram Logs" button works
- [ ] Window can be resized
- [ ] Logs auto-scroll to bottom

### Process Management
- [ ] Close window with services running
- [ ] Confirmation dialog appears
- [ ] Selecting "OK" stops services and closes
- [ ] No orphaned node.exe or python.exe processes in Task Manager
- [ ] All processes properly terminated

### Error Handling
- [ ] Stop services when already stopped (should handle gracefully)
- [ ] Start services when already running (should handle gracefully)
- [ ] Kill node.exe manually (should show error in logs)
- [ ] Port 3000 already in use (should show error)

## Packaging for Distribution

### Create Distribution Package
```bash
cd releases
zip -r FreeQwenApi-v1.0.0.zip FreeQwenApi/
# OR on Windows
# Right-click FreeQwenApi folder → Send to → Compressed folder
```

### Package Verification
- [ ] ZIP file created successfully
- [ ] ZIP size reasonable (~200-300 MB)
- [ ] Extract test: extract to new folder
- [ ] Run from extracted folder works
- [ ] All files present in extraction

### Generate Checksums
```bash
# SHA256 checksum
sha256sum FreeQwenApi-v1.0.0.zip > checksums.txt
# OR on Windows PowerShell
# Get-FileHash FreeQwenApi-v1.0.0.zip -Algorithm SHA256 > checksums.txt
```

### Documentation for End Users
- [ ] README.txt included in package
- [ ] LAUNCHER_GUIDE.md included (or linked)
- [ ] Configuration instructions clear
- [ ] Support/contact information provided

## Security Scan

### Virus Scanning
- [ ] Scan with Windows Defender
- [ ] Scan with VirusTotal (optional, for public releases)
- [ ] No false positives (or documented)
- [ ] Clean report generated

### Code Signing (Optional but Recommended)
- [ ] Obtain code signing certificate
- [ ] Sign FreeQwenApi.exe with signtool
- [ ] Verify signature
- [ ] Test signed executable

## Release Publishing

### GitHub Release (if using GitHub)
- [ ] Create new release/tag (e.g., v1.0.0)
- [ ] Upload FreeQwenApi-v1.0.0.zip
- [ ] Upload checksums.txt
- [ ] Write release notes
- [ ] Mention known issues (if any)
- [ ] Include installation instructions
- [ ] Publish release

### Release Notes Template
```markdown
## FreeQwenApi v1.0.0

### What's New
- Standalone executable with GUI
- Dual log panels
- Automatic service management

### Installation
1. Download FreeQwenApi-v1.0.0.zip
2. Extract to any folder
3. Run FreeQwenApi.exe

### Requirements
- Windows 7/8/10/11
- No Python or Node.js required

### Checksums
SHA256: [paste from checksums.txt]

### Documentation
- [User Guide](LAUNCHER_GUIDE.md)
- [Build Instructions](BUILD_INSTRUCTIONS.md)

### Known Issues
- [List any known issues]
```

## Post-Release

### Announce
- [ ] Update README.md with download link
- [ ] Post in relevant communities (if applicable)
- [ ] Update documentation site (if exists)
- [ ] Notify users/testers

### Monitor
- [ ] Watch for issue reports
- [ ] Check download statistics
- [ ] Collect user feedback
- [ ] Plan next release based on feedback

### Support
- [ ] Respond to issues
- [ ] Update FAQ based on questions
- [ ] Create troubleshooting guide
- [ ] Document common problems

## Troubleshooting Common Build Issues

### Build fails at "Download Node.js"
**Solution:**
- Check internet connection
- Verify nodejs.org is accessible
- Try manual download and place in project root

### Build fails at "npm install"
**Solution:**
- Ensure npm is in PATH
- Try `npm cache clean --force`
- Delete node_modules and retry

### PyInstaller fails
**Solution:**
- Update PyInstaller: `pip install --upgrade pyinstaller`
- Check disk space (need 2-3 GB)
- Disable antivirus temporarily
- Try clean build

### Executable doesn't run
**Solution:**
- Check antivirus quarantine
- Add exception for FreeQwenApi.exe
- Run as administrator (test only)
- Check Windows Event Viewer for errors

### Services don't start in built exe
**Solution:**
- Verify all files bundled (check spec file)
- Test in development: `python launcher.py`
- Check logs for missing dependencies
- Ensure node_modules copied correctly

## Version Numbering

Recommended scheme: **MAJOR.MINOR.PATCH**

- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes

Example progression:
- v1.0.0 - Initial release
- v1.0.1 - Bug fixes
- v1.1.0 - Add system tray feature
- v2.0.0 - Breaking API changes

## Quality Gates

Before releasing, ensure:
- [ ] ✅ All tests pass
- [ ] ✅ Manual testing complete
- [ ] ✅ No critical bugs
- [ ] ✅ Documentation accurate
- [ ] ✅ Package tested on clean machine
- [ ] ✅ Performance acceptable
- [ ] ✅ Security scan clean

## Emergency Rollback Plan

If major issues discovered post-release:

1. **Immediate:**
   - [ ] Mark release as "pre-release" or add warning
   - [ ] Document the issue prominently

2. **Short-term:**
   - [ ] Provide workaround instructions
   - [ ] Prepare hotfix release

3. **Long-term:**
   - [ ] Fix issue in code
   - [ ] Follow checklist for new release
   - [ ] Test extensively before publishing

## Continuous Improvement

After each release:
- [ ] Review what went well
- [ ] Document what could be improved
- [ ] Update this checklist with lessons learned
- [ ] Automate more steps (if possible)

## Automation Opportunities

Consider automating:
- [ ] Version number updates
- [ ] Checksum generation
- [ ] GitHub release creation
- [ ] Documentation updates
- [ ] Build validation tests
- [ ] Package upload

Example CI/CD workflow:
```yaml
# .github/workflows/release.yml
name: Build and Release

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
      - name: Run tests
        run: python test_launcher.py
      - name: Create ZIP
        run: |
          cd releases
          Compress-Archive -Path FreeQwenApi -DestinationPath FreeQwenApi-${{ github.ref_name }}.zip
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: releases/FreeQwenApi-${{ github.ref_name }}.zip
```

---

**Last Updated**: January 2024
**Version**: 1.0
**Maintained by**: Release Team
