@echo off
rem Japanese Web UI (voice library / duration slider / SRT export)
call "%~dp0_env.bat"
if not exist "%UPSTREAM_DIR%" (echo Run setup.bat first. & pause & exit /b 1)
cd /d "%ROOT%"
uv run --project "%UPSTREAM_DIR%" --no-sync python "%ROOT%\app\app_ja.py" --open
pause
