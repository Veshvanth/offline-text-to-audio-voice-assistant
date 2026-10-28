import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, List
from PIL import Image

from .config import load_config, save_config, VOICE_OPTIONS, MODE_OPTIONS, ENGINE_OPTIONS
from .screen_capture import SnipOverlay, capture_fullscreen, capture_clipboard, has_image_changed
from .ai_vision import AIVisionEngine
from .local_ocr import LocalOCREngine
from .tts_engine import TTSEngine
from .audio_visualizer import AudioVisualizer
from .scratchpad import HandwritingScratchpad
from .voice_commands import VoiceCommandListener

# Try importing pynput for global keyboard shortcuts
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


class AuraVoiceApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Load persisted settings
        self.config = load_config()

        # Window Setup
        self.title("🎙️ AuraVoice AI - Live Screen & Handwriting Voice Assistant")
        self.geometry("860x720")
        self.minsize(760, 620)
        self.configure(bg="#0f172a")

        # Keep on top if configured
        if self.config.get("always_on_top", True):
            self.attributes("-topmost", True)

        # Initialize Engines
        # 1. Local Offline Engine (No API key required)
        self.local_ocr_engine = LocalOCREngine()

        # 2. Cloud Gemini Vision Engine
        self.cloud_vision_engine = AIVisionEngine(
            api_key=self.config.get("gemini_api_key", ""),
            model_name=self.config.get("model_name", "gemini-2.5-flash")
        )

        # 3. Text to Speech Engine (Adjustable speed, high-def voices)
        self.tts_engine = TTSEngine(
            on_start=self._on_speech_started,
            on_finish=self._on_speech_finished,
            on_error=self._on_speech_error
        )

        # 4. Voice Commands Listener (Microphone)
        self.voice_command_listener = VoiceCommandListener(
            on_command=self._on_voice_command_detected,
            on_status=self._on_voice_command_status
        )

        # Internal State & Paragraph Navigation
        self.current_image: Optional[Image.Image] = None
        self.paragraphs: List[str] = []
        self.current_para_index = 0
        self.is_live_watch_active = False
        self.live_watch_thread: Optional[threading.Thread] = None
        self.last_monitored_image: Optional[Image.Image] = None
        self.hotkey_listener = None

        # Build UI Components
        self._setup_styles()
        self._build_header()
        self._build_engine_and_mode_bar()
        self._build_action_bar()
        self._build_audio_controls()
        self._build_paragraph_nav_bar()
        self._build_transcript_box()
        self._build_footer()

        # Start Global Hotkey Listener
        if PYNPUT_AVAILABLE:
            self._start_global_hotkey()

        # Start Voice Commands if enabled
        if self.config.get("voice_commands_enabled", True):
            self.after(800, self.voice_command_listener.start)

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Combobox styling
        style.configure("TCombobox",
                        fieldbackground="#1e293b",
                        background="#334155",
                        foreground="#f8fafc",
                        arrowcolor="#38bdf8",
                        font=("Segoe UI", 9))
        
        style.map("TCombobox",
                  fieldbackground=[("readonly", "#1e293b")],
                  selectbackground=[("readonly", "#0284c7")],
                  selectforeground=[("readonly", "#ffffff")])

        # Scale slider styling
        style.configure("Horizontal.TScale",
                        background="#0f172a",
                        troughcolor="#1e293b",
                        sliderrelief="flat")

    def _build_header(self):
        header = tk.Frame(self, bg="#0f172a")
        header.pack(fill=tk.X, padx=20, pady=(12, 6))

        # Title and Subtitle
        title_box = tk.Frame(header, bg="#0f172a")
        title_box.pack(side=tk.LEFT)

        title_label = tk.Label(
            title_box,
            text="🎙️ AuraVoice AI",
            font=("Segoe UI", 17, "bold"),
            bg="#0f172a",
            fg="#f8fafc"
        )
        title_label.pack(anchor="w")

        subtitle = tk.Label(
            title_box,
            text="Live Screen & Human Handwriting to Speech Converter with Voice Commands",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94a3b8"
        )
        subtitle.pack(anchor="w")

        # Right side: Visualizer and Status Pill
        status_box = tk.Frame(header, bg="#0f172a")
        status_box.pack(side=tk.RIGHT, pady=2)

        # Audio wave visualizer
        self.visualizer = AudioVisualizer(status_box, width=140, height=28, bg="#0f172a")
        self.visualizer.pack(side=tk.RIGHT, padx=(8, 0))

        # Status badge pill
        self.status_pill = tk.Label(
            status_box,
            text="🟢 Ready",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#38bdf8",
            padx=10,
            pady=3,
            relief=tk.FLAT
        )
        self.status_pill.pack(side=tk.RIGHT)

    def _build_engine_and_mode_bar(self):
        """Engine Switcher (Local No Key vs Cloud Gemini) and Voice Command status."""
        top_bar = tk.Frame(self, bg="#1e293b", bd=1, relief=tk.SOLID)
        top_bar.pack(fill=tk.X, padx=20, pady=(2, 6))

        inner = tk.Frame(top_bar, bg="#1e293b")
        inner.pack(fill=tk.X, padx=12, pady=6)

        # Engine Selection
        tk.Label(
            inner,
            text="⚙️ Engine:",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#cbd5e1"
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.engine_var = tk.StringVar()
        engine_names = [name for _, name, _ in ENGINE_OPTIONS]
        self.engine_combo = ttk.Combobox(
            inner,
            textvariable=self.engine_var,
            values=engine_names,
            state="readonly",
            width=32
        )
        curr_eng = self.config.get("engine", "local")
        matched = next((name for eid, name, _ in ENGINE_OPTIONS if eid == curr_eng), engine_names[0])
        self.engine_combo.set(matched)
        self.engine_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.engine_combo.bind("<<ComboboxSelected>>", self._on_engine_changed)

        # Mode Selection
        tk.Label(
            inner,
            text="Mode:",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8"
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.mode_var = tk.StringVar()
        mode_names = [name for _, name, _ in MODE_OPTIONS]
        self.mode_combo = ttk.Combobox(
            inner,
            textvariable=self.mode_var,
            values=mode_names,
            state="readonly",
            width=20
        )
        curr_id = self.config.get("assistant_mode", "direct")
        display_map = {cid: name for cid, name, _ in MODE_OPTIONS}
        self.mode_combo.set(display_map.get(curr_id, mode_names[0]))
        self.mode_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)

        # Microphone Voice Commands Toggle
        self.mic_btn = tk.Button(
            inner,
            text="🎤 Voice Commands: ON",
            font=("Segoe UI", 9, "bold"),
            bg="#065f46",
            fg="#a7f3d0",
            activebackground="#047857",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.toggle_voice_commands
        )
        self.mic_btn.pack(side=tk.RIGHT)

        # Voice command help tip
        self.voice_cmd_tip = tk.Label(
            inner,
            text="Say: 'pause', 'continue', 'next', 'back', 'faster', 'stop'",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#64748b"
        )
        self.voice_cmd_tip.pack(side=tk.RIGHT, padx=8)

    def _build_action_bar(self):
        """Action Bar with primary capture buttons."""
        action_card = tk.Frame(self, bg="#1e293b", bd=1, relief=tk.SOLID)
        action_card.pack(fill=tk.X, padx=20, pady=4)

        inner = tk.Frame(action_card, bg="#1e293b")
        inner.pack(fill=tk.X, padx=12, pady=8)

        # Primary Snip Button
        self.snip_btn = tk.Button(
            inner,
            text="✂️ Snip & Read (Ctrl+Shift+S)",
            font=("Segoe UI", 10, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=7,
            cursor="hand2",
            command=self.trigger_snip
        )
        self.snip_btn.pack(side=tk.LEFT, padx=(0, 6))

        # Full Screen
        self.full_btn = tk.Button(
            inner,
            text="🖥️ Full Screen",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#f8fafc",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=7,
            cursor="hand2",
            command=self.trigger_fullscreen
        )
        self.full_btn.pack(side=tk.LEFT, padx=3)

        # Handwriting Scratchpad
        self.scratch_btn = tk.Button(
            inner,
            text="✍️ Draw / Scratchpad",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#38bdf8",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=7,
            cursor="hand2",
            command=self.open_scratchpad
        )
        self.scratch_btn.pack(side=tk.LEFT, padx=3)

        # Paste Clipboard
        self.clip_btn = tk.Button(
            inner,
            text="📋 Paste Image",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#f8fafc",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=7,
            cursor="hand2",
            command=self.trigger_clipboard
        )
        self.clip_btn.pack(side=tk.LEFT, padx=3)

        # Live Monitor Toggle Button
        self.live_btn = tk.Button(
            inner,
            text="👀 Live Watch",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#f8fafc",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=7,
            cursor="hand2",
            command=self.toggle_live_watch
        )
        self.live_btn.pack(side=tk.RIGHT)

    def _build_audio_controls(self):
        """Speed adjustability, voice selection, and audio playback controls."""
        controls_card = tk.Frame(self, bg="#1e293b", bd=1, relief=tk.SOLID)
        controls_card.pack(fill=tk.X, padx=20, pady=4)

        # Row 1: Speed Adjustability & Voice Selection
        row1 = tk.Frame(controls_card, bg="#1e293b")
        row1.pack(fill=tk.X, padx=14, pady=(8, 4))

        # --- SPEED ADJUSTABILITY SLIDER ---
        speed_box = tk.Frame(row1, bg="#1e293b")
        speed_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))

        speed_header = tk.Frame(speed_box, bg="#1e293b")
        speed_header.pack(fill=tk.X)

        tk.Label(
            speed_header,
            text="⚡ Speech Speed Rate:",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#f8fafc"
        ).pack(side=tk.LEFT)

        self.speed_val = self.config.get("speed", 1.0)
        self.speed_badge = tk.Label(
            speed_header,
            text=f"{self.speed_val:.2f}x (Normal)",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            padx=6,
            pady=1
        )
        self.speed_badge.pack(side=tk.RIGHT)

        # Speed Slider (0.50x to 2.50x)
        self.speed_slider = ttk.Scale(
            speed_box,
            from_=0.5,
            to=2.5,
            orient=tk.HORIZONTAL,
            style="Horizontal.TScale",
            command=self._on_speed_slide
        )
        self.speed_slider.set(self.speed_val)
        self.speed_slider.pack(fill=tk.X, pady=(2, 0))

        # Quick Speed Preset Chips
        preset_frame = tk.Frame(speed_box, bg="#1e293b")
        preset_frame.pack(fill=tk.X, pady=(2, 0))
        for spd in [0.75, 1.0, 1.25, 1.5, 2.0]:
            btn = tk.Button(
                preset_frame,
                text=f"{spd}x",
                font=("Segoe UI", 7),
                bg="#334155",
                fg="#94a3b8",
                relief=tk.FLAT,
                padx=4,
                pady=0,
                command=lambda s=spd: self._set_speed_preset(s)
            )
            btn.pack(side=tk.LEFT, padx=1)

        # --- VOICE SELECTION DROPDOWN ---
        voice_box = tk.Frame(row1, bg="#1e293b")
        voice_box.pack(side=tk.RIGHT, fill=tk.X, padx=(10, 0))

        tk.Label(
            voice_box,
            text="🗣️ AI Voice Character:",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#f8fafc"
        ).pack(anchor="w")

        self.voice_var = tk.StringVar()
        voice_display_names = [v["name"] for v in VOICE_OPTIONS]
        self.voice_combo = ttk.Combobox(
            voice_box,
            textvariable=self.voice_var,
            values=voice_display_names,
            state="readonly",
            width=28
        )
        curr_voice_id = self.config.get("voice", "en-US-JennyNeural")
        matched = next((v["name"] for v in VOICE_OPTIONS if v["id"] == curr_voice_id), voice_display_names[0])
        self.voice_combo.set(matched)
        self.voice_combo.pack(pady=(3, 0))
        self.voice_combo.bind("<<ComboboxSelected>>", self._on_voice_changed)

        # Row 2: Playback Action Buttons
        row2 = tk.Frame(controls_card, bg="#1e293b")
        row2.pack(fill=tk.X, padx=14, pady=(4, 8))

        # Play / Pause Toggle
        self.play_pause_btn = tk.Button(
            row2,
            text="▶️ Read Text",
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="#ffffff",
            activebackground="#059669",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.toggle_playback
        )
        self.play_pause_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Stop Button
        self.stop_btn = tk.Button(
            row2,
            text="⏹️ Stop",
            font=("Segoe UI", 9),
            bg="#ef4444",
            fg="#ffffff",
            activebackground="#dc2626",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.stop_playback
        )
        self.stop_btn.pack(side=tk.LEFT, padx=3)

        # Replay at Current Speed
        self.replay_btn = tk.Button(
            row2,
            text="🔁 Replay",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#f8fafc",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.replay_text
        )
        self.replay_btn.pack(side=tk.LEFT, padx=3)

        # Export Audio MP3
        self.export_btn = tk.Button(
            row2,
            text="💾 Save Audio (.mp3)",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#38bdf8",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.save_audio_file
        )
        self.export_btn.pack(side=tk.RIGHT)

    def _build_paragraph_nav_bar(self):
        """Paragraph & Page Navigation Bar (Next/Prev Para)."""
        nav_frame = tk.Frame(self, bg="#0f172a")
        nav_frame.pack(fill=tk.X, padx=20, pady=(2, 2))

        # Previous Paragraph Button
        self.prev_para_btn = tk.Button(
            nav_frame,
            text="⏮️ Prev Para (Say: 'back')",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#cbd5e1",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=2,
            command=self.previous_paragraph
        )
        self.prev_para_btn.pack(side=tk.LEFT)

        # Next Paragraph Button
        self.next_para_btn = tk.Button(
            nav_frame,
            text="⏭️ Next Para (Say: 'next')",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#cbd5e1",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=2,
            command=self.next_paragraph
        )
        self.next_para_btn.pack(side=tk.LEFT, padx=6)

        # Paragraph count indicator
        self.para_indicator = tk.Label(
            nav_frame,
            text="Paragraph: 0 / 0",
            font=("Segoe UI", 8, "bold"),
            bg="#0f172a",
            fg="#38bdf8"
        )
        self.para_indicator.pack(side=tk.LEFT, padx=10)

        # Voice command activity indicator
        self.voice_feedback_lbl = tk.Label(
            nav_frame,
            text="🎤 Mic Active: Ready for voice commands",
            font=("Segoe UI", 8, "italic"),
            bg="#0f172a",
            fg="#64748b"
        )
        self.voice_feedback_lbl.pack(side=tk.RIGHT)

    def _build_transcript_box(self):
        """Live Transcript Text Editor."""
        text_card = tk.Frame(self, bg="#1e293b", bd=1, relief=tk.SOLID)
        text_card.pack(fill=tk.BOTH, expand=True, padx=20, pady=4)

        header = tk.Frame(text_card, bg="#1e293b")
        header.pack(fill=tk.X, padx=14, pady=(8, 3))

        tk.Label(
            header,
            text="📝 Recognized Text & Handwriting (Live Transcript):",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#f8fafc"
        ).pack(side=tk.LEFT)

        self.word_count_lbl = tk.Label(
            header,
            text="0 words",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#64748b"
        )
        self.word_count_lbl.pack(side=tk.RIGHT, padx=4)

        copy_btn = tk.Button(
            header,
            text="📋 Copy Text",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#f8fafc",
            relief=tk.FLAT,
            padx=8,
            pady=1,
            cursor="hand2",
            command=self.copy_transcript
        )
        copy_btn.pack(side=tk.RIGHT, padx=6)

        # Scrollable Text Area
        text_inner = tk.Frame(text_card, bg="#0f172a")
        text_inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))

        scrollbar = tk.Scrollbar(text_inner, bg="#1e293b")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_box = tk.Text(
            text_inner,
            bg="#0f172a",
            fg="#f8fafc",
            insertbackground="#38bdf8",
            selectbackground="#0284c7",
            selectforeground="#ffffff",
            font=("Segoe UI", 11),
            wrap=tk.WORD,
            bd=0,
            padx=10,
            pady=10,
            yscrollcommand=scrollbar.set
        )
        self.text_box.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_box.yview)

        # Configure highlight tag for current reading paragraph
        self.text_box.tag_config("current_para", background="#1e3a8a", foreground="#ffffff")

        # Initial instructions
        self.text_box.insert(
            tk.END,
            "💡 Ready! You can use AuraVoice without any API keys:\n"
            "   1. 'Local Engine (No API Key)' is selected by default — runs 100% offline on your PC!\n"
            "   2. Click 'Snip & Read' or press Ctrl+Shift+S over any handwriting or screen text.\n"
            "   3. Voice Commands: Say 'pause', 'continue', 'next', 'back', 'faster', or 'stop' into your microphone anytime!\n"
        )
        self.text_box.bind("<KeyRelease>", self._on_text_edited)

    def _build_footer(self):
        """Settings drawer and hotkey indicator."""
        footer = tk.Frame(self, bg="#0f172a")
        footer.pack(fill=tk.X, padx=20, pady=(2, 10))

        # Always on Top Checkbox
        self.topmost_var = tk.BooleanVar(value=self.config.get("always_on_top", True))
        top_cb = tk.Checkbutton(
            footer,
            text="📌 Keep on Top",
            variable=self.topmost_var,
            bg="#0f172a",
            fg="#94a3b8",
            activebackground="#0f172a",
            activeforeground="#f8fafc",
            selectcolor="#1e293b",
            font=("Segoe UI", 8),
            command=self._on_toggle_topmost
        )
        top_cb.pack(side=tk.LEFT)

        # Hotkey badge
        hotkey_text = "⌨️ Shortcut: Ctrl+Shift+S (Active anywhere)" if PYNPUT_AVAILABLE else "⌨️ Shortcut: Set up pynput"
        tk.Label(
            footer,
            text=hotkey_text,
            font=("Segoe UI", 8),
            bg="#0f172a",
            fg="#64748b"
        ).pack(side=tk.LEFT, padx=12)

        # Settings / API Key button (optional for Cloud mode)
        self.settings_btn = tk.Button(
            footer,
            text="⚙️ Cloud API Key (Optional)",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#38bdf8",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self.open_settings_dialog
        )
        self.settings_btn.pack(side=tk.RIGHT)

    # -------------------------------------------------------------
    # Voice Commands Handlers
    # -------------------------------------------------------------
    def toggle_voice_commands(self):
        new_state = self.voice_command_listener.toggle()
        if new_state:
            self.mic_btn.config(text="🎤 Voice Commands: ON", bg="#065f46", fg="#a7f3d0")
            self.voice_feedback_lbl.config(text="🎤 Mic Listening: Speak commands anytime", fg="#10b981")
            self.config["voice_commands_enabled"] = True
        else:
            self.mic_btn.config(text="🎤 Voice Commands: OFF", bg="#334155", fg="#94a3b8")
            self.voice_feedback_lbl.config(text="🎤 Voice Commands Paused", fg="#64748b")
            self.config["voice_commands_enabled"] = False
        save_config(self.config)

    def _on_voice_command_status(self, status_msg: str):
        self.after(0, lambda: self.voice_feedback_lbl.config(text=status_msg))

    def _on_voice_command_detected(self, cmd: str, raw_phrase: str):
        """Execute spoken voice command safely in main GUI thread."""
        self.after(0, lambda: self._execute_voice_command(cmd, raw_phrase))

    def _execute_voice_command(self, cmd: str, raw_phrase: str):
        self._update_status(f"⚡ Spoken Command: {cmd.upper()}", "#a855f7")
        self.voice_feedback_lbl.config(text=f"⚡ Heard: '{raw_phrase}' -> Action: {cmd.upper()}", fg="#a855f7")

        if cmd == "pause":
            if self.tts_engine.is_playing() and not self.tts_engine.is_paused:
                self.toggle_playback()

        elif cmd == "resume":
            if self.tts_engine.is_paused:
                self.toggle_playback()
            elif not self.tts_engine.is_playing():
                self._speak_current_paragraph_or_text()

        elif cmd == "stop":
            self.stop_playback()

        elif cmd == "next_para":
            self.next_paragraph()

        elif cmd == "prev_para":
            self.previous_paragraph()

        elif cmd == "faster":
            cur_speed = float(self.speed_slider.get())
            new_speed = min(2.5, round(cur_speed + 0.25, 2))
            self.speed_slider.set(new_speed)
            self._on_speed_slide(str(new_speed))
            self._update_status(f"⚡ Speed increased to {new_speed:.2f}x", "#38bdf8")

        elif cmd == "slower":
            cur_speed = float(self.speed_slider.get())
            new_speed = max(0.5, round(cur_speed - 0.25, 2))
            self.speed_slider.set(new_speed)
            self._on_speed_slide(str(new_speed))
            self._update_status(f"⚡ Speed decreased to {new_speed:.2f}x", "#38bdf8")

        elif cmd == "replay":
            self.replay_text()

        elif cmd == "snip":
            self.trigger_snip()

    # -------------------------------------------------------------
    # Paragraph & Page Navigation
    # -------------------------------------------------------------
    def _parse_paragraphs_from_text(self, full_text: str):
        """Splits full transcript into logical paragraphs/sections."""
        raw_blocks = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        if not raw_blocks:
            raw_blocks = [l.strip() for l in full_text.split("\n") if l.strip()]
        self.paragraphs = raw_blocks if raw_blocks else [full_text.strip()]
        self.current_para_index = 0
        self._update_para_indicator()

    def _update_para_indicator(self):
        total = len(self.paragraphs)
        cur = (self.current_para_index + 1) if total > 0 else 0
        self.para_indicator.config(text=f"Paragraph: {cur} / {total}")

    def next_paragraph(self):
        if not self.paragraphs:
            return
        if self.current_para_index < len(self.paragraphs) - 1:
            self.current_para_index += 1
            self._update_para_indicator()
            self._speak_current_paragraph()
        else:
            self._update_status("Reached end of paragraphs", "#38bdf8")

    def previous_paragraph(self):
        if not self.paragraphs:
            return
        if self.current_para_index > 0:
            self.current_para_index -= 1
            self._update_para_indicator()
            self._speak_current_paragraph()
        else:
            self._update_status("Already at first paragraph", "#38bdf8")

    def _speak_current_paragraph(self):
        if not self.paragraphs or self.current_para_index >= len(self.paragraphs):
            return
        para_text = self.paragraphs[self.current_para_index]
        self._highlight_paragraph(para_text)
        self._speak_text_string(para_text)

    def _speak_current_paragraph_or_text(self):
        if self.paragraphs and self.current_para_index < len(self.paragraphs):
            self._speak_current_paragraph()
        else:
            self._speak_current_text()

    def _highlight_paragraph(self, target_text: str):
        """Highlights the currently active paragraph in the text editor."""
        try:
            self.text_box.tag_remove("current_para", "1.0", tk.END)
            start_pos = "1.0"
            idx = self.text_box.search(target_text[:40], start_pos, tk.END)
            if idx:
                end_idx = f"{idx}+{len(target_text)}c"
                self.text_box.tag_add("current_para", idx, end_idx)
                self.text_box.see(idx)
        except Exception:
            pass

    # -------------------------------------------------------------
    # Screen & Handwriting Capture Actions
    # -------------------------------------------------------------
    def trigger_snip(self):
        """Launches the screen snipping overlay."""
        self._update_status("✂️ Drag a rectangle on your screen...", "#38bdf8")
        overlay = SnipOverlay(self, self._on_snip_done)
        overlay.start()

    def _on_snip_done(self, image: Optional[Image.Image]):
        if image is None:
            self._update_status("🟢 Ready", "#38bdf8")
            return
        self.current_image = image
        self._process_image_async(image)

    def trigger_fullscreen(self):
        """Captures the active full screen."""
        self.withdraw()
        self.after(250, self._do_capture_fullscreen)

    def _do_capture_fullscreen(self):
        img = capture_fullscreen()
        self.deiconify()
        if img:
            self.current_image = img
            self._process_image_async(img)

    def trigger_clipboard(self):
        """Grabs image from clipboard."""
        img = capture_clipboard()
        if img:
            self.current_image = img
            self._process_image_async(img)
        else:
            messagebox.showinfo("Clipboard Empty", "No screenshot found in clipboard.\nTip: Press Win+Shift+S first to capture a snip!")

    def open_scratchpad(self):
        """Opens interactive handwriting canvas."""
        HandwritingScratchpad(self, on_submit=self._on_scratchpad_submitted)

    def _on_scratchpad_submitted(self, image: Image.Image):
        self.current_image = image
        self._process_image_async(image)

    # -------------------------------------------------------------
    # Async OCR Processing (Local vs Cloud)
    # -------------------------------------------------------------
    def _process_image_async(self, image: Image.Image):
        curr_eng = self.config.get("engine", "local")

        # Check API key only if user explicitly selected Cloud Gemini mode
        if curr_eng == "gemini" and not self.config.get("gemini_api_key"):
            self._prompt_api_key_banner()
            return

        eng_label = "Local Offline OCR (No Key)" if curr_eng == "local" else "Gemini Vision"
        self._update_status(f"🔍 Reading handwriting with {eng_label}...", "#f59e0b")
        self.snip_btn.config(state=tk.DISABLED)

        # Selected mode ID
        curr_name = self.mode_var.get()
        mode_id = next((cid for cid, name, _ in MODE_OPTIONS if name == curr_name), "direct")

        def task():
            try:
                if curr_eng == "local":
                    text = self.local_ocr_engine.recognize(image)
                else:
                    text = self.cloud_vision_engine.recognize_screen_and_handwriting(image, mode=mode_id)
                self.after(0, lambda: self._on_recognition_completed(text))
            except Exception as e:
                self.after(0, lambda: self._on_recognition_error(str(e)))

        threading.Thread(target=task, daemon=True).start()

    def _on_recognition_completed(self, text: str):
        self.snip_btn.config(state=tk.NORMAL)
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, text)
        self._update_word_count()

        # Check for Gemini API key error
        if "API key is required" in text or "Invalid Gemini API Key" in text:
            self._update_status("⚠️ API Key Error", "#ef4444")
            self.open_settings_dialog()
            return

        self._update_status("🟢 Text & Handwriting Recognized", "#10b981")

        # Parse paragraphs and start reading
        if text and not text.startswith("No readable text"):
            self._parse_paragraphs_from_text(text)
            self._speak_current_paragraph()

    def _on_recognition_error(self, err_msg: str):
        self.snip_btn.config(state=tk.NORMAL)
        self._update_status("❌ Error", "#ef4444")
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, f"Error processing screen image: {err_msg}")

    # -------------------------------------------------------------
    # Audio Speech Playback
    # -------------------------------------------------------------
    def _speak_text_string(self, text: str):
        if not text:
            return

        vname = self.voice_var.get()
        voice_id = next((v["id"] for v in VOICE_OPTIONS if v["name"] == vname), "en-US-JennyNeural")
        speed = float(self.speed_slider.get())

        self._update_status(f"🔊 Speaking ({speed:.2f}x)...", "#38bdf8")
        self.play_pause_btn.config(text="⏸️ Pause", bg="#f59e0b")

        self.tts_engine.speak(
            text=text,
            voice=voice_id,
            speed=speed,
            pitch=self.config.get("pitch", 0),
            volume=self.config.get("volume", 1.0)
        )

    def _speak_current_text(self):
        text = self.text_box.get("1.0", tk.END).strip()
        if not self.paragraphs:
            self._parse_paragraphs_from_text(text)
        self._speak_current_paragraph()

    def toggle_playback(self):
        if self.tts_engine.is_playing():
            is_paused = self.tts_engine.toggle_pause()
            if is_paused:
                self.play_pause_btn.config(text="▶️ Resume", bg="#10b981")
                self.visualizer.stop_animation()
                self._update_status("⏸️ Paused (Say 'continue')", "#94a3b8")
            else:
                self.play_pause_btn.config(text="⏸️ Pause", bg="#f59e0b")
                self.visualizer.start_animation()
                self._update_status("🔊 Speaking...", "#38bdf8")
        else:
            self._speak_current_paragraph_or_text()

    def stop_playback(self):
        self.tts_engine.stop()
        self.visualizer.stop_animation()
        self.play_pause_btn.config(text="▶️ Read Text", bg="#10b981")
        self._update_status("🟢 Ready", "#38bdf8")

    def replay_text(self):
        """Stops and replays current paragraph or text at current speed setting."""
        self.tts_engine.stop()
        self._speak_current_paragraph_or_text()

    def save_audio_file(self):
        """Prompts user to export the synthesized speech to an mp3 file."""
        path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 Audio Files", "*.mp3"), ("All Files", "*.*")],
            title="Save Speech Audio File"
        )
        if path:
            success = self.tts_engine.save_current_audio_to_file(path)
            if success:
                messagebox.showinfo("Export Successful", f"Audio saved successfully to:\n{path}")
            else:
                messagebox.showerror("Export Failed", "Could not export audio file. Please try speaking the text first.")

    # -------------------------------------------------------------
    # Settings & Engine Callbacks
    # -------------------------------------------------------------
    def _on_engine_changed(self, event=None):
        ename = self.engine_var.get()
        eid = next((i for i, name, _ in ENGINE_OPTIONS if name == ename), "local")
        self.config["engine"] = eid
        save_config(self.config)
        if eid == "local":
            self._update_status("🔒 Switched to Local Engine (No Key Required)", "#10b981")
        else:
            self._update_status("☁️ Switched to Gemini Cloud Vision", "#38bdf8")
            if not self.config.get("gemini_api_key"):
                self.open_settings_dialog()

    def _on_speed_slide(self, val_str: str):
        val = float(val_str)
        desc = "Normal"
        if val < 0.85:
            desc = "Slow"
        elif val > 1.4:
            desc = "Fast"
        elif val > 1.15:
            desc = "Brisk"

        self.speed_badge.config(text=f"{val:.2f}x ({desc})")
        self.config["speed"] = round(val, 2)
        save_config(self.config)

    def _set_speed_preset(self, speed: float):
        self.speed_slider.set(speed)
        self._on_speed_slide(str(speed))

    def _on_voice_changed(self, event=None):
        vname = self.voice_var.get()
        voice_id = next((v["id"] for v in VOICE_OPTIONS if v["name"] == vname), "en-US-JennyNeural")
        self.config["voice"] = voice_id
        save_config(self.config)

    def _on_mode_changed(self, event=None):
        curr_name = self.mode_var.get()
        mode_id = next((cid for cid, name, _ in MODE_OPTIONS if name == curr_name), "direct")
        self.config["assistant_mode"] = mode_id
        save_config(self.config)

    # -------------------------------------------------------------
    # Live Watch Mode
    # -------------------------------------------------------------
    def toggle_live_watch(self):
        if self.is_live_watch_active:
            self.is_live_watch_active = False
            self.live_btn.config(text="👀 Live Watch", bg="#334155", fg="#f8fafc")
            self._update_status("🟢 Ready", "#38bdf8")
        else:
            self.is_live_watch_active = True
            self.live_btn.config(text="🔴 Watching...", bg="#b91c1c", fg="#ffffff")
            self._update_status("👀 Live Watch Active: Monitoring screen...", "#f59e0b")
            self.live_watch_thread = threading.Thread(target=self._live_watch_loop, daemon=True)
            self.live_watch_thread.start()

    def _live_watch_loop(self):
        while self.is_live_watch_active:
            time.sleep(3.5)
            if not self.is_live_watch_active:
                break
            if self.tts_engine.is_playing():
                continue

            new_img = capture_fullscreen()
            if new_img and has_image_changed(self.last_monitored_image, new_img, threshold=0.08):
                self.last_monitored_image = new_img
                self.after(0, lambda img=new_img: self._process_image_async(img))

    # -------------------------------------------------------------
    # Speech Engine Notifications
    # -------------------------------------------------------------
    def _on_speech_started(self):
        self.after(0, self._handle_speech_started)

    def _handle_speech_started(self):
        self.visualizer.start_animation()
        self.play_pause_btn.config(text="⏸️ Pause", bg="#f59e0b")
        spd = float(self.speed_slider.get())
        self._update_status(f"🔊 Speaking ({spd:.2f}x)...", "#38bdf8")

    def _on_speech_finished(self):
        self.after(0, self._handle_speech_finished)

    def _handle_speech_finished(self):
        self.visualizer.stop_animation()
        self.play_pause_btn.config(text="▶️ Read Text", bg="#10b981")
        self._update_status("🟢 Ready (Say 'next' for next para)", "#38bdf8")

    def _on_speech_error(self, err_msg: str):
        self.after(0, lambda: self._update_status(f"❌ {err_msg}", "#ef4444"))

    # -------------------------------------------------------------
    # Global Hotkey (pynput)
    # -------------------------------------------------------------
    def _start_global_hotkey(self):
        try:
            hotkeys = keyboard.GlobalHotKeys({
                '<ctrl>+<shift>+s': self._on_hotkey_triggered,
                '<alt>+s': self._on_hotkey_triggered
            })
            hotkeys.start()
            self.hotkey_listener = hotkeys
        except Exception as e:
            print(f"Global hotkey initialization error: {e}")

    def _on_hotkey_triggered(self):
        self.after(0, self.trigger_snip)

    # -------------------------------------------------------------
    # UI Helpers & Dialogs
    # -------------------------------------------------------------
    def _update_status(self, text: str, fg_color: str):
        self.status_pill.config(text=text, fg=fg_color)

    def _update_word_count(self):
        content = self.text_box.get("1.0", tk.END).strip()
        words = len(content.split()) if content else 0
        chars = len(content)
        self.word_count_lbl.config(text=f"{words} words | {chars} chars")

    def _on_text_edited(self, event=None):
        self._update_word_count()
        content = self.text_box.get("1.0", tk.END).strip()
        if content:
            self._parse_paragraphs_from_text(content)

    def copy_transcript(self):
        content = self.text_box.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self._update_status("📋 Text Copied to Clipboard!", "#38bdf8")
            self.after(2000, lambda: self._update_status("🟢 Ready", "#38bdf8"))

    def _on_toggle_topmost(self):
        val = self.topmost_var.get()
        self.attributes("-topmost", val)
        self.config["always_on_top"] = val
        save_config(self.config)

    def _prompt_api_key_banner(self):
        ans = messagebox.askyesno(
            "Gemini Cloud Vision Setup",
            "You selected Cloud Gemini mode, which uses an API key.\n\n"
            "Would you like to enter a Gemini API key now?\n\n"
            "(Or click 'No' to use the 100% Free Local Engine with zero API keys!)"
        )
        if ans:
            self.open_settings_dialog()
        else:
            # Switch back to local engine
            self.engine_combo.set(ENGINE_OPTIONS[0][1])
            self._on_engine_changed()

    def open_settings_dialog(self):
        """Settings window for API Key and options."""
        dlg = tk.Toplevel(self)
        dlg.title("⚙️ Gemini Cloud API Key (Optional)")
        dlg.geometry("520x330")
        dlg.configure(bg="#0f172a")
        dlg.transient(self)
        dlg.grab_set()

        tk.Label(
            dlg,
            text="⚙️ Cloud API Key (Optional)",
            font=("Segoe UI", 13, "bold"),
            bg="#0f172a",
            fg="#f8fafc"
        ).pack(anchor="w", padx=20, pady=(15, 5))

        tk.Label(
            dlg,
            text="Note: AuraVoice works 100% offline with NO API key needed when using the Local Engine.\nEnter a key only if you want to use Google Gemini Cloud Vision.",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94a3b8",
            wraplength=480,
            justify=tk.LEFT
        ).pack(anchor="w", padx=20, pady=(0, 15))

        key_frame = tk.Frame(dlg, bg="#1e293b", bd=1, relief=tk.SOLID)
        key_frame.pack(fill=tk.X, padx=20, pady=5)

        inner = tk.Frame(key_frame, bg="#1e293b")
        inner.pack(fill=tk.X, padx=12, pady=10)

        tk.Label(
            inner,
            text="Gemini API Key:",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#cbd5e1"
        ).pack(anchor="w")

        key_entry_box = tk.Frame(inner, bg="#1e293b")
        key_entry_box.pack(fill=tk.X, pady=(4, 0))

        key_entry = tk.Entry(
            key_entry_box,
            font=("Segoe UI", 10),
            bg="#0f172a",
            fg="#f8fafc",
            insertbackground="#38bdf8",
            relief=tk.FLAT,
            show="•"
        )
        key_entry.insert(0, self.config.get("gemini_api_key", ""))
        key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        show_var = tk.BooleanVar(value=False)
        def toggle_show():
            key_entry.config(show="" if show_var.get() else "•")

        show_cb = tk.Checkbutton(
            key_entry_box,
            text="Show",
            variable=show_var,
            bg="#1e293b",
            fg="#94a3b8",
            activebackground="#1e293b",
            activeforeground="#f8fafc",
            selectcolor="#0f172a",
            font=("Segoe UI", 8),
            command=toggle_show
        )
        show_cb.pack(side=tk.RIGHT, padx=(6, 0))

        link_lbl = tk.Label(
            dlg,
            text="Get a free Gemini API Key at: https://aistudio.google.com/apikey",
            font=("Segoe UI", 8, "underline"),
            bg="#0f172a",
            fg="#38bdf8",
            cursor="hand2"
        )
        link_lbl.pack(anchor="w", padx=20, pady=(6, 12))
        link_lbl.bind("<Button-1>", lambda e: self._open_browser("https://aistudio.google.com/apikey"))

        def save_and_close():
            new_key = key_entry.get().strip()
            self.config["gemini_api_key"] = new_key
            save_config(self.config)
            self.cloud_vision_engine.set_api_key(new_key)
            dlg.destroy()
            if new_key:
                self._update_status("🟢 Gemini API Key Saved!", "#10b981")
                messagebox.showinfo("Success", "Gemini API Key saved successfully!")

        btn_bar = tk.Frame(dlg, bg="#0f172a")
        btn_bar.pack(fill=tk.X, padx=20, pady=10)

        cancel_btn = tk.Button(
            btn_bar,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#f8fafc",
            relief=tk.FLAT,
            padx=14,
            pady=4,
            command=dlg.destroy
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(6, 0))

        save_btn = tk.Button(
            btn_bar,
            text="Save Settings",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=18,
            pady=4,
            command=save_and_close
        )
        save_btn.pack(side=tk.RIGHT)

    def _open_browser(self, url: str):
        import webbrowser
        webbrowser.open(url)

    def _on_close(self):
        """Clean up threads and stop engines when exiting."""
        self.is_live_watch_active = False
        self.tts_engine.stop()
        self.voice_command_listener.stop()
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
        self.destroy()
        sys.exit(0)
