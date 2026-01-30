"""
Build script for creating a standalone .exe package of FreeQwenApi
Bundles Node.js runtime, Python runtime, and all dependencies into a single executable
"""
import os
import sys
import shutil
import subprocess
import zipfile
import urllib.request
from pathlib import Path


class ExeBuilder:
    """Builds the standalone executable"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        self.dist_dir = self.base_dir / "dist"
        self.build_dir = self.base_dir / "build"
        self.nodejs_dir = self.base_dir / "nodejs_portable"
        
        # Node.js portable version to download
        self.node_version = "v20.11.0"
        self.node_arch = "win-x64"
        self.node_url = f"https://nodejs.org/dist/{self.node_version}/node-{self.node_version}-{self.node_arch}.zip"
    
    def clean(self):
        """Clean previous build artifacts"""
        print("🧹 Cleaning previous builds...")
        
        for directory in [self.dist_dir, self.build_dir]:
            if directory.exists():
                shutil.rmtree(directory)
                print(f"   Removed {directory}")
        
        # Clean PyInstaller spec files
        for spec_file in self.base_dir.glob("*.spec"):
            spec_file.unlink()
            print(f"   Removed {spec_file}")
    
    def download_nodejs(self):
        """Download portable Node.js runtime"""
        if self.nodejs_dir.exists():
            print(f"✓ Node.js portable already exists at {self.nodejs_dir}")
            return
        
        print(f"📥 Downloading Node.js {self.node_version} for {self.node_arch}...")
        
        zip_path = self.base_dir / f"node-{self.node_version}.zip"
        
        try:
            # Download with progress
            with urllib.request.urlopen(self.node_url) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192
                
                with open(zip_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"   Progress: {percent:.1f}%", end='\r')
            
            print(f"\n✓ Downloaded Node.js ({downloaded / 1024 / 1024:.1f} MB)")
            
            # Extract
            print("📦 Extracting Node.js...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.base_dir)
            
            # Rename extracted folder
            extracted_folder = self.base_dir / f"node-{self.node_version}-{self.node_arch}"
            extracted_folder.rename(self.nodejs_dir)
            
            # Cleanup zip
            zip_path.unlink()
            
            print(f"✓ Node.js extracted to {self.nodejs_dir}")
        
        except Exception as e:
            print(f"❌ Error downloading Node.js: {e}")
            if zip_path.exists():
                zip_path.unlink()
            raise
    
    def install_node_dependencies(self):
        """Install Node.js dependencies"""
        print("📦 Installing Node.js dependencies...")
        
        node_exe = self.nodejs_dir / "node.exe"
        npm_cmd = self.nodejs_dir / "npm.cmd"
        
        if not node_exe.exists():
            print("❌ Node.js not found. Run download_nodejs first.")
            return False
        
        # Check if node_modules exists
        if (self.base_dir / "node_modules").exists():
            print("✓ node_modules already exists")
            return True
        
        try:
            # Run npm install
            result = subprocess.run(
                [str(npm_cmd), "install", "--production"],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result.returncode == 0:
                print("✓ Node.js dependencies installed")
                return True
            else:
                print(f"❌ npm install failed:\n{result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            print("❌ npm install timed out")
            return False
        except Exception as e:
            print(f"❌ Error installing Node.js dependencies: {e}")
            return False
    
    def install_python_dependencies(self):
        """Install Python dependencies"""
        print("📦 Installing Python dependencies...")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✓ Python dependencies installed")
                return True
            else:
                print(f"❌ pip install failed:\n{result.stderr}")
                return False
        
        except Exception as e:
            print(f"❌ Error installing Python dependencies: {e}")
            return False
    
    def install_playwright_browsers(self):
        """Install Playwright browsers"""
        print("📦 Installing Playwright browsers...")
        
        try:
            # Install Playwright browsers
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✓ Playwright Chromium installed")
                return True
            else:
                print(f"⚠ Playwright install warning: {result.stderr}")
                # Continue anyway as Playwright might work
                return True
        
        except Exception as e:
            print(f"⚠ Playwright install issue: {e}")
            # Continue anyway
            return True
    
    def create_pyinstaller_spec(self):
        """Create PyInstaller spec file"""
        print("📝 Creating PyInstaller spec file...")
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Collect all data files
datas = [
    ('index.js', '.'),
    ('package.json', '.'),
    ('src', 'src'),
    ('telegram_bot', 'telegram_bot'),
    ('examples', 'examples'),
    ('scripts', 'scripts'),
    ('node_modules', 'node_modules'),
    ('nodejs_portable', 'nodejs'),
    ('index.html', '.'),
]

# Hidden imports for Python dependencies
hiddenimports = [
    'telegram',
    'telegram.ext',
    'telegram.bot',
    'aiohttp',
    'playwright',
    'PIL',
    'PIL.Image',
    'requests',
    'urllib3',
    'certifi',
]

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FreeQwenApi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FreeQwenApi',
)
'''
        
        spec_file = self.base_dir / "FreeQwenApi.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"✓ Created {spec_file}")
        return spec_file
    
    def build_with_pyinstaller(self, spec_file):
        """Build executable with PyInstaller"""
        print("🔨 Building executable with PyInstaller...")
        print("   This may take several minutes...")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "PyInstaller", str(spec_file), "--clean"],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✓ PyInstaller build completed")
                
                # Check if executable exists
                exe_path = self.dist_dir / "FreeQwenApi" / "FreeQwenApi.exe"
                if exe_path.exists():
                    size_mb = exe_path.stat().st_size / 1024 / 1024
                    print(f"✓ Executable created: {exe_path} ({size_mb:.1f} MB)")
                    return True
                else:
                    print(f"❌ Executable not found at {exe_path}")
                    return False
            else:
                print(f"❌ PyInstaller failed:\n{result.stderr}")
                return False
        
        except Exception as e:
            print(f"❌ Error running PyInstaller: {e}")
            return False
    
    def create_release_package(self):
        """Create final release package with necessary runtime files"""
        print("📦 Creating release package...")
        
        release_dir = self.base_dir / "releases"
        release_dir.mkdir(exist_ok=True)
        
        # Copy dist folder contents
        dist_source = self.dist_dir / "FreeQwenApi"
        release_target = release_dir / "FreeQwenApi"
        
        if release_target.exists():
            shutil.rmtree(release_target)
        
        shutil.copytree(dist_source, release_target)
        
        # Create necessary directories
        (release_target / "uploads").mkdir(exist_ok=True)
        (release_target / "logs").mkdir(exist_ok=True)
        (release_target / "session").mkdir(exist_ok=True)
        
        # Create README
        readme_content = """# FreeQwenApi - Standalone Application

## Quick Start

1. Run `FreeQwenApi.exe`
2. The application will start both services automatically
3. View logs in the dual-panel interface

## Services

- **Node.js Proxy**: http://localhost:3000
- **Telegram Bot**: Configure in telegram_bot/.env

## Configuration

Edit configuration files in the installation directory:
- Node.js: Edit environment variables or config files in `src/`
- Telegram Bot: Edit `telegram_bot/.env` or `telegram_bot/config.py`

## Logs

Real-time logs are displayed in the application GUI.
Log files are also saved in the `logs/` directory.

## Controls

- **Start Services**: Starts both Node.js proxy and Telegram bot
- **Stop Services**: Gracefully stops both services
- **Clear Logs**: Clears the respective log panels

## Troubleshooting

If services fail to start:
1. Check the log panels for error messages
2. Ensure ports 3000 is not in use by other applications
3. Verify configuration files are properly set up
4. Check that you have internet connectivity (required for first-time Playwright setup)

## Support

For issues and questions, please refer to the main README.md or create an issue on the project repository.
"""
        
        readme_file = release_target / "README.txt"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"✓ Release package created at {release_target}")
        
        # Calculate total size
        total_size = sum(
            f.stat().st_size
            for f in release_target.rglob('*')
            if f.is_file()
        )
        print(f"   Total size: {total_size / 1024 / 1024:.1f} MB")
        
        return release_target
    
    def build(self):
        """Main build process"""
        print("=" * 60)
        print("FreeQwenApi - Executable Builder")
        print("=" * 60)
        print()
        
        steps = [
            ("Cleaning previous builds", self.clean),
            ("Downloading Node.js portable", self.download_nodejs),
            ("Installing Node.js dependencies", self.install_node_dependencies),
            ("Installing Python dependencies", self.install_python_dependencies),
            ("Installing Playwright browsers", self.install_playwright_browsers),
        ]
        
        for step_name, step_func in steps:
            print()
            print(f"Step: {step_name}")
            print("-" * 60)
            result = step_func()
            if result is False:
                print(f"\n❌ Build failed at step: {step_name}")
                return False
        
        print()
        print("Step: Creating PyInstaller spec")
        print("-" * 60)
        spec_file = self.create_pyinstaller_spec()
        
        print()
        print("Step: Building with PyInstaller")
        print("-" * 60)
        if not self.build_with_pyinstaller(spec_file):
            print("\n❌ Build failed at PyInstaller step")
            return False
        
        print()
        print("Step: Creating release package")
        print("-" * 60)
        release_path = self.create_release_package()
        
        print()
        print("=" * 60)
        print("✅ BUILD COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print(f"📦 Release package location: {release_path}")
        print(f"🚀 Executable: {release_path / 'FreeQwenApi.exe'}")
        print()
        print("You can now distribute the entire 'FreeQwenApi' folder to users.")
        print("Users just need to run FreeQwenApi.exe - no installation required!")
        print()
        
        return True


def main():
    """Main entry point"""
    builder = ExeBuilder()
    
    try:
        success = builder.build()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Build failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
