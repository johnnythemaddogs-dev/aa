@echo off
setlocal
call "%~dp0_env.bat"

where git >nul 2>nul || (echo [ERROR] git not found. Install: winget install Git.Git & pause & exit /b 1)
where uv >nul 2>nul
if errorlevel 1 (
  echo Installing uv...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" || (pause & exit /b 1)
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

if not exist "%UPSTREAM_DIR%\.git" git clone "%UPSTREAM_URL%" "%UPSTREAM_DIR%" || (pause & exit /b 1)
git -C "%UPSTREAM_DIR%" fetch --tags origin
git -C "%UPSTREAM_DIR%" checkout %UPSTREAM_REF% || (pause & exit /b 1)
if /i "%UPSTREAM_REF%"=="main" git -C "%UPSTREAM_DIR%" pull --ff-only origin main

cd /d "%UPSTREAM_DIR%"
uv sync --extra %BACKEND% || (echo [ERROR] uv sync failed & pause & exit /b 1)

if not "%SKIP_MODEL%"=="1" (
  uv run --no-sync python -c "from huggingface_hub import snapshot_download as s; print(s('%MODEL%'))" || (pause & exit /b 1)
)
echo.
echo Setup done. Double-click start.bat to launch the Web UI.
pause
