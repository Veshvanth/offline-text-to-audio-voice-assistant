#!/usr/bin/env python3
"""
AuraVoice AI - Live Screen Text & Handwriting to Audio Voice Assistant
Run this file to start the desktop assistant.
"""
import sys
import os

# Ensure current directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aura_voice.gui import AuraVoiceApp

def main():
    try:
        app = AuraVoiceApp()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nExiting AuraVoice AI...")
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

