import os
import requests
from tqdm import tqdm

MODELS = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
}

def download_file(url, filename, progress_callback=None):
    """Downloads a file with optional progress reporting."""
    print(f"Downloading {filename} from {url}...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        downloaded = 0
        with open(filename, 'wb') as file:
            for data in response.iter_content(chunk_size=8192):
                size = file.write(data)
                downloaded += size
                if progress_callback and total_size > 0:
                    progress_callback(filename, downloaded / total_size)
                    
        print(f"Successfully downloaded {filename}")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        if os.path.exists(filename):
            os.remove(filename)
        raise

def ensure_models(progress_callback=None):
    """Checks if models exist and downloads them if missing."""
    for filename, url in MODELS.items():
        if not os.path.exists(filename) or os.path.getsize(filename) < 1024 * 1024:
            if progress_callback:
                progress_callback(f"Downloading {filename}...", 0)
            download_file(url, filename, progress_callback)
        else:
            print(f"[*] {filename} found.")
            if progress_callback:
                progress_callback(f"{filename} found.", 1.0)

if __name__ == "__main__":
    ensure_models()
