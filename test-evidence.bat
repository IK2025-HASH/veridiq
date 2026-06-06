@echo off
REM ============================================================
REM  Verid-iq — generate test-run evidence
REM  Produces reports\report.html (readable) + reports\junit.xml (CI/audit).
REM  Run from the activated venv (the same one you run pytest in).
REM  Output is gitignored — regenerate any time.
REM ============================================================

cd /d "%~dp0"
if not exist reports mkdir reports

echo.
echo  Running tests and writing evidence to .\reports ...
echo.

python -m pytest tests/ -v ^
  --junitxml=reports\junit.xml ^
  --html=reports\report.html --self-contained-html

echo.
echo  ============================================
echo   Evidence written:
echo     reports\report.html   (open in a browser)
echo     reports\junit.xml     (CI / audit format)
echo  ============================================
echo.
pause
