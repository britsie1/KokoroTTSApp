# Kokoro TTS Streamer

A high-performance, real-time Text-to-Speech (TTS) application built with Python, [Kokoro-ONNX](https://github.com/thewh1teagle/kokoro-onnx), and CustomTkinter. This app features a built-in bootstrapper that automatically handles dependency installation and model downloads on the first run.

## Features
- **Real-time Streaming:** Hear audio as it's being generated.
- **Visual Feedback:** Highlights the text currently being spoken.
- **Export to WAV:** Save your generated audio to a file.
- **Multiple Voices:** Support for all Kokoro v1.0 voices (e.g., `af_sarah`, `am_michael`).
- **Self-Healing Setup:** Automatically detects missing models or libraries and fixes the environment.

## Demo

<div align="left">
  <video src="https://github.com/britsie1/KokoroTTSApp/blob/main/Demo.mp4" controls width="400"></video>
  <br>
  <a href="https://github.com/britsie1/KokoroTTSApp/blob/main/Demo.mp4">📥 Download Demo.mp4</a>
</div>

**Voice Sample Script:**
```text
[am_adam] This is a test of my voice changing capabilities [/]
[af_sarah] from a young and energetic woman [/]
[em_santa] to an old man with wisdom in his voice [/]
[ff_siwis] I can even do some accents, as sweet as a French baguette [/]
[zf_xiaoxiao] or as tasty as a steaming hot ramen bowl [/]
```

---

## Getting Started (Manual Run)

If you have Python installed, you can run the application directly from the source code.

1. **Clone or Download** this repository.
2. **Open a terminal** in the project folder.
3. **Run the application:**
   ```bash
   python main.py
   ```

**Note:** On the first launch, a "Setup" window will appear. It will automatically:
- Install required libraries (via `pip`).
- Download the ~310MB model files (`kokoro-v1.0.onnx` and `voices-v1.0.bin`).
- Once finished, the main GUI will open automatically.

---

## Building an Executable (.exe)

You can package this application into a single runnable file that doesn't require the user to manually install Python or manage libraries.

1. **Run the build script:**
   ```bash
   python build.py
   ```
2. **Find your app:** After the process completes, look in the `dist/` folder for `Kokoro-TTS.exe`.
3. **Distribute:** You can share this `.exe` file. It **does not** include the large model files by default (to keep the initial download small); it will download them on the user's machine during the first launch.

---

## Core Components
- **`main.py`**: The entry point containing the Bootstrapper and the main GUI.
- **`engine.py`**: The TTS engine logic using ONNX Runtime.
- **`download_models.py`**: Helper script for fetching AI assets.
- **`requirements.txt`**: List of Python dependencies.

## Acknowledgments
This project is powered by the [Kokoro TTS](https://huggingface.co/hexgrad/Kokoro-82M) model and the [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) wrapper.
