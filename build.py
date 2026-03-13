import os
import sys
import subprocess
import shutil

def build():
    print("[*] Starting Kokoro TTS Build Process...")
    
    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Define build command
    # --onefile: Create a single executable
    # --noconsole: Don't show terminal when running (optional, but good for GUI)
    # --name: Name of the output file
    # --add-data: Include requirements.txt in the bundle (optional)
    # --hidden-import: Ensure dynamic imports are caught
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name=Kokoro-TTS",
        "--clean",
        # We don't add models or voices here - the bootstrapper will download them
        "main.py"
    ]

    print(f"[*] Running command: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("\n" + "="*50)
        print("[SUCCESS] Build complete!")
        print(f"[INFO] Your executable is in the 'dist' folder: dist/Kokoro-TTS.exe")
        print("[INFO] You can distribute this .exe without the model files.")
        print("[INFO] On first run, it will download the models automatically.")
        print("="*50)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Build failed with code {e.returncode}")

if __name__ == "__main__":
    build()
