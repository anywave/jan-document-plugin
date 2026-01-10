@echo off
REM ============================================================================
REM Download and Install Portable Tesseract OCR
REM ============================================================================
REM This script downloads Tesseract to a local 'tesseract' folder
REM so you don't need admin rights or system-wide installation.
REM ============================================================================

setlocal EnableDelayedExpansion

set "APP_DIR=%~dp0"
set "TESSERACT_DIR=%APP_DIR%tesseract"

echo.
echo ========================================================================
echo    Tesseract OCR - Portable Installation
echo ========================================================================
echo.

if exist "%TESSERACT_DIR%\tesseract.exe" (
    echo Tesseract already installed at: %TESSERACT_DIR%
    echo.
    echo To reinstall, delete the 'tesseract' folder and run this again.
    pause
    exit /b 0
)

echo This script will download and install Tesseract OCR to:
echo   %TESSERACT_DIR%
echo.
echo Download size: ~70MB
echo.

set /p CONFIRM="Continue? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Installation cancelled.
    pause
    exit /b 0
)

echo.
echo Checking for curl...

where curl >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: curl not found. Please install curl or download Tesseract manually.
    echo.
    echo Manual download:
    echo   https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    pause
    exit /b 1
)

REM Create tesseract directory
mkdir "%TESSERACT_DIR%" 2>nul

REM Download URL for Tesseract portable/installer
set "TESSERACT_URL=https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
set "INSTALLER=%TESSERACT_DIR%\tesseract-installer.exe"

echo.
echo Downloading Tesseract...
echo URL: %TESSERACT_URL%
echo.

curl -L -o "%INSTALLER%" "%TESSERACT_URL%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Download failed!
    echo.
    echo Please download manually from:
    echo   https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo    Download Complete!
echo ========================================================================
echo.
echo The Tesseract installer has been downloaded to:
echo   %INSTALLER%
echo.
echo Please run the installer and:
echo   1. Choose "Install for current user only" (no admin required)
echo   2. Install to: %TESSERACT_DIR%
echo   3. Select "Add to PATH" if prompted
echo.
echo Starting installer...
echo.

start "" "%INSTALLER%"

echo.
echo After installation completes:
echo   1. Update config.env with:
echo      TESSERACT_PATH=%TESSERACT_DIR%\tesseract.exe
echo.
echo   2. Restart the Jan Document Plugin
echo.

pause
