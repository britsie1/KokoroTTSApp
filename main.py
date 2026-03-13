import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk

# --- Bootstrapping GUI ---

class BootstrapGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Kokoro TTS Setup")
        self.root.geometry("400x180")
        self.root.resizable(False, False)
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        self.label = tk.Label(self.root, text="Initializing Kokoro TTS...", pady=20, font=("Helvetica", 11, "bold"))
        self.label.pack()
        
        self.progress = ttk.Progressbar(self.root, length=300, mode='determinate')
        self.progress.pack(pady=10)
        
        self.status = tk.Label(self.root, text="Preparing...", font=("Helvetica", 9), fg="gray")
        self.status.pack()

        self.success = False
        threading.Thread(target=self.run_bootstrap, daemon=True).start()
        self.root.mainloop()

    def update_ui(self, text, progress_val, status_text=""):
        self.root.after(0, lambda: self._update(text, progress_val, status_text))

    def _update(self, text, progress_val, status_text):
        if text: self.label.config(text=text)
        self.progress['value'] = progress_val * 100
        if status_text: self.status.config(text=status_text)

    def run_bootstrap(self):
        try:
            # 1. Install Requirements (Only if running as script)
            if not getattr(sys, 'frozen', False) and os.path.exists("requirements.txt"):
                self.update_ui("Installing dependencies...", 0.1, "This may take a moment on first run")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet", "--disable-pip-version-check"])
                import importlib
                importlib.invalidate_caches()
            else:
                self.update_ui("Starting setup...", 0.1, "Bundled environment detected")

            # 2. Download Models
            self.update_ui("Checking models...", 0.4, "Verifying model files")
            # We import here because download_models depends on requests/tqdm
            from download_models import ensure_models
            
            def model_progress(filename, percent):
                ui_percent = 0.4 + (percent * 0.6)
                self.update_ui("Downloading Models...", ui_percent, f"Fetching {filename}...")

            ensure_models(progress_callback=model_progress)
            
            self.update_ui("Environment Ready!", 1.0, "Launching Kokoro TTS...")
            self.success = True
            self.root.after(1000, self.root.destroy)
            
        except Exception as e:
            self.update_ui("Setup Failed", 0, f"Error: {str(e)}")
            print(f"[!] Bootstrap Error: {e}")

# Run the bootstrap before anything else
bootstrap_gui = BootstrapGUI()
if not bootstrap_gui.success:
    sys.exit(1)

# --- Main Application Imports ---
# Now safe to import non-standard libraries
import sounddevice as sd
import customtkinter as ctk
from engine import KokoroEngine

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Kokoro TTS Streamer")
        self.geometry("800x600")
        ctk.set_appearance_mode("Dark")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.loading_frame = ctk.CTkFrame(self)
        self.loading_frame.grid(row=0, column=0, sticky="nsew")
        self.loading_frame.grid_columnconfigure(0, weight=1)
        self.loading_frame.grid_rowconfigure((0,1), weight=1)
        
        self.load_label = ctk.CTkLabel(self.loading_frame, text="Initializing Kokoro TTS...\n(Checking hardware & warming up)", font=("Helvetica", 18))
        self.load_label.grid(row=0, column=0, pady=(100, 20))
        
        self.progress = ctk.CTkProgressBar(self.loading_frame, orientation="horizontal", width=400)
        self.progress.grid(row=1, column=0, pady=(0, 100))
        self.progress.set(0)
        self.progress.start()
        
        self.main_frame = ctk.CTkFrame(self)
        self.setup_main_ui()
        self.engine = None
        threading.Thread(target=self.init_engine, daemon=True).start()

    def init_engine(self):
        try:
            self.engine = KokoroEngine()
            self.engine.warmup()
            self.after(0, self.show_main_ui)
        except Exception as e:
            self.after(0, lambda: self.load_label.configure(text=f"Error loading models:\n{e}", text_color="red"))

    def show_main_ui(self):
        self.loading_frame.grid_forget()
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.voice_combo.configure(values=self.engine.voices)
        self.voice_combo.set("af_sarah")
        self.status_label.configure(text=f"Engine: {self.engine.provider}")

    def setup_main_ui(self):
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        self.label = ctk.CTkLabel(self.main_frame, text="Kokoro High-Performance TTS", font=("Helvetica", 24, "bold"))
        self.label.grid(row=0, column=0, pady=(0, 20), sticky="w")
        
        self.textbox = ctk.CTkTextbox(self.main_frame, font=("Helvetica", 14), wrap="word")
        self.textbox.grid(row=1, column=0, sticky="nsew", pady=(0, 20))
        self.textbox.insert("1.0", """[am_adam] This is a test of my voice changing capabilities [/]
[af_sarah] from a young and energetic woman [/]
[em_santa] to an old man with wisdom in his voice [/]
[ff_siwis] I can even do some accents, as sweet as a French baguette [/]
[zf_xiaoxiao] or as tasty as a steaming hot ramen bowl [/]""")
        
        self.ctrl_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.ctrl_frame.grid(row=2, column=0, sticky="ew")
        self.ctrl_frame.grid_columnconfigure((1,3,5), weight=1)
        
        self.voice_label = ctk.CTkLabel(self.ctrl_frame, text="Voice:")
        self.voice_label.grid(row=0, column=0, padx=5, sticky="e")
        self.voice_combo = ctk.CTkComboBox(self.ctrl_frame, values=["Loading..."])
        self.voice_combo.grid(row=0, column=1, padx=5, sticky="w")
        
        self.speed_label = ctk.CTkLabel(self.ctrl_frame, text="Speed: 1.0x")
        self.speed_label.grid(row=0, column=2, padx=5, sticky="e")
        self.speed_slider = ctk.CTkSlider(self.ctrl_frame, from_=0.5, to=2.0, number_of_steps=15, command=self.update_speed_label, width=150)
        self.speed_slider.grid(row=0, column=3, padx=5, sticky="w")
        self.speed_slider.set(1.0)

        self.vol_label = ctk.CTkLabel(self.ctrl_frame, text="Vol: 100%")
        self.vol_label.grid(row=0, column=4, padx=5, sticky="e")
        self.vol_slider = ctk.CTkSlider(self.ctrl_frame, from_=0, to=1.5, number_of_steps=30, command=self.update_volume, width=150)
        self.vol_slider.grid(row=0, column=5, padx=5, sticky="w")
        self.vol_slider.set(1.0)
        
        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.grid(row=3, column=0, pady=(20, 0))
        
        self.play_btn = ctk.CTkButton(self.btn_frame, text="▶ Play", command=self.on_play, width=120)
        self.play_btn.grid(row=0, column=0, padx=10)
        
        self.pause_btn = ctk.CTkButton(self.btn_frame, text="⏸ Pause", command=self.on_pause, width=120, state="disabled")
        self.pause_btn.grid(row=0, column=1, padx=10)
        
        self.stop_btn = ctk.CTkButton(self.btn_frame, text="⏹ Stop", command=self.on_stop, width=120, fg_color="#A12", hover_color="#800")
        self.stop_btn.grid(row=0, column=2, padx=10)

        self.export_btn = ctk.CTkButton(self.btn_frame, text="💾 Export (.wav)", command=self.on_export, width=120, fg_color="#282", hover_color="#161")
        self.export_btn.grid(row=0, column=3, padx=10)

        self.status_label = ctk.CTkLabel(self.main_frame, text="Engine: Detecting...", font=("Helvetica", 10))
        self.status_label.grid(row=5, column=0, sticky="e")

        self.main_progress = ctk.CTkProgressBar(self.main_frame, orientation="horizontal")
        self.main_progress.set(0)

        # File Operations Frame
        self.file_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.file_frame.grid(row=0, column=0, sticky="e")
        
        self.open_btn = ctk.CTkButton(self.file_frame, text="📂 Open", command=self.on_open_file, width=80, fg_color="#444")
        self.open_btn.grid(row=0, column=0, padx=5)
        
        self.save_btn = ctk.CTkButton(self.file_frame, text="💾 Save", command=self.on_save_file, width=80, fg_color="#444")
        self.save_btn.grid(row=0, column=1, padx=5)

        # Highlighting tag configuration
        self.textbox.tag_config("highlight", background="#440", foreground="white")

    def on_open_file(self):
        file_path = ctk.filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.textbox.delete("1.0", "end")
                self.textbox.insert("1.0", content)
                self.status_label.configure(text=f"Loaded: {os.path.basename(file_path)}")

    def on_save_file(self):
        file_path = ctk.filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            content = self.textbox.get("1.0", "end-1c")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                self.status_label.configure(text=f"Saved: {os.path.basename(file_path)}")

    def update_speed_label(self, val):
        self.speed_label.configure(text=f"Speed: {val:.1f}x")

    def update_volume(self, val):
        if self.engine:
            self.engine.volume = float(val)
            self.vol_label.configure(text=f"Volume: {int(val*100)}%")

    def highlight_text(self, start, end, progress):
        self.after(0, lambda: self._do_highlight(start, end, progress))

    def _do_highlight(self, start, end, progress):
        self.textbox.tag_remove("highlight", "1.0", "end")
        start_idx = f"1.0 + {start} chars"
        end_idx = f"1.0 + {end} chars"
        self.textbox.tag_add("highlight", start_idx, end_idx)
        self.textbox.see(start_idx)
        self.main_progress.set(progress)

    def _reset_export_ui(self):
        self.export_btn.configure(state="normal")
        self.main_progress.grid_forget()
        self.main_progress.set(0)
        self.status_label.configure(text=f"Engine: {self.engine.provider}", text_color="white")

    def on_export(self):
        text = self.textbox.get("1.0", "end-1c").strip()
        if not text: return
        
        file_path = ctk.filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav")],
            title="Export Audio"
        )
        if not file_path: return

        self.export_btn.configure(state="disabled")
        self.main_progress.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        self.status_label.configure(text="Exporting...")
        
        def do_export():
            try:
                success = self.engine.export_to_file(
                    text, 
                    self.voice_combo.get(), 
                    self.speed_slider.get(),
                    file_path,
                    progress_callback=lambda p: self.after(0, lambda: self.main_progress.set(p))
                )
                if success:
                    self.after(0, lambda: self.status_label.configure(text="Export Complete!", text_color="green"))
                else:
                    self.after(0, lambda: self.status_label.configure(text="Export Cancelled/Failed", text_color="yellow"))
            except Exception as e:
                self.after(0, lambda: self.status_label.configure(text=f"Export Error: {e}", text_color="red"))
            finally:
                self.after(2000, self._reset_export_ui)

        threading.Thread(target=do_export, daemon=True).start()

    def on_play(self):
        text = self.textbox.get("1.0", "end-1c") # Remove .strip() to keep indices exact
        if not text.strip(): return
        if not self.engine.pause_event.is_set():
            self.engine.pause_event.set()
            self.play_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal")
            return
        
        self.main_progress.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        self.play_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        
        # Get start offset from cursor position
        cursor_pos = self.textbox.index("insert") # e.g. "5.10"
        line, col = map(int, cursor_pos.split("."))
        # Convert line.col to flat character offset
        start_offset = len(self.textbox.get("1.0", f"{line}.0")) + col
        
        self.engine.start_stream(text, self.voice_combo.get(), self.speed_slider.get(), self.on_playback_finished, self.highlight_text, start_offset=start_offset)

    def on_pause(self):
        if self.engine.pause_event.is_set():
            self.engine.pause_event.clear()
            self.play_btn.configure(state="normal", text="▶ Resume")
            self.pause_btn.configure(state="disabled")
            sd.stop()

    def on_stop(self):
        self.engine.stop()
        self.on_playback_finished()

    def on_playback_finished(self):
        self.after(0, self._reset_btns)
        self.after(0, lambda: self.textbox.tag_remove("highlight", "1.0", "end"))
        self.after(0, lambda: self.main_progress.grid_forget())
        self.after(0, lambda: self.main_progress.set(0))

    def _reset_btns(self):
        self.play_btn.configure(state="normal", text="▶ Play")
        self.pause_btn.configure(state="disabled")

if __name__ == "__main__":
    app = App()
    app.mainloop()
