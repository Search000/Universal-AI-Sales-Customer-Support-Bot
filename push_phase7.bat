@echo off
REM ============================================
REM  Phase 7 push helper — just double-click this
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

echo.
echo [3/4] Going back to project folder...
cd ..

echo.
echo [4/4] Pushing to GitHub...
git add -A
git commit -m "Phase 7: order engine"
git push

echo.
echo ============================================
echo   DONE. Scroll up and check for any red
echo   ERROR lines. If everything looks OK,
echo   you can close this window.
echo ============================================
pause
