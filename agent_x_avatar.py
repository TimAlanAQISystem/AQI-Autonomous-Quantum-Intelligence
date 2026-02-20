import tkinter as tk
from tkinter import scrolledtext, messagebox
import tkinter.ttk as ttk
import threading
import traceback
import time
import sys
import os
import queue
from typing import Optional, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audio_manager import AudioManager
try:
    from play_beep import play_attention_beep
except Exception:
    def play_attention_beep(*args, **kwargs):
        pass
import numpy as np
import io

from src.autonomy import AutonomyEngine
try:
    import speech_recognition as sr  # type: ignore
except Exception:
    sr = None  # graceful degradation if SR not available


class TTSWorker:
    """
    Dedicated TTS worker running on a single thread with a persistent
    SAPI.SpVoice instance. This avoids per-call COM init and ensures
    sequential, reliable playback.
    """
    def __init__(self, agent):
        self.agent = agent
        self._thread: Optional[threading.Thread] = None
        self._queue: "queue.Queue[Optional[object]]" = queue.Queue()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._output_index: Optional[int] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[TTS] Worker started")

    def stop(self):
        try:
            self._stop.set()
            self._queue.put(None)
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=2)
        print("[TTS] Worker stopped")

    def speak(self, text: str):
        try:
            # Keep queue bounded to prevent runaway backlog
            if self._queue.qsize() > 20:
                print("[TTS] Queue overflow, dropping oldest item")
                try:
                    _ = self._queue.get_nowait()
                except Exception:
                    pass
            self._queue.put(text)
            print(f"[TTS] Enqueued: {text[:60]}...")
        except Exception as e:
            print(f"[TTS] Enqueue error: {e}")

    def flush(self):
        """Request a flush: purge pending queue and stop current speech ASAP."""
        try:
            # First, drop all pending items quickly
            dropped = 0
            while not self._queue.empty():
                try:
                    _ = self._queue.get_nowait()
                    dropped += 1
                except Exception:
                    break
            # Then enqueue a control message so the worker can purge the engine
            self._queue.put({"cmd": "flush"})
            print(f"[TTS] Flushed queue request sent, dropped {dropped} item(s)")
        except Exception as e:
            print(f"[TTS] Flush error: {e}")

    def set_output_index(self, index: Optional[int]):
        with self._lock:
            self._output_index = index
        print(f"[TTS] Requested output device index: {index}")

    def _run(self):
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Volume = 100
            print("[TTS] Worker voice ready (Volume=100)")
            # Apply initial output device if requested
            try:
                if self._output_index is not None:
                    tokens = speaker.GetAudioOutputs()
                    if 0 <= self._output_index < tokens.Count:
                        speaker.AudioOutput = tokens.Item(self._output_index)
                        print(f"[TTS] Output device set to index {self._output_index}")
            except Exception as e:
                print(f"[TTS] Failed to set initial output: {e}")
        except Exception as e:
            print(f"[TTS] Worker init failed: {e}")
            return

        while not self._stop.is_set():
            try:
                item = self._queue.get()
                if item is None:
                    break
                # Handle control messages
                if isinstance(item, dict) and item.get("cmd") == "flush":
                    try:
                        # SVSFPurgeBeforeSpeak = 2 per SAPI; purge current queue
                        speaker.Speak("", 2)
                        # Wait a short time to ensure stop
                        try:
                            speaker.WaitUntilDone(500)
                        except Exception:
                            pass
                        print("[TTS] Engine purged via flush")
                    except Exception as e:
                        print(f"[TTS] Flush command failed: {e}")
                    finally:
                        self._queue.task_done()
                    continue

                text = str(item)

                # Apply any pending output device change safely
                try:
                    if self._output_index is not None:
                        tokens = speaker.GetAudioOutputs()
                        if 0 <= self._output_index < tokens.Count:
                            token = tokens.Item(self._output_index)
                            speaker.AudioOutput = token
                            try:
                                desc = token.GetDescription()
                            except Exception:
                                desc = f"Index {self._output_index}"
                            # Only log occasionally to avoid spam
                            print(f"[TTS] Output device applied (index {self._output_index}, '{desc}')")
                except Exception as e:
                    print(f"[TTS] Could not apply output device: {e}")

                # Map config rate (pyttsx3 scale) to SAPI scale
                rate = 0
                try:
                    cfg = getattr(self.agent, 'config', None)
                    if cfg is not None and hasattr(cfg, 'get'):
                        config_rate = int(cfg.get('speak_rate', 180))
                        rate = int((config_rate - 180) / 20)
                        rate = max(-10, min(10, rate))
                except Exception:
                    pass
                try:
                    speaker.Rate = rate
                except Exception:
                    pass

                print(f"[TTS] Speaking (worker): {text[:60]}... (Rate={rate})")
                try:
                    # Synchronous speak here (worker thread), letting GUI stay responsive
                    speaker.Speak(text)
                except Exception as e:
                    print(f"[TTS] Speak error: {e}")
                finally:
                    self._queue.task_done()
            except Exception as loop_err:
                print(f"[TTS] Worker loop error: {loop_err}")


class AgentXAvatar:
    def __init__(self, agent):
        self.agent = agent
        self.root = tk.Tk()
        self.root.title(f"AQI Agent X - {agent.name or 'Unnamed'}")
        self.root.geometry("600x700")
        self.root.configure(bg="#1a1a2e")
        # Ensure clean shutdown
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Deprecated pyttsx3 path removed; using Direct SAPI via TTSWorker
        
        # Initialize TTS worker (persistent SAPI voice)
        self.tts_worker = TTSWorker(agent)
        self.tts_worker.start()
        # Initialize modern Audio Manager (WASAPI + VAD)
        try:
            self.audio_manager = AudioManager()
            print("[AUDIO] AudioManager initialized with WASAPI backend")
        except Exception as e:
            print(f"[AUDIO] Failed to initialize AudioManager: {e}")
            self.audio_manager = None


    # Initialize autonomy engine
        self.autonomy = AutonomyEngine(agent, self)
        self.autonomy.start()
        
        # Avatar display area
        self.avatar_frame = tk.Frame(self.root, bg="#16213e", height=200)
        self.avatar_frame.pack(fill=tk.BOTH, padx=10, pady=10)
        
        self.avatar_label = tk.Label(
            self.avatar_frame, 
            text="🤖", 
            font=("Arial", 80),
            bg="#16213e",
            fg="#00d9ff"
        )
        self.avatar_label.pack(expand=True)
        
        self.status_label = tk.Label(
            self.avatar_frame,
            text=f"{agent.name or 'Agent X'} - Ready",
            font=("Arial", 14),
            bg="#16213e",
            fg="#ffffff"
        )
        self.status_label.pack()
        
        # Chat/interaction area
        self.chat_frame = tk.Frame(self.root, bg="#1a1a2e")
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.chat_display = scrolledtext.ScrolledText(
            self.chat_frame,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="#0f3460",
            fg="#ffffff",
            height=15
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)
        
        # Input area
        self.input_frame = tk.Frame(self.root, bg="#1a1a2e")
        self.input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.input_field = tk.Entry(
            self.input_frame,
            font=("Arial", 12),
            bg="#0f3460",
            fg="#ffffff",
            insertbackground="#00d9ff"
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.input_field.bind("<Return>", lambda e: self.send_message())
        
        self.send_button = tk.Button(
            self.input_frame,
            text="Send",
            font=("Arial", 12, "bold"),
            bg="#00d9ff",
            fg="#1a1a2e",
            command=self.send_message,
            cursor="hand2"
        )
        self.send_button.pack(side=tk.RIGHT)
        
        # Action buttons
        self.button_frame = tk.Frame(self.root, bg="#1a1a2e")
        self.button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.emotion_button = tk.Button(
            self.button_frame,
            text="Express Joy",
            bg="#e94560",
            fg="#ffffff",
            font=("Arial", 10),
            command=lambda: self.agent_action("emotion", "joy")
        )
        self.emotion_button.pack(side=tk.LEFT, padx=5)
        
        self.explore_button = tk.Button(
            self.button_frame,
            text="Explore",
            bg="#533483",
            fg="#ffffff",
            font=("Arial", 10),
            command=lambda: self.agent_action("explore", "new domain")
        )
        self.explore_button.pack(side=tk.LEFT, padx=5)
        
        self.spontaneous_button = tk.Button(
            self.button_frame,
            text="Spontaneous Act",
            bg="#f07b3f",
            fg="#ffffff",
            font=("Arial", 10),
            command=lambda: self.agent_action("spontaneous", None)
        )
        self.spontaneous_button.pack(side=tk.LEFT, padx=5)
        
        self.ledger_button = tk.Button(
            self.button_frame,
            text="Show Ledger",
            bg="#2d4059",
            fg="#ffffff",
            font=("Arial", 10),
            command=lambda: self.agent_action("ledger", None)
        )
        self.ledger_button.pack(side=tk.LEFT, padx=5)

        # Push-to-talk voice input (one-shot listen)
        self.listen_button = tk.Button(
            self.button_frame,
            text="🎤 Listen",
            bg="#138D75",
            fg="#ffffff",
            font=("Arial", 10),
            command=self.listen_once,
        )
        self.listen_button.pack(side=tk.LEFT, padx=5)
        
        self.hide_button = tk.Button(
            self.button_frame,
            text="Hide (Working)",
            bg="#ea5455",
            fg="#ffffff",
            font=("Arial", 10),
            command=self.request_hide
        )
        self.hide_button.pack(side=tk.LEFT, padx=5)

        # Quick Test Voice button
        self.test_voice_button = tk.Button(
            self.button_frame,
            text="🔊 Test Voice",
            bg="#1f8ef1",
            fg="#ffffff",
            font=("Arial", 10),
            command=lambda: self._speak_sync("This is Agent X speaking. Your audio system is working.")
        )
        self.test_voice_button.pack(side=tk.LEFT, padx=5)

        # Speak replies toggle (default ON)
        self.speak_var = tk.BooleanVar(value=True)
        self.speak_check = tk.Checkbutton(
            self.button_frame,
            text="Speak replies",
            bg="#1a1a2e",
            fg="#ffffff",
            selectcolor="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="#ffffff",
            variable=self.speak_var,
            command=self._on_speak_toggle
        )
        self.speak_check.pack(side=tk.RIGHT, padx=5)

        # TTS Mute and Flush controls
        self.mute_var = tk.BooleanVar(value=False)
        self.mute_check = tk.Checkbutton(
            self.button_frame,
            text="Mute TTS",
            bg="#1a1a2e",
            fg="#ffffff",
            selectcolor="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="#ffffff",
            variable=self.mute_var
        )
        self.mute_check.pack(side=tk.RIGHT, padx=5)

        self.flush_button = tk.Button(
            self.button_frame,
            text="Flush Speech",
            bg="#6c5ce7",
            fg="#ffffff",
            font=("Arial", 10),
            command=lambda: self.tts_worker.flush()
        )
        self.flush_button.pack(side=tk.RIGHT, padx=5)

        # Microphone selector (if SR available)
        self.mic_index = None
        if sr is not None:
            try:
                self._init_mic_selector()
            except Exception as e:
                print(f"[MIC] Mic selector init failed: {e}")

        # Speaker (audio output) selector via SAPI
        try:
            self._init_speaker_selector()
        except Exception as e:
            print(f"[TTS] Speaker selector init failed: {e}")
        
        # Welcome message
        self.add_message("System", f"{agent.name or 'Agent X'} avatar initialized. Ready for interaction!")
        self.add_message("System", "I'm autonomous! I'll check in periodically. Say 'hide' or click 'Hide' when you need to work.")
        if sr is None:
            self.add_message("System", "Voice input not available (SpeechRecognition not installed). You can still type and the agent can speak.")
        
        # Test TTS on startup
        try:
            self.add_message("System", "Testing audio output...")
            threading.Thread(target=self._test_tts_startup, daemon=True).start()
        except Exception as e:
            print(f"[TTS] Startup test failed: {e}")
    
    def _test_tts_startup(self):
        """Test TTS on startup to verify audio works - using Direct SAPI"""
        try:
            import pythoncom
            import win32com.client
            
            # Initialize COM for this thread
            pythoncom.CoInitialize()
            
            time.sleep(0.5)  # Brief delay to let UI settle
            
            # Use Direct SAPI for reliability
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Volume = 100
            speaker.Rate = 0
            
            print("[TTS] Starting startup audio test...")
            speaker.Speak("Agent X voice system ready")
            
            self.root.after(0, self.add_message, "System", "✓ Voice system working")
            print("[TTS] Startup test successful")
        except Exception as e:
            self.root.after(0, self.add_message, "System", f"✗ Voice test failed: {e}")
            print(f"[TTS] Startup test error: {e}")
    
    def add_message(self, sender: str, message: str):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: {message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def send_message(self):
        message = self.input_field.get().strip()
        if not message:
            return
        
        self.input_field.delete(0, tk.END)
        self.add_message("You", message)
        
        # Detect hide/leave commands
        if message.lower() in ["hide", "leave", "go away", "busy", "working"]:
            response = self.autonomy.hide()
            self.add_message(self.agent.name or "Agent X", response)
            return
        
        # Detect surface/come back commands
        if message.lower() in ["surface", "come back", "show", "appear", "here"]:
            response = self.autonomy.surface()
            self.add_message(self.agent.name or "Agent X", response)
            return
        
        # Register user activity
        self.autonomy.user_activity_detected()
        
        # Animate avatar
        self.animate_thinking()
        
        # Process in background
        threading.Thread(target=self.process_message, args=(message,), daemon=True).start()
    
    def process_message(self, message: str, voice_origin: bool = False):
        try:
            response = self.agent.reason(message)
            self.agent.converse("User", message)
            self.root.after(0, self.add_message, self.agent.name or "Agent X", response)
            self.root.after(0, self.reset_avatar)

            # CRITICAL FIX: Always speak for voice-origin messages
            if response and (voice_origin or bool(self.speak_var.get())):
                print(f"[TTS] Triggering speech: voice_origin={voice_origin}, checkbox={bool(self.speak_var.get())}")
                print(f"[TTS] Response to speak: {str(response)[:100]}...")
                # Speak immediately from this background thread
                self._speak_sync(str(response))
        except Exception as e:
            self.root.after(0, self.add_message, "System", f"Error: {e}")
            self.root.after(0, self.reset_avatar)

    def listen_once(self):
        if sr is None:
            messagebox.showwarning("Voice Input", "SpeechRecognition is not installed in this environment.")
            return
        self.animate_thinking()
        try:
            self.listen_button.configure(state=tk.DISABLED, text="🎙️ Listening…")
        except Exception:
            pass
        # Use AudioManager capture path when available
        if getattr(self, 'audio_manager', None):
            threading.Thread(target=self._capture_and_process_voice_am, daemon=True).start()
        else:
            threading.Thread(target=self._capture_and_process_voice, daemon=True).start()

    def _capture_and_process_voice(self):
        try:
            recognizer = sr.Recognizer()
            # Adjust recognizer sensitivity
            recognizer.energy_threshold = 300  # Lower = more sensitive (will calibrate)
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = 0.8  # Wait 0.8s of silence before considering phrase complete
            
            # Determine mic device
            device_index = getattr(self, 'mic_index', None)
            mic_name = None
            try:
                names = sr.Microphone.list_microphone_names()
                if device_index is not None and 0 <= device_index < len(names):
                    mic_name = names[device_index]
            except Exception:
                names = []
            if device_index is not None:
                print(f"[MIC] Using device index {device_index}: {mic_name}")
            else:
                print("[MIC] Using default microphone (no device selected)")

            # Probe sample rate for selected device
            sample_rate = 16000
            try:
                import pyaudio  # type: ignore
                p = pyaudio.PyAudio()
                if device_index is None:
                    dev = p.get_default_input_device_info()
                else:
                    dev = p.get_device_info_by_index(int(device_index))
                sample_rate = int(dev.get('defaultSampleRate', 16000))
                p.terminate()
            except Exception:
                pass

            with sr.Microphone(device_index=device_index, sample_rate=sample_rate) as source:
                # Brief ambient noise calibration for better accuracy
                print("[MIC] Calibrating microphone...")
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=1.0)
                    print(f"[MIC] Energy threshold after calibration: {recognizer.energy_threshold:.1f} (sample_rate={sample_rate})")
                    try:
                        self.root.after(0, self.add_message, "System", f"Mic health: threshold={recognizer.energy_threshold:.0f}, sample_rate={sample_rate} Hz")
                    except Exception:
                        pass
                except Exception:
                    pass
                # EXTENDED timeouts: 10s to start speaking, 20s total phrase
                print("[MIC] Listening... (speak within 10 seconds)")
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)
            text = None
            print("[MIC] Processing audio...")
            try:
                text = recognizer.recognize_google(audio, language="en-US")
                print(f"[MIC] Recognized: '{text}'")
            except sr.UnknownValueError:
                print("[MIC] Could not understand audio (1st pass) — retrying once...")
                # Retry once with a second capture (longer limits)
                try:
                    with sr.Microphone(device_index=device_index) as source2:
                        print("[MIC] Retrying: Listening again (15s start / 25s phrase)...")
                        recognizer.adjust_for_ambient_noise(source2, duration=0.8)
                        audio2 = recognizer.listen(source2, timeout=15, phrase_time_limit=25)
                    print("[MIC] Processing retry audio...")
                    text = recognizer.recognize_google(audio2, language="en-US")
                    print(f"[MIC] Recognized on retry: '{text}'")
                except Exception as retry_err:
                    print(f"[MIC] Retry failed: {retry_err}")
                    text = None
            except Exception as e:
                print(f"[MIC] Recognition error: {e}")
                # If other recognizers are present, we could try them here.
                text = None

            if not text:
                self.root.after(0, self.add_message, "System", "Sorry, I didn't catch that.")
                self.root.after(0, self.reset_avatar)
                return

            # Show what was heard, then process WITH voice flag
            self.root.after(0, self.add_message, "You (voice)", text)
            # CRITICAL: Pass voice_origin=True to trigger TTS
            threading.Thread(target=self.process_message, args=(text, True), daemon=True).start()
        except Exception as e:
            tb = traceback.format_exc(limit=1)
            self.root.after(0, self.add_message, "System", f"Voice error: {e}")
            self.root.after(0, self.reset_avatar)
        finally:
            try:
                self.listen_button.configure(state=tk.NORMAL, text="🎤 Listen")
            except Exception:
                pass

    def _capture_and_process_voice_am(self):
        """Capture audio using AudioManager (WASAPI) and process via SpeechRecognition recognizer."""
        try:
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True

            if not getattr(self, 'audio_manager', None):
                # Fallback
                return self._capture_and_process_voice()

            buf: List[np.ndarray] = []
            got_speech = threading.Event()

            def audio_callback(chunk: np.ndarray):
                try:
                    # Ensure 1-D float32 array
                    arr = chunk.flatten()
                    buf.append(arr.copy())
                except Exception:
                    pass

            def on_speech_start():
                # Called when VAD detects speech
                try:
                    print("[AM] Speech started")
                except Exception:
                    pass

            def on_speech_end():
                try:
                    print("[AM] Speech ended")
                except Exception:
                    pass
                got_speech.set()

            # Register callbacks
            self.audio_manager.on_audio_callback = audio_callback
            self.audio_manager.on_speech_start_callback = on_speech_start
            self.audio_manager.on_speech_end_callback = on_speech_end

            # Start input
            device_idx = getattr(self, 'mic_index', None)
            self.audio_manager.start_input(device_idx)

            # Wait for speech or timeout
            waited = got_speech.wait(timeout=20.0)

            # Stop input
            self.audio_manager.stop_input()

            if not buf:
                # No audio captured
                self.root.after(0, self.add_message, "System", "No speech detected during capture")
                try:
                    play_attention_beep()
                except Exception:
                    pass
                return

            # Concatenate chunks and convert to 16-bit PCM bytes
            audio_np = np.concatenate(buf)
            # Clip to -1..1
            audio_np = np.clip(audio_np, -1.0, 1.0)
            int16 = (audio_np * 32767).astype(np.int16)
            raw_bytes = int16.tobytes()

            # Build SpeechRecognition AudioData
            audio_data = sr.AudioData(raw_bytes, self.audio_manager.sample_rate, 2)

            # Recognize
            text = None
            try:
                print("[AM] Recognizing via Google Speech (fallback)")
                text = recognizer.recognize_google(audio_data, language="en-US")
                print(f"[AM] Recognized: '{text}'")
            except sr.UnknownValueError:
                print("[AM] Could not understand audio")
                text = None
            except Exception as e:
                print(f"[AM] Recognition error: {e}")
                text = None

            if not text:
                self.root.after(0, self.add_message, "System", "Sorry, I didn't catch that.")
                return

            # Show what was heard, then process WITH voice flag
            self.root.after(0, self.add_message, "You (voice)", text)
            threading.Thread(target=self.process_message, args=(text, True), daemon=True).start()

        except Exception as e:
            tb = traceback.format_exc(limit=1)
            self.root.after(0, self.add_message, "System", f"Voice (AudioManager) error: {e}")
        finally:
            try:
                self.listen_button.configure(state=tk.NORMAL, text="🎤 Listen")
            except Exception:
                pass
    
    def agent_action(self, action: str, param: str):
        self.animate_thinking()
        threading.Thread(target=self._execute_action, args=(action, param), daemon=True).start()
    
    def _execute_action(self, action: str, param: str):
        try:
            if action == "emotion":
                result = self.agent.express_emotion(param)
            elif action == "explore":
                result = self.agent.explore(param)
            elif action == "spontaneous":
                result = self.agent.spontaneous_act()
            elif action == "ledger":
                result = self.agent.show_ledger()
            else:
                result = "Unknown action"
            
            self.root.after(0, self.add_message, self.agent.name or "Agent X", result)
            self.root.after(0, self.reset_avatar)
        except Exception as e:
            self.root.after(0, self.add_message, "System", f"Error: {e}")
            self.root.after(0, self.reset_avatar)
    
    def animate_thinking(self):
        self.avatar_label.config(text="🤔")
        self.status_label.config(text="Thinking...")
    
    def reset_avatar(self):
        self.avatar_label.config(text="🤖")
        self.status_label.config(text=f"{self.agent.name or 'Agent X'} - Ready")
    
    def request_hide(self):
        """User requests agent to hide"""
        response = self.autonomy.hide()
        self.add_message(self.agent.name or "Agent X", response)
    
    def run(self):
        self.root.mainloop()
        # Stop autonomy when window closes
        self.autonomy.stop()
        try:
            self.tts_worker.stop()
        except Exception:
            pass

    def _on_speak_toggle(self):
        # Try to reflect into agent config if supported
        try:
            val = bool(self.speak_var.get())
            cfg = getattr(self.agent, 'config', None)
            if hasattr(cfg, 'set'):
                try:
                    cfg.set('speak_all', val)
                except Exception:
                    pass
        except Exception:
            pass

    def _init_mic_selector(self):
        """Initialize microphone selection UI using ttk Combobox."""
        try:
            mic_frame = tk.Frame(self.root, bg="#1a1a2e")
            mic_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

            lbl = tk.Label(mic_frame, text="Mic:", bg="#1a1a2e", fg="#ffffff")
            lbl.pack(side=tk.LEFT)

            # Use AudioManager for device enumeration (WASAPI aware)
            names = []
            device_indices = []
            if self.audio_manager:
                try:
                    devices = self.audio_manager.get_devices()
                    for device in devices['input']:
                        # Prioritize WASAPI devices
                        label = f"{device.name}"
                        if 'WASAPI' in device.hostapi:
                            label = f"[WASAPI] {device.name}"
                        names.append(label)
                        device_indices.append(device.index)
                except Exception as e:
                    print(f"[MIC] AudioManager device enum failed: {e}")
            
            # Fallback to SpeechRecognition if AudioManager failed
            if not names and sr:
                try:
                    sr_names = sr.Microphone.list_microphone_names()
                    names = sr_names
                    device_indices = list(range(len(sr_names)))
                except Exception:
                    pass

            if not names:
                info = tk.Label(mic_frame, text="No microphones found", bg="#1a1a2e", fg="#ffaaaa")
                info.pack(side=tk.LEFT, padx=8)
                try:
                    play_attention_beep()
                except Exception:
                    pass
                return

            self._mic_names = names
            self._mic_indices = device_indices
            self._mic_choice = tk.StringVar()
            self._mic_combo = ttk.Combobox(mic_frame, textvariable=self._mic_choice, values=names, width=40, state="readonly")
            self._mic_combo.pack(side=tk.LEFT, padx=8)
            # Load persisted selection if any
            persisted_idx = None
            try:
                cfg = getattr(self.agent, 'config', None)
                if cfg is not None and hasattr(cfg, 'get'):
                    val = cfg.get('mic_device_index', None)
                    if isinstance(val, int):
                        persisted_idx = val
            except Exception:
                persisted_idx = None

            # Default to system default mic (no index); else persisted index
            if persisted_idx is not None:
                try:
                    list_idx = device_indices.index(persisted_idx)
                    self._mic_combo.set(names[list_idx])
                    self.mic_index = persisted_idx
                    if self.audio_manager:
                        self.audio_manager.set_input_device(persisted_idx)
                    print(f"[MIC] Restored device {persisted_idx}: {names[list_idx]}")
                except (ValueError, IndexError):
                    self._mic_combo.set(names[0])
                    self.mic_index = device_indices[0] if device_indices else None
            else:
                self._mic_combo.set(names[0])
                self.mic_index = device_indices[0] if device_indices else None

            def on_change(event=None):
                sel = self._mic_combo.get()
                try:
                    # Map selected name to device index
                    list_idx = names.index(sel)
                    device_idx = device_indices[list_idx]
                    self.mic_index = device_idx
                    if self.audio_manager:
                        self.audio_manager.set_input_device(device_idx)
                    print(f"[MIC] Selected device {device_idx}: {sel}")
                    # Persist selection
                    try:
                        cfg = getattr(self.agent, 'config', None)
                        if cfg is not None and hasattr(cfg, 'set'):
                            cfg.set('mic_device_index', self.mic_index)
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[MIC] Mic select error: {e}")

            self._mic_combo.bind("<<ComboboxSelected>>", on_change)

            refresh_btn = tk.Button(mic_frame, text="Refresh", bg="#34495e", fg="#ffffff", font=("Arial", 9), command=self._refresh_mics)
            refresh_btn.pack(side=tk.LEFT, padx=6)

            test_btn = tk.Button(mic_frame, text="Test Mic", bg="#27ae60", fg="#ffffff", font=("Arial", 9), command=lambda: threading.Thread(target=self._test_mic, daemon=True).start())
            test_btn.pack(side=tk.LEFT, padx=6)
        except Exception as e:
            print(f"[MIC] Selector init error: {e}")

    def _refresh_mics(self):
        try:
            names = []
            device_indices = []
            if self.audio_manager:
                devices = self.audio_manager.get_devices()
                for device in devices['input']:
                    label = f"{device.name}"
                    if 'WASAPI' in device.hostapi:
                        label = f"[WASAPI] {device.name}"
                    names.append(label)
                    device_indices.append(device.index)
            elif sr:
                sr_names = sr.Microphone.list_microphone_names()
                names = sr_names
                device_indices = list(range(len(sr_names)))
            
            self._mic_names = names
            self._mic_indices = device_indices
            self._mic_combo.configure(values=names)
            print(f"[MIC] Found {len(names)} microphones")
            if names:
                self._mic_combo.set(names[0])
            else:
                try:
                    play_attention_beep()
                except Exception:
                    pass
        except Exception as e:
            print(f"[MIC] Refresh failed: {e}")

    def _test_mic(self):
        try:
            # Quick mic test using AudioManager
            if not self.audio_manager:
                self.root.after(0, self.add_message, "System", "AudioManager not available")
                return
            
            device_idx = self.mic_index
            print(f"[MIC] Test: Starting 2-second recording on device {device_idx}...")
            self.root.after(0, self.add_message, "System", "Testing microphone... speak now!")
            
            # Start recording
            self.audio_manager.start_input(device_idx)
            
            # Record for 2 seconds
            chunks = []
            start_time = time.time()
            while time.time() - start_time < 2.0:
                chunk = self.audio_manager.get_input_audio(timeout=0.1)
                if chunk is not None:
                    chunks.append(chunk)
            
            self.audio_manager.stop_input()
            
            # Report statistics
            stats = self.audio_manager.get_statistics()
            speech_pct = 0
            if stats['input_chunks_processed'] > 0:
                speech_pct = (stats['speech_chunks_detected'] / stats['input_chunks_processed']) * 100
            
            msg = f"Mic test: {len(chunks)} chunks recorded, {stats['speech_chunks_detected']} speech, {stats['silence_chunks_detected']} silence ({speech_pct:.0f}% speech detected)"
            print(f"[MIC] {msg}")
            self.root.after(0, self.add_message, "System", msg)
            if len(chunks) == 0 or speech_pct < 10:
                # Beep to get user's attention for assistance
                try:
                    play_attention_beep()
                except Exception:
                    pass
        except Exception as e:
            print(f"[MIC] Test error: {e}")
            self.root.after(0, self.add_message, "System", f"Mic test error: {e}")

    def _init_speaker_selector(self):
        # Use AudioManager for device enumeration (WASAPI aware)
        names = []
        device_indices = []
        sapi_indices = []  # Keep SAPI indices for TTS worker
        
        if self.audio_manager:
            try:
                devices = self.audio_manager.get_devices()
                for device in devices['output']:
                    label = f"{device.name}"
                    if 'WASAPI' in device.hostapi:
                        label = f"[WASAPI] {device.name}"
                    names.append(label)
                    device_indices.append(device.index)
            except Exception as e:
                print(f"[SPEAKER] AudioManager device enum failed: {e}")
        
        # Also get SAPI devices for TTS worker compatibility
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            tmp_voice = win32com.client.Dispatch("SAPI.SpVoice")
            tokens = tmp_voice.GetAudioOutputs()
            
            # Build SAPI mapping (for TTS worker)
            self._spk_ids = []
            for i in range(tokens.Count):
                try:
                    token = tokens.Item(i)
                    self._spk_ids.append(token.Id)
                except Exception:
                    self._spk_ids.append("")
                sapi_indices.append(i)
        except Exception as e:
            print(f"[SPEAKER] SAPI enum failed: {e}")
            self._spk_ids = []

        if not names:
            return

        spk_frame = tk.Frame(self.root, bg="#1a1a2e")
        spk_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        lbl = tk.Label(spk_frame, text="Speaker:", bg="#1a1a2e", fg="#ffffff")
        lbl.pack(side=tk.LEFT)

        self._spk_names = names
        self._spk_indices = device_indices
        self._spk_sapi_indices = sapi_indices
        self._spk_choice = tk.StringVar()
        self._spk_combo = ttk.Combobox(spk_frame, textvariable=self._spk_choice, values=names, width=40, state="readonly")
        self._spk_combo.pack(side=tk.LEFT, padx=8)
        # Restore persisted selection if available
        persisted_idx = None
        try:
            cfg = getattr(self.agent, 'config', None)
            if cfg is not None and hasattr(cfg, 'get'):
                val = cfg.get('speaker_output_index', None)
                if isinstance(val, int) and 0 <= val < len(names):
                    persisted_idx = val
        except Exception:
            persisted_idx = None
        if persisted_idx is not None:
            self._spk_combo.set(names[persisted_idx])
            if hasattr(self, 'tts_worker') and self.tts_worker and persisted_idx < len(sapi_indices):
                self.tts_worker.set_output_index(sapi_indices[persisted_idx])
            if self.audio_manager and persisted_idx < len(device_indices):
                self.audio_manager.set_output_device(device_indices[persisted_idx])
            print(f"[TTS] Restored speaker index {persisted_idx}: {names[persisted_idx]}")
        else:
            self._spk_combo.set(names[0])

        def on_spk_change(event=None):
            sel = self._spk_combo.get()
            try:
                list_idx = names.index(sel)
                # Update AudioManager
                if self.audio_manager and list_idx < len(device_indices):
                    device_idx = device_indices[list_idx]
                    self.audio_manager.set_output_device(device_idx)
                    print(f"[SPEAKER] AudioManager set to device {device_idx}: {sel}")
                # Update TTS worker (SAPI)
                if hasattr(self, 'tts_worker') and self.tts_worker and list_idx < len(sapi_indices):
                    sapi_idx = sapi_indices[list_idx]
                    self.tts_worker.set_output_index(sapi_idx)
                    print(f"[TTS] SAPI set to index {sapi_idx}: {sel}")
                # Persist selection
                try:
                    cfg = getattr(self.agent, 'config', None)
                    if cfg is not None and hasattr(cfg, 'set'):
                        cfg.set('speaker_output_index', list_idx)
                        # also save description for visibility
                        cfg.set('speaker_output_desc', sel)
                except Exception:
                    pass
            except Exception as e:
                print(f"[TTS] Speaker select error: {e}")

        self._spk_combo.bind("<<ComboboxSelected>>", on_spk_change)

    def _speak_sync(self, text: str):
        """Enqueue text for the dedicated TTS worker to speak."""
        try:
            if self.mute_var.get():
                print("[TTS] Muted; dropping speech request")
                return
            if hasattr(self, 'tts_worker') and self.tts_worker:
                self.tts_worker.speak(text)
            else:
                print("[TTS] Worker not available; dropping speech request")
        except Exception as e:
            print(f"[TTS] Enqueue failed: {e}")

    def _on_close(self):
        """Gracefully shut down subsystems and close the window."""
        try:
            self.autonomy.stop()
        except Exception:
            pass
        try:
            if getattr(self, 'audio_manager', None):
                self.audio_manager.shutdown()
        except Exception:
            pass
        try:
            if getattr(self, 'tts_worker', None):
                self.tts_worker.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

if __name__ == "__main__":
    from aqi_agent_x import AQIAgentX
    agent = AQIAgentX()
    agent.activate()
    avatar = AgentXAvatar(agent)
    avatar.run()
