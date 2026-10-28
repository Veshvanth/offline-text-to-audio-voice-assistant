# 🎙️ AuraVoice AI — Live Screen & Handwriting Voice Assistant

**AuraVoice AI** is an intelligent desktop voice assistant that turns screen text and **human handwriting** into natural, live spoken audio with **real-time speed adjustability** and **hands-free voice commands**.

It can run **100% locally with NO API keys required**, completely offline and private on your PC.

---

## ✨ What's New: Hands-Free Voice Commands & No-API-Key Engine!

### 🔒 100% Free / No API Key Engine (Default)
- **Local Engine (EasyOCR)**: Runs locally on your computer with **zero API keys**, zero subscriptions, and complete offline privacy.
- **Optional Cloud Gemini Vision**: Toggle to Google Cloud Gemini when you want conversational explanations, summaries, or math narrator modes.

### 🎤 Hands-Free Voice Commands
Control the assistant completely with your voice while working, studying, or reading:

| Voice Command | What It Does |
| :--- | :--- |
| **"Pause"** / **"Hold on"** / **"Wait"** | Pauses speech playback |
| **"Continue"** / **"Resume"** / **"Play"** | Resumes speech playback |
| **"Stop"** / **"Quiet"** / **"Silence"** | Stops speech immediately |
| **"Next"** / **"Next paragraph"** / **"Next page"** | Jumps forward to the next paragraph and reads it |
| **"Previous"** / **"Back"** / **"Last paragraph"** | Jumps back to the previous paragraph |
| **"Faster"** / **"Speed up"** | Increases reading speed (+0.25x) |
| **"Slower"** / **"Slow down"** | Decreases reading speed (-0.25x) |
| **"Repeat"** / **"Replay"** / **"Read again"** | Replays current paragraph |
| **"Snip"** / **"Capture"** / **"Read screen"** | Triggers screen snipping overlay |

---

## ⚡ Core Features

- ✍️ **Human Handwriting & Cursive Recognition**:
  - Deciphers student notes, teacher feedback, whiteboard notes, stylus handwriting in OneNote/Paint, and typed screen text.
  - Automatic ink enhancement filter sharpens light pencil/pen strokes.
- ⚡ **Real-Time Speed Adjustability (0.5x to 2.5x)**:
  - Drag the fluid speed slider or use quick chips (`0.75x`, `1.0x`, `1.25x`, `1.5x`, `2.0x`).
  - Say *"faster"* or *"slower"* to adjust speed on the fly!
- 📖 **Paragraph & Page Reader Navigation**:
  - Breaks recognized text into paragraphs with visual highlighting showing you the exact sentence being spoken.
  - Skip ahead or jump back using buttons or voice commands.
- 🗣️ **Natural High-Definition AI Voices**:
  - Powered by neural text-to-speech voices across accents (US, UK, Indian, Australian) with zero API keys required.
- 🎨 **Built-in Handwriting Scratchpad**:
  - Test handwriting directly inside the app with your mouse, stylus, or drawing tablet.
- ⌨️ **Global Shortcut**:
  - Press `Ctrl + Shift + S` or `Alt + S` from any window in Windows to snip and read.
- 💾 **Export Audio (.mp3)**:
  - Save synthesized speech directly to an audio file.

---

## 🚀 Quick Start

### 1. Launch AuraVoice
Double-click `run.bat` or run:
```powershell
.\.venv\Scripts\python.exe main.py
```

### 2. Using Without Any API Key (Default)
The app starts with **Local Engine (No API Key Required)** selected. You do **not** need to enter any API keys or sign up for any account!

App settings are saved locally in `config.json`. This file is excluded from Git because it can contain your Gemini API key.

### 3. Start Reading!
1. Click **✂️ Snip & Read** (or press `Ctrl + Shift + S`).
2. Drag a rectangle over any handwriting or text on your screen.
3. AuraVoice will transcribe the text and read it aloud immediately!
4. Say **"pause"**, **"continue"**, **"next"**, or **"faster"** to control it with your voice.

---

## 🛠️ Project Structure

```
project 1/
│
├── aura_voice/
│   ├── __init__.py
│   ├── config.py              # Configuration & persistent options
│   ├── local_ocr.py           # 100% Offline No-Key Handwriting & Screen OCR
│   ├── ai_vision.py           # Cloud Gemini Vision Engine (Optional)
│   ├── voice_commands.py      # Real-time microphone voice commands listener
│   ├── tts_engine.py          # Neural TTS with speed control & playback
│   ├── screen_capture.py      # DPI-aware screen snipper & live monitor
│   ├── scratchpad.py          # Mouse & stylus drawing canvas
│   ├── audio_visualizer.py    # Animated equalizer waves widget
│   └── gui.py                 # Modern desktop user interface
│
├── main.py                    # App launcher
├── run.bat                    # One-click Windows batch script
├── requirements.txt           # Python dependencies
└── README.md                  # Documentation & Voice Command Guide
```
