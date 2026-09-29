@echo off
rem Web UI (voice cloning). Opens http://localhost:7860
call "%~dp0_env.bat"
if not exist "%UPSTREAM_DIR%" (echo Run setup.bat first. & pause & exit /b 1)
cd /d "%UPSTREAM_DIR%"
start "" http://localhost:7860
uv run --no-sync python gradio_app.py --server-name 127.0.0.1 --server-port 7860
pause
