@echo off
REM ============================================================================
REM Build Windows Executable for Jan Document Plugin v2.0.0-beta
REM ============================================================================
REM Prerequisites:
REM   - Python 3.12 (onnxruntime requires it)
REM   - All dependencies installed (run install.bat first)
REM   - PyInstaller: pip install pyinstaller
REM
REM This script:
REM   1. Builds the standalone .exe with PyInstaller
REM   2. Copies Chat UI, rollback helper, and new data files
REM   3. Creates llm/ and models/ staging directories
REM   4. Prepares all files needed for the Inno Setup installer
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ========================================================================
echo    Building Jan Document Plugin v2.0.0-beta
echo ========================================================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install required packages if not present
echo Checking dependencies...
pip show pyinstaller >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

pip show pillow >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing Pillow for icon generation...
    pip install pillow
)

REM Generate icon if it doesn't exist
if not exist "assets\icon.ico" (
    echo.
    echo Generating application icon...
    python assets\create_icon.py
    if %ERRORLEVEL% NEQ 0 (
        echo WARNING: Could not generate icon, using default
    )
)

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build the executable
echo.
echo Building executable with PyInstaller...
echo This may take several minutes...
echo.

pyinstaller JanDocumentPlugin.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

REM Copy additional files to dist folder
echo.
echo Copying additional files...

REM Config file (example version for fresh installs)
copy config.env.example dist\JanDocumentPlugin\config.env >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    copy config.env dist\JanDocumentPlugin\ >nul 2>nul
)

REM Chat UI
copy chat_ui.html dist\JanDocumentPlugin\ >nul 2>nul

REM Jan rollback helper
copy rollback_jan.ps1 dist\JanDocumentPlugin\ >nul 2>nul

REM Documentation
copy README.md dist\JanDocumentPlugin\ >nul 2>nul
copy LICENSE dist\JanDocumentPlugin\ >nul 2>nul

REM Create calibration folder and copy test PDF
mkdir dist\JanDocumentPlugin\calibration 2>nul
copy calibration\JanDocPlugin_Calibration.pdf dist\JanDocumentPlugin\calibration\ >nul 2>nul

REM Create tesseract folder placeholder
mkdir dist\JanDocumentPlugin\tesseract 2>nul
echo Tesseract OCR files can be placed here for portable installation > dist\JanDocumentPlugin\tesseract\README.txt

REM Create data directory
mkdir dist\JanDocumentPlugin\jan_doc_store 2>nul

REM Create llm/ and models/ staging directories for bundled LLM
mkdir dist\JanDocumentPlugin\llm 2>nul
echo Place llama-server.exe and Vulkan DLLs here > dist\JanDocumentPlugin\llm\README.txt
mkdir dist\JanDocumentPlugin\models 2>nul
echo Place GGUF model files here > dist\JanDocumentPlugin\models\README.txt

REM Create installer output directory
mkdir dist\installer 2>nul

echo.
echo ========================================================================
echo    Build Complete!
echo ========================================================================
echo.
echo Executable: dist\JanDocumentPlugin\JanDocumentPlugin.exe
echo.
echo NEXT STEPS:
echo.
echo   Option 1 - Direct Distribution:
echo     Copy the entire dist\JanDocumentPlugin folder
echo.
echo   Option 2 - Create Installer (Recommended):
echo     1. Install Inno Setup: https://jrsoftware.org/isinfo.php
echo     2. Stage llm/ and models/ in installer\ directory
echo     3. Open installer\setup.iss in Inno Setup
echo     4. Compile to create JanDocumentPlugin_Setup_2.0.0-beta.exe
echo.
echo ========================================================================
echo.

pause
