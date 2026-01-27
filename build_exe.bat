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

REM ---- Verify dist output ----
echo.
echo Verifying build output...

set "VERIFY_OK=1"

if not exist "dist\JanDocumentPlugin\JanDocumentPlugin.exe" (
    echo   [FAIL] JanDocumentPlugin.exe missing
    set "VERIFY_OK=0"
) else (
    echo   [OK] JanDocumentPlugin.exe
)

if not exist "dist\JanDocumentPlugin\chat_ui.html" (
    echo   [FAIL] chat_ui.html missing
    set "VERIFY_OK=0"
) else (
    echo   [OK] chat_ui.html
)

if not exist "dist\JanDocumentPlugin\config.env" (
    echo   [WARN] config.env missing (will use defaults)
) else (
    echo   [OK] config.env
)

if not exist "dist\JanDocumentPlugin\rollback_jan.ps1" (
    echo   [WARN] rollback_jan.ps1 missing
) else (
    echo   [OK] rollback_jan.ps1
)

if not exist "dist\JanDocumentPlugin\calibration\JanDocPlugin_Calibration.pdf" (
    echo   [WARN] Calibration PDF missing
) else (
    echo   [OK] Calibration PDF
)

if "%VERIFY_OK%"=="0" (
    echo.
    echo WARNING: Some required files are missing from the dist output.
    echo The build may be incomplete.
)

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
echo     1. Stage LLM files in installer\llm\ and installer\models\
echo     2. Run: build_installer.bat
echo        (validates everything and compiles the Inno Setup installer)
echo.
echo ========================================================================
echo.

pause
