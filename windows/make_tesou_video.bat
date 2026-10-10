@echo off
rem Palm-reading short video: drag the narration .wav and the palm image onto this file together.
rem Optional: set SUNLINE=..., TIMINGS=edited.srt, PREVIEW=1 (stills only) before running.
call "%~dp0_env.bat"
set "AUDIO="
set "PALM="
for %%F in (%*) do (
  if /i "%%~xF"==".wav" set "AUDIO=%%~fF"
  if /i "%%~xF"==".png" set "PALM=%%~fF"
  if /i "%%~xF"==".jpg" set "PALM=%%~fF"
  if /i "%%~xF"==".jpeg" set "PALM=%%~fF"
)
if not defined AUDIO (echo wav ファイルを一緒にドロップしてください。 & pause & exit /b 1)
if not defined PALM (echo 手のひら画像 png/jpg を一緒にドロップしてください。 & pause & exit /b 1)
set "OPTS="
if defined SUNLINE set OPTS=%OPTS% --sunline "%SUNLINE%"
if defined TIMINGS set OPTS=%OPTS% --timings "%TIMINGS%"
if "%PREVIEW%"=="1" set OPTS=%OPTS% --preview
uv run --no-project --with pillow --with numpy --with soundfile --with imageio-ffmpeg python "%ROOT%\video\tesou_taiyousen.py" "%AUDIO%" "%PALM%" %OPTS%
pause
