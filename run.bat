@echo off
REM Start Tetrabot with the local virtual environment.
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Create it first:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

.venv\Scripts\python.exe -m tetrabot
pause

