"""
Quick launcher for testing the GUI in development mode
(without building the .exe)
"""
import sys
import subprocess

if __name__ == "__main__":
    print("Starting FreeQwenApi GUI in development mode...")
    print("Note: This runs the GUI without building the .exe")
    print("For production, use build_exe.py to create the standalone .exe")
    print()
    
    # Just run the launcher directly
    subprocess.run([sys.executable, "launcher.py"])
