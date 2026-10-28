import threading
import time
from typing import Callable, Optional
import speech_recognition as sr


class VoiceCommandListener:
    """
    Listens for spoken voice commands via the microphone in real-time
    to control playback, speed, navigation (next/prev paragraph), and snipping.
    """
    COMMAND_PATTERNS = {
        "pause": ["pause", "wait", "hold on", "pause speech", "paws"],
        "resume": ["continue", "resume", "play", "start", "keep going", "proceed"],
        "stop": ["stop", "quiet", "shut up", "silence", "cancel", "halt"],
        "next_para": ["next", "next paragraph", "next para", "next page", "forward", "skip"],
        "prev_para": ["previous", "previous paragraph", "back", "prev", "last paragraph", "go back"],
        "faster": ["faster", "speed up", "quicker", "fast", "increase speed"],
        "slower": ["slower", "slow down", "decrease speed", "slow"],
        "replay": ["repeat", "replay", "read again", "again", "restart"],
        "snip": ["snip", "capture", "read screen", "screen", "take snip"]
    }

    def __init__(self, on_command: Callable[[str, str], None], on_status: Optional[Callable[[str], None]] = None):
        self.on_command = on_command
        self.on_status = on_status

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.6

        self.is_running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start listening for voice commands in a background daemon thread."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        if self.on_status:
            self.on_status("🎤 Voice Commands: Listening...")

    def stop(self):
        """Stop microphone listening."""
        self.is_running = False
        if self.on_status:
            self.on_status("🎤 Voice Commands: Off")

    def toggle(self) -> bool:
        """Toggle between listening and off. Returns new state."""
        if self.is_running:
            self.stop()
            return False
        else:
            self.start()
            return True

    def _listen_loop(self):
        try:
            with sr.Microphone() as source:
                # Calibrate ambient noise level
                try:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                except Exception as e:
                    print(f"Noise adjust notice: {e}")

                while self.is_running:
                    try:
                        # Listen for short command phrases
                        audio = self.recognizer.listen(source, timeout=2.0, phrase_time_limit=3.0)
                        if not self.is_running:
                            break

                        # Transcribe speech using built-in Google Web Speech API (free, zero API key)
                        phrase = self.recognizer.recognize_google(audio).strip().lower()

                        if phrase:
                            cmd = self._parse_command(phrase)
                            if cmd:
                                if self.on_status:
                                    self.on_status(f"⚡ Command: {cmd.upper()} (heard: '{phrase}')")
                                self.on_command(cmd, phrase)

                    except sr.WaitTimeoutError:
                        # Normal timeout when silence
                        continue
                    except sr.UnknownValueError:
                        # Speech not understood
                        continue
                    except Exception as e:
                        time.sleep(0.5)

        except Exception as e:
            print(f"VoiceCommandListener error: {e}")
            if self.on_status:
                self.on_status(f"🎤 Mic Error: {e}")
            self.is_running = False

    def _parse_command(self, phrase: str) -> Optional[str]:
        """Match spoken phrase against registered commands."""
        # Check longest matching patterns first
        for cmd, patterns in self.COMMAND_PATTERNS.items():
            for pat in patterns:
                # Direct word or phrase match
                if pat in phrase.split() or pat == phrase:
                    return cmd
                # Substring check for compound phrases
                if len(pat.split()) > 1 and pat in phrase:
                    return cmd
        return None

