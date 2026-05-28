@echo off
chcp 65001 >nul
echo.
echo ==========================================================
echo    SSH Tunnel Manager -- Build Script (Windows/Python)
echo ==========================================================
echo.

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed!
    echo  Download at: https://www.python.org/downloads/
    echo  Choose: Python 3.11+ - Windows x64
    echo  Make sure to tick "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] %PYVER%
echo.

:: Check pip packages
echo  [1/4] Checking dependencies...
python -c "import cryptography" >nul 2>&1
if errorlevel 1 (
    echo  Installing cryptography...
    pip install cryptography -q
)

python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo  Installing PyInstaller...
    pip install pyinstaller -q
)

echo  [OK] Dependencies are ready
echo.

:: Remove old build cache
echo  [2/4] Cleaning old build cache...
if exist build rmdir /s /q build
if exist publish\windows rmdir /s /q publish\windows
echo  [OK] Cache cleaned
echo.

:: Build
echo  [3/4] Building SshTunnelManager.exe...
pyinstaller SshTunnelManager.spec ^
    --distpath publish\windows ^
    --workpath build ^
    --noconfirm ^
    --clean

if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo  [4/4] Build completed!
echo.
echo ==========================================================
echo                    BUILD SUCCESSFUL
echo ==========================================================
echo.
echo  Output: publish\windows\SshTunnelManager.exe
echo.

:: Check required files
if exist publish\windows\plink.exe (
    echo  [OK] plink.exe found
) else (
    echo  [!] MISSING: plink.exe
    echo      Copy to: publish\windows\plink.exe
)

if exist publish\windows\default_vps.ppk (
    echo  [OK] default_vps.ppk found
) else (
    echo  [!] MISSING: default_vps.ppk
    echo      Copy to: publish\windows\default_vps.ppk
)

echo.
echo  Distribution folder:
echo    publish\windows\
echo    +-- SshTunnelManager.exe
echo    +-- plink.exe
echo    +-- default_vps.ppk (or .ppk.enc)
echo.
echo ==========================================================
echo.
pause