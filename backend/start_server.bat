@echo off
REM Double-click this to start the bot server on this PC.
REM Keeps running until you close this window (or Ctrl+C).
REM For it to survive after you log out / restart, set this up as a
REM Windows Task Scheduler task instead (see docs/HOSTING_ON_YOUR_PC.md).

cd /d "%~dp0"
python run_production.py
pause
