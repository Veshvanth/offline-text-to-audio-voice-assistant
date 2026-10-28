@echo off
title AuraVoice AI - Live Screen & Handwriting Voice Assistant
echo Starting AuraVoice AI...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    python main.py
)
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred while running AuraVoice AI.
    pause
)

