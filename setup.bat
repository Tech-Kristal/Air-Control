@echo off
setlocal
cd /d "%~dp0"
echo =====================================
echo          AirControl V3 Setup
echo =====================================

set PYVER=
for %%V in (3.15 3.14 3.13 3.12) do (
    if not defined PYVER (
        py -%%V --version >nul 2>&1
        if not errorlevel 1 set PYVER=%%V
    )
)
if not defined PYVER (
    echo Python 3.12 - 3.15 ^(64-bit^) was not found.
    echo Install Python 3.15.2 from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo Using Python %PYVER%

if not exist ".venv\Scripts\python.exe" (
    py -%PYVER% -m venv .venv
    if errorlevel 1 goto error
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto error
pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo Downloading hand tracking model ^(one time, about 8 MB^)...
python -m aircontrol.model_manager
if errorlevel 1 goto error

echo.
echo Setup complete. Run run.bat.
pause
exit /b 0
:error
echo Setup failed. Review the error above.
pause
exit /b 1
