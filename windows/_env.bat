@echo off
chcp 65001 >nul
rem Common settings. Override by setting variables before running.
set "ROOT=%~dp0.."
if not defined UPSTREAM_URL set "UPSTREAM_URL=https://github.com/Aratako/Irodori-TTS.git"
if not defined UPSTREAM_REF set "UPSTREAM_REF=main"
if not defined BACKEND set "BACKEND=cu128"
if not defined MODEL set "MODEL=Aratako/Irodori-TTS-v4.1-Small"
set "UPSTREAM_DIR=%ROOT%\Irodori-TTS"
rem Keep model cache inside this folder (easy to delete / move)
if not defined HF_HOME set "HF_HOME=%ROOT%\hf_cache"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
set "PYTHONUTF8=1"
