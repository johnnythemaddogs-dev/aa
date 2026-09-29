@echo off
rem Web UI (VoiceDesign: describe the voice with a caption). Opens http://localhost:7861
call "%~dp0_env.bat"
if not exist "%UPSTREAM_DIR%" (echo Run setup.bat first. & pause & exit /b 1)
cd /d "%UPSTREAM_DIR%"
start "" http://localhost:7861
uv run --no-sync python gradio_app_voicedesign.py --server-name 127.0.0.1 --server-port 7861
pause
