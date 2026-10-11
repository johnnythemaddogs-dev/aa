@echo off
rem Remotion version: drag the narration .wav and the palm image onto this file together.
rem Needs Node.js (https://nodejs.org). First run installs packages (npm install).
call "%~dp0_env.bat"
set "RDIR=%ROOT%\remotion"
set "AUDIO="
set "PALM="
for %%F in (%*) do (
  if /i "%%~xF"==".wav" set "AUDIO=%%~fF"
  if /i "%%~xF"==".png" set "PALM=%%~fF"
)
if not defined AUDIO (echo wav ファイルを一緒にドロップしてください。 & pause & exit /b 1)
if not defined PALM (echo 手のひら画像 png を一緒にドロップしてください。 & pause & exit /b 1)
copy /y "%AUDIO%" "%RDIR%\public\narration.wav" >nul
copy /y "%PALM%" "%RDIR%\public\palm.png" >nul
cd /d "%RDIR%"
if not exist node_modules call npm install
if "%STUDIO%"=="1" (call npx remotion studio) else (call npx remotion render TesouTaiyousen "%AUDIO:~0,-4%.mp4")
pause
