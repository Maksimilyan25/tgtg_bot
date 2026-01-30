"""
Test script to verify launcher components without actually running the GUI
"""
import sys
import os
from pathlib import Path


def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import tkinter
        print("  ✓ tkinter available")
        tkinter_available = True
    except ImportError as e:
        print(f"  ⚠ tkinter not available (expected on Linux servers): {e}")
        print("    This is OK - tkinter will be available on Windows")
        tkinter_available = False
    
    if tkinter_available:
        try:
            from tkinter import ttk, scrolledtext, messagebox
            print("  ✓ tkinter submodules available")
        except ImportError as e:
            print(f"  ❌ tkinter submodules not available: {e}")
            return False
    
    try:
        import subprocess
        import threading
        import queue
        import signal
        import time
        from datetime import datetime
        print("  ✓ Standard library modules available")
    except ImportError as e:
        print(f"  ❌ Standard library modules missing: {e}")
        return False
    
    return True


def test_launcher_structure():
    """Test that launcher.py has correct structure"""
    print("\nTesting launcher.py structure...")
    
    try:
        # Check file syntax without importing (since tkinter may not be available)
        launcher_path = Path(__file__).parent / 'launcher.py'
        
        with open(launcher_path, 'r') as f:
            content = f.read()
        
        # Check for required classes and functions
        required_elements = [
            'class ServiceManager:',
            'class LauncherGUI:',
            'def main():',
            'def start_services',
            'def stop_services',
        ]
        
        for element in required_elements:
            if element in content:
                print(f"  ✓ Found {element}")
            else:
                print(f"  ❌ Missing {element}")
                return False
        
        # Try to compile
        compile(content, 'launcher.py', 'exec')
        print("  ✓ launcher.py syntax is valid")
        
        return True
    
    except SyntaxError as e:
        print(f"  ❌ Syntax error in launcher.py: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error checking launcher: {e}")
        return False


def test_build_script():
    """Test that build_exe.py has correct structure"""
    print("\nTesting build_exe.py structure...")
    
    try:
        import build_exe
        
        if not hasattr(build_exe, 'ExeBuilder'):
            print("  ❌ ExeBuilder class not found")
            return False
        print("  ✓ ExeBuilder class exists")
        
        builder = build_exe.ExeBuilder()
        
        # Check for required methods
        required_methods = [
            'clean', 'download_nodejs', 'install_node_dependencies',
            'install_python_dependencies', 'create_pyinstaller_spec',
            'build_with_pyinstaller', 'create_release_package', 'build'
        ]
        
        for method in required_methods:
            if not hasattr(builder, method):
                print(f"  ❌ Method {method} not found")
                return False
        
        print(f"  ✓ All {len(required_methods)} required methods exist")
        return True
    
    except Exception as e:
        print(f"  ❌ Error importing build_exe: {e}")
        return False


def test_file_structure():
    """Test that all required files exist"""
    print("\nTesting file structure...")
    
    base_dir = Path(__file__).parent
    
    required_files = [
        'launcher.py',
        'build_exe.py',
        'build.bat',
        'run_gui.py',
        'BUILD_INSTRUCTIONS.md',
        'LAUNCHER_GUIDE.md',
        'index.js',
        'package.json',
        'telegram_bot/bot.py',
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = base_dir / file_path
        if full_path.exists():
            print(f"  ✓ {file_path} exists")
        else:
            print(f"  ❌ {file_path} missing")
            all_exist = False
    
    return all_exist


def test_gitignore():
    """Test that .gitignore includes build artifacts"""
    print("\nTesting .gitignore...")
    
    gitignore_path = Path(__file__).parent / '.gitignore'
    
    if not gitignore_path.exists():
        print("  ❌ .gitignore not found")
        return False
    
    with open(gitignore_path, 'r') as f:
        content = f.read()
    
    required_patterns = ['build/', 'dist/', 'releases/', '*.spec', 'nodejs_portable/']
    
    all_found = True
    for pattern in required_patterns:
        if pattern in content:
            print(f"  ✓ .gitignore includes {pattern}")
        else:
            print(f"  ❌ .gitignore missing {pattern}")
            all_found = False
    
    return all_found


def main():
    """Run all tests"""
    print("=" * 60)
    print("FreeQwenApi Launcher - Component Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("Import availability", test_imports),
        ("Launcher structure", test_launcher_structure),
        ("Build script structure", test_build_script),
        ("File structure", test_file_structure),
        (".gitignore configuration", test_gitignore),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    print()
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("✅ All tests passed!")
        print()
        print("Next steps:")
        print("  1. Build the executable: python build_exe.py")
        print("  2. Test in dev mode: python launcher.py")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
