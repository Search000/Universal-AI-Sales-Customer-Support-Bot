@echo off
REM ============================================
REM  Phase 12 push helper — just double-click this
REM  Fully automatic: installs deps, tests, commits, pushes.
REM ============================================
cd /d "%~dp0"

echo.
echo [1/4] Installing dependencies...
cd backend
pip install -r requirements.txt

echo.
echo [2/4] Running tests...
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest -q
if errorlevel 1 (
    echo.
    echo ============================================
    echo   TESTS FAILED. Not pushing broken code.
    echo   Scroll up, fix the red errors, run again.
    echo ============================================
    pause
    exit /b 1
)

echo.
echo [3/4] Going back to project folder...
cd ..

echo.
echo [4/4] Committing and pushing to GitHub...
git add -A
git commit -m "Phase 12: Owner dashboard - Analytics (Phase 12 complete)"
git push

echo.
echo ============================================
echo   DONE. Scroll up and check for any red
echo   ERROR lines. If everything looks OK,
echo   you can close this window.
echo ============================================
pause
