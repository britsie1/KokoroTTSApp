import os
import sys
import time
import queue
import threading
import re
import site
import wave
import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro
import onnxruntime as ort

# --- DLL Path Helper ---

def _add_nvidia_dll_paths():
    """Helper to add NVIDIA DLL directories to the search path on Windows."""
    if os.name != 'nt':
        return
    
    site_packages = site.getsitepackages()
    # Also check user site-packages just in case
    if hasattr(site, 'getusersitepackages'):
        site_packages.append(site.getusersitepackages())
        
    for sp in site_packages:
        nvidia_dir = os.path.join(sp, 'nvidia')
        if os.path.exists(nvidia_dir):
            for root, dirs, files in os.walk(nvidia_dir):
                if 'bin' in dirs:
                    bin_dir = os.path.normpath(os.path.join(root, 'bin'))
                    os.add_dll_directory(bin_dir)
                    # For ONNX Runtime, PATH must also contain these directories
                    os.environ['PATH'] = bin_dir + os.pathsep + os.environ['PATH']

# Initialize DLL paths before any ONNX operations
_add_nvidia_dll_paths()

class KokoroEngine:
    def __init__(self, model_path="kokoro-v1.0.onnx", voices_path="voices-v1.0.bin"):
        self.provider = self._get_optimal_provider(model_path)
        print(f"[*] Initializing Kokoro with {self.provider}")
        
        # Override the environment variable for kokoro-onnx
        os.environ["ONNX_PROVIDER"] = self.provider
        
        self.kokoro = Kokoro(model_path, voices_path)
        self.voices = sorted(list(self.kokoro.get_voices()))
        
        # Audio state
        self.audio_queue = queue.Queue(maxsize=20)
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.inference_done = threading.Event()
        
        # Audio Settings
        self.volume = 1.0
        
    def _get_optimal_provider(self, model_path):
        """Checks if CUDA is actually functional, not just installed."""
        available = ort.get_available_providers()
        if "CUDAExecutionProvider" in available:
            try:
                # Use the actual model for the probe; a dummy array fails
                # because it's not a valid ONNX model.
                sess = ort.InferenceSession(
                    model_path, 
                    providers=["CUDAExecutionProvider"]
                )
                if "CUDAExecutionProvider" in sess.get_providers():
                    return "CUDAExecutionProvider"
                return "CPUExecutionProvider"
            except Exception as e:
                # This is where actual DLL errors are caught
                print(f"[!] CUDA check failed: {e}. Falling back to CPU.")
                return "CPUExecutionProvider"
        return "CPUExecutionProvider"

    def warmup(self, voice="af_sarah"):
        self.kokoro.create("Warm up", voice=voice)

    def _split_text(self, text):
        segments = []
        current_voice_tag = ""
        
        # Pattern to match tags or text
        pattern = re.compile(r'(\[.*?\])|([^\[]+)')
        
        for match in pattern.finditer(text):
            tag = match.group(1)
            content = match.group(2)
            
            if tag:
                current_voice_tag = tag
                continue
            
            if content:
                start_offset = match.start()
                # Use a single-character placeholder to keep length 1:1 for index safety
                processed_content = content
                abbrevs = ["Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.", "vs.", "etc.", "St."]
                for abbrev in abbrevs:
                    placeholder = abbrev.replace(".", "\uffff") 
                    pattern_ab = r'\b' + re.escape(abbrev)
                    processed_content = re.sub(pattern_ab, placeholder, processed_content, flags=re.IGNORECASE)
                
                # Split sentences while preserving trailing whitespace for exact indexing
                sent_pattern = re.compile(r'([^.!?\n]+[.!?\n]*[\s]*)')
                for sent_match in sent_pattern.finditer(processed_content):
                    sent_text_raw = sent_match.group(0)
                    s_start = start_offset + sent_match.start()
                    s_end = start_offset + sent_match.end()
                    
                    clean_sent = sent_text_raw.replace("\uffff", ".").strip()
                    if clean_sent:
                        segments.append({
                            "text": clean_sent,
                            "voice_tag": current_voice_tag,
                            "start": s_start,
                            "end": s_end
                        })
        return segments

    def _inference_worker(self, segments, default_voice, speed):
        active_voice = default_voice
        for seg in segments:
            if self.stop_event.is_set():
                break
            try:
                voice_tag = seg["voice_tag"]
                seg_voice = active_voice
                if voice_tag:
                    voice_match = re.search(r'\[\s*([a-zA-Z0-9_]+)\s*\]', voice_tag)
                    if voice_match:
                        requested_voice = voice_match.group(1).lower()
                        if requested_voice in self.voices:
                            seg_voice = requested_voice
                            active_voice = requested_voice
                    elif "[/]" in voice_tag:
                        seg_voice = default_voice
                        active_voice = default_voice
                
                clean_chunk = seg["text"]
                samples, sample_rate = self.kokoro.create(clean_chunk, voice=seg_voice, speed=speed)
                padding = np.zeros(int(sample_rate * 0.4), dtype=np.float32)
                samples = np.concatenate([samples, padding])
                # Add segment index and total for progress tracking
                self.audio_queue.put((samples, sample_rate, seg["start"], seg["end"], segments.index(seg), len(segments)))
            except Exception as e:
                print(f"Inference error: {e}")
        self.inference_done.set()

    def _playback_worker(self, on_finish_callback, on_segment_start_callback=None):
        while not self.stop_event.is_set():
            self.pause_event.wait()
            try:
                item = self.audio_queue.get(timeout=0.1)
                samples, sample_rate, start_idx, end_idx, seg_idx, total_segs = item
                
                if on_segment_start_callback:
                    on_segment_start_callback(start_idx, end_idx, (seg_idx + 1) / total_segs)
                
                # Apply volume scaling
                scaled_samples = samples * self.volume
                
                sd.play(scaled_samples, sample_rate)
                while sd.get_stream().active:
                    if self.stop_event.is_set():
                        sd.stop()
                        break
                    if not self.pause_event.is_set():
                        sd.stop()
                        break
                    time.sleep(0.05)
                self.audio_queue.task_done()
            except (queue.Empty, AttributeError):
                if self.inference_done.is_set():
                    break
                continue
        if on_finish_callback:
            on_finish_callback()

    def stop(self):
        self.stop_event.set()
        self.pause_event.set()
        sd.stop()
        while not self.audio_queue.empty():
            try: self.audio_queue.get_nowait()
            except: break

    def start_stream(self, text, voice, speed, on_finish_callback, on_segment_start_callback=None, start_offset=0):
        self.stop()
        time.sleep(0.1)
        self.stop_event.clear()
        self.pause_event.set()
        self.inference_done.clear()
        segments = self._split_text(text)
        if not segments: return
        
        # Filter segments to start from the given offset
        # We find the first segment that contains or is after the offset
        filtered_segments = [s for s in segments if s["end"] > start_offset]
        if not filtered_segments:
            filtered_segments = segments # Fallback if offset is at the very end
            
        threading.Thread(target=self._inference_worker, args=(filtered_segments, voice, speed), daemon=True).start()
        threading.Thread(target=self._playback_worker, args=(on_finish_callback, on_segment_start_callback), daemon=True).start()

    def export_to_file(self, text, voice, speed, file_path, progress_callback=None):
        """Generates audio and writes it to a file incrementally."""
        self.stop_event.clear()
        segments = self._split_text(text)
        if not segments:
            return False

        sample_rate = 24000
        active_voice = voice
        total = len(segments)

        try:
            with wave.open(file_path, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2) # 16-bit PCM
                wav_file.setframerate(sample_rate)

                for i, seg in enumerate(segments):
                    if self.stop_event.is_set():
                        return False
                    
                    voice_tag = seg["voice_tag"]
                    seg_voice = active_voice
                    if voice_tag:
                        voice_match = re.search(r'\[\s*([a-zA-Z0-9_]+)\s*\]', voice_tag)
                        if voice_match:
                            requested_voice = voice_match.group(1).lower()
                            if requested_voice in self.voices:
                                seg_voice = requested_voice
                                active_voice = requested_voice
                        elif "[/]" in voice_tag:
                            seg_voice = voice
                            active_voice = voice
                    
                    clean_chunk = seg["text"]
                    samples, rate = self.kokoro.create(clean_chunk, voice=seg_voice, speed=speed)
                    
                    # Convert float32 [-1, 1] to int16
                    samples_int16 = (samples * 32767).astype(np.int16)
                    wav_file.writeframes(samples_int16.tobytes())
                    
                    # Add 0.4s padding/pause
                    padding = np.zeros(int(sample_rate * 0.4), dtype=np.int16)
                    wav_file.writeframes(padding.tobytes())
                    
                    if progress_callback:
                        progress_callback((i + 1) / total)
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
