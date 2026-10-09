@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" -m streamlit run "%~dp0app.py"
) else (
  python -m streamlit run "%~dp0app.py"
)
