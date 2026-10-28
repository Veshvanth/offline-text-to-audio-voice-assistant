import json
import os
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"

DEFAULT_CONFIG = {
    "engine": "local",  # "local" (No API Key Required) or "gemini" (Cloud Vision)
    "gemini_api_key": "",
    "model_name": "gemini-2.5-flash",
    "voice": "en-US-JennyNeural",
    "speed": 1.0,
    "pitch": 0,
    "volume": 1.0,
    "assistant_mode": "direct",  # "direct", "explain", "summary", "math"
    "auto_play": True,
    "always_on_top": True,
    "voice_commands_enabled": True,
    "hotkey": "ctrl+shift+s"
}

VOICE_OPTIONS = [
    {"id": "en-US-JennyNeural", "name": "Jenny (US English, Female, Natural)", "gender": "Female", "lang": "en-US"},
    {"id": "en-US-GuyNeural", "name": "Guy (US English, Male, Clear)", "gender": "Male", "lang": "en-US"},
    {"id": "en-US-AriaNeural", "name": "Aria (US English, Female, Expressive)", "gender": "Female", "lang": "en-US"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher (US English, Male, Calm)", "gender": "Male", "lang": "en-US"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (UK English, Female, Articulate)", "gender": "Female", "lang": "en-GB"},
    {"id": "en-GB-RyanNeural", "name": "Ryan (UK English, Male, Professional)", "gender": "Male", "lang": "en-GB"},
    {"id": "en-IN-NeerjaNeural", "name": "Neerja (Indian English, Female, Soft)", "gender": "Female", "lang": "en-IN"},
    {"id": "en-IN-PrabhatNeural", "name": "Prabhat (Indian English, Male, Warm)", "gender": "Male", "lang": "en-IN"},
    {"id": "en-AU-NatashaNeural", "name": "Natasha (Australian English, Female)", "gender": "Female", "lang": "en-AU"},
]

MODE_OPTIONS = [
    ("direct", "Exact Read Aloud", "Transcribes screen text/handwriting word-for-word and speaks it aloud."),
    ("explain", "Smart Voice Assistant", "Reads handwriting/text and explains the concepts clearly in spoken voice."),
    ("summary", "Key Points Summary", "Summarizes the screen notes into concise spoken bullet points."),
    ("math", "Math & Equation Narrator", "Translates handwritten formulas into clear spoken mathematical language."),
]

ENGINE_OPTIONS = [
    ("local", "🔒 Local Engine (No API Key Required)", "100% offline, private, runs on your PC with EasyOCR."),
    ("gemini", "☁️ Gemini Cloud Vision", "Google Cloud AI for handwriting analysis & conversational explanation.")
]

def load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception as e:
            print(f"Error loading config: {e}")
            
    # Also check system environment variable as fallback
    if not config.get("gemini_api_key"):
        env_key = os.environ.get("GEMINI_API_KEY", "")
        if env_key:
            config["gemini_api_key"] = env_key
            
    return config

def save_config(config: dict) -> bool:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
