import asyncio
import os
import tempfile
import threading
from typing import Callable, Optional
import edge_tts
import pygame


def format_rate(speed_multiplier: float) -> str:
    """
    Convert speed multiplier (e.g. 0.5 to 2.5) to edge-tts rate string
    e.g. 1.0 -> "+0%", 1.5 -> "+50%", 0.75 -> "-25%"
    """
    percent = int(round((speed_multiplier - 1.0) * 100))
    if percent >= 0:
        return f"+{percent}%"
    return f"{percent}%"


def format_pitch(pitch_hz: int) -> str:
    """Convert pitch Hz adjustment to edge-tts pitch string."""
    if pitch_hz >= 0:
        return f"+{pitch_hz}Hz"
    return f"{pitch_hz}Hz"


class TTSEngine:
    def __init__(self,
                 on_start: Optional[Callable[[], None]] = None,
                 on_finish: Optional[Callable[[], None]] = None,
                 on_error: Optional[Callable[[str], None]] = None):
        self.on_start = on_start
        self.on_finish = on_finish
        self.on_error = on_error

        self.current_audio_file: Optional[str] = None
        self.is_paused = False
        self._is_generating = False
        self._stop_requested = False
        self._playback_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None

        # Initialize pygame mixer
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception as e:
            print(f"Error initializing pygame mixer: {e}")

    def speak(self, text: str, voice: str = "en-US-JennyNeural", speed: float = 1.0, pitch: int = 0, volume: float = 1.0):
        """
        Synthesize speech from text and play it immediately with the specified speed.
        """
        if not text or not text.strip():
            return

        # Stop any ongoing playback
        self.stop()
        self._stop_requested = False
        self.is_paused = False

        # Start synthesis and playback in background thread
        thread = threading.Thread(
            target=self._generate_and_play,
            args=(text.strip(), voice, speed, pitch, volume),
            daemon=True
        )
        self._playback_thread = thread
        thread.start()

    def _generate_and_play(self, text: str, voice: str, speed: float, pitch: int, volume: float):
        self._is_generating = True
        try:
            rate_str = format_rate(speed)
            pitch_str = format_pitch(pitch)

            # Create a dedicated temp mp3 file
            temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3", prefix="auravoice_")
            os.close(temp_fd)

            # Generate audio using asyncio edge-tts
            async def run_tts():
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=rate_str,
                    pitch=pitch_str
                )
                await communicate.save(temp_path)

            asyncio.run(run_tts())

            if self._stop_requested:
                self._safe_remove_file(temp_path)
                return

            self.current_audio_file = temp_path
            self._is_generating = False

            # Start playback via pygame
            pygame.mixer.music.load(self.current_audio_file)
            pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
            pygame.mixer.music.play()

            if self.on_start:
                self.on_start()

            # Monitor until audio playback completes
            while pygame.mixer.music.get_busy() or self.is_paused:
                if self._stop_requested:
                    pygame.mixer.music.stop()
                    break
                pygame.time.Clock().tick(15)

            # Cleanup
            if hasattr(pygame.mixer.music, "unload"):
                pygame.mixer.music.unload()

            if not self._stop_requested and self.on_finish:
                self.on_finish()

        except Exception as e:
            self._is_generating = False
            print(f"TTS Error: {e}")
            if self.on_error:
                self.on_error(f"Speech error: {e}")
            if self.on_finish:
                self.on_finish()

    def pause(self):
        """Pause current playback."""
        if pygame.mixer.music.get_busy() and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True

    def resume(self):
        """Resume paused playback."""
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False

    def toggle_pause(self):
        """Toggle between pause and resume."""
        if self.is_paused:
            self.resume()
            return False  # not paused
        else:
            self.pause()
            return True   # paused

    def stop(self):
        """Stop current playback and reset state."""
        self._stop_requested = True
        self.is_paused = False
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                if hasattr(pygame.mixer.music, "unload"):
                    pygame.mixer.music.unload()
        except Exception:
            pass

        # Cleanup old audio file
        if self.current_audio_file:
            self._safe_remove_file(self.current_audio_file)
            self.current_audio_file = None

    def set_volume(self, volume: float):
        """Adjust volume 0.0 to 1.0."""
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
        except Exception:
            pass

    def is_playing(self) -> bool:
        """Returns True if audio is playing or currently being generated."""
        return self._is_generating or (pygame.mixer.get_init() and pygame.mixer.music.get_busy())

    def save_current_audio_to_file(self, destination_path: str) -> bool:
        """Export the last synthesized audio file to a user specified destination."""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            return False
        try:
            import shutil
            shutil.copy2(self.current_audio_file, destination_path)
            return True
        except Exception as e:
            print(f"Error exporting audio: {e}")
            return False

    def _safe_remove_file(self, path: str):
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

