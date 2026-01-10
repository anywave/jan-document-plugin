@echo off
REM ============================================================================
REM Jan Document Plugin - Interactive Tutorial & Setup Wizard
REM ============================================================================
REM Guides users through first-time setup and verification
REM ============================================================================

setlocal EnableDelayedExpansion

set "INSTALL_DIR=%~dp0"
cd /d "%INSTALL_DIR%"

:main_menu
cls
echo.
echo ========================================================================
echo    Jan Document Plugin - Setup Wizard v1.2.0
echo ========================================================================
echo.
echo   Welcome! This wizard will help you set up and verify the plugin.
echo.
echo   What would you like to do?
echo.
echo   [1] First-Time Setup (Recommended for new users)
echo   [2] Verify Installation
echo   [3] Test PDF Extraction
echo   [4] Troubleshooting Guide
echo   [5] View Configuration
echo   [6] Exit
echo.
set /p "choice=Enter your choice (1-6): "

if "%choice%"=="1" goto :first_time_setup
if "%choice%"=="2" goto :verify_installation
if "%choice%"=="3" goto :test_extraction
if "%choice%"=="4" goto :troubleshooting
if "%choice%"=="5" goto :view_config
if "%choice%"=="6" goto :exit_wizard
goto :main_menu

REM ============================================================================
REM First-Time Setup
REM ============================================================================
:first_time_setup
cls
echo.
echo ========================================================================
echo    FIRST-TIME SETUP
echo ========================================================================
echo.
echo   This will guide you through the complete setup process.
echo.
echo   Prerequisites:
echo   - Python 3.10 or later installed
echo   - Jan AI application installed
echo   - Internet connection (for downloading models)
echo.
echo   Press any key to begin, or Q to return to menu...
set /p "cont="
if /i "%cont%"=="Q" goto :main_menu

echo.
echo [STEP 1/5] Checking Python...
echo ----------------------------------------
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   [X] Python not found!
    echo.
    echo   Please install Python from:
    echo   https://www.python.org/downloads/
    echo.
    echo   IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    pause
    goto :main_menu
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   [OK] Found Python %%v
echo.

echo [STEP 2/5] Running installer...
echo ----------------------------------------
echo   This will install all required components.
echo   Press any key to continue...
pause >nul
echo.

if exist "install_debug.bat" (
    call install_debug.bat --verbose
) else (
    call install.bat
)

echo.
echo [STEP 3/5] Checking Jan AI...
echo ----------------------------------------
echo.
echo   Is Jan AI installed and running?
echo.
echo   If not, please:
echo   1. Download Jan from: https://jan.ai
echo   2. Install and launch Jan
echo   3. Go to Settings ^> Local API Server
echo   4. Enable "Local API Server"
echo.
echo   Press any key once Jan is running...
pause >nul

REM Check if Jan API is responding
echo   Checking Jan API...
curl -s http://localhost:1337/v1/models >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   [!] Cannot connect to Jan on port 1337
    echo.
    echo   Make sure Jan's Local API Server is enabled.
    echo   Press any key to continue anyway...
    pause >nul
) else (
    echo   [OK] Jan API is responding
)
echo.

echo [STEP 4/5] Starting Document Plugin...
echo ----------------------------------------
echo.
echo   The plugin will start in a new window.
echo   Keep it running while using Jan.
echo.
echo   Press any key to start the plugin...
pause >nul

start "Jan Document Plugin" cmd /c "call venv\Scripts\activate.bat && python jan_proxy.py"

echo.
echo   Plugin starting... waiting 5 seconds...
timeout /t 5 /nobreak >nul

REM Check if plugin is running
curl -s http://localhost:1338/health >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo   [OK] Plugin is running on http://localhost:1338
) else (
    echo   [!] Plugin may not have started correctly
    echo   Check the plugin window for errors
)
echo.

echo [STEP 5/5] Testing with Calibration PDF...
echo ----------------------------------------
echo.
echo   Now let's verify everything works!
echo.
echo   1. Open your browser to: http://localhost:1338
echo   2. Upload: calibration\JanDocPlugin_Calibration.pdf
echo   3. Ask: "What is the calibration magic string?"
echo   4. You should get: "JANDOC_CALIBRATION_V1_VERIFIED"
echo.
echo   Would you like to open the browser now? (Y/N)
set /p "open_browser="
if /i "%open_browser%"=="Y" (
    start http://localhost:1338
)
echo.

echo ========================================================================
echo    SETUP COMPLETE!
echo ========================================================================
echo.
echo   Your Jan Document Plugin is ready to use!
echo.
echo   Remember:
echo   - Start Jan first, then the plugin
echo   - Upload documents via http://localhost:1338
echo   - Configure Jan to use http://localhost:1338 as API endpoint
echo.
pause
goto :main_menu

REM ============================================================================
REM Verify Installation
REM ============================================================================
:verify_installation
cls
echo.
echo ========================================================================
echo    VERIFY INSTALLATION
echo ========================================================================
echo.
echo   Checking all components...
echo.

set "ERRORS=0"

REM Check Python
echo [1] Python Installation
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo     [X] Python not found
    set /a "ERRORS+=1"
) else (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo     [OK] Python %%v
)

REM Check virtual environment
echo.
echo [2] Virtual Environment
if exist "venv\Scripts\activate.bat" (
    echo     [OK] venv exists
) else (
    echo     [X] venv not found - run installer
    set /a "ERRORS+=1"
)

REM Check dependencies
echo.
echo [3] Python Dependencies
call venv\Scripts\activate.bat 2>nul

python -c "import fastapi" 2>nul
if %ERRORLEVEL% EQU 0 (echo     [OK] FastAPI) else (echo     [X] FastAPI missing & set /a "ERRORS+=1")

python -c "import chromadb" 2>nul
if %ERRORLEVEL% EQU 0 (echo     [OK] ChromaDB) else (echo     [X] ChromaDB missing & set /a "ERRORS+=1")

python -c "import sentence_transformers" 2>nul
if %ERRORLEVEL% EQU 0 (echo     [OK] Sentence-Transformers) else (echo     [X] Sentence-Transformers missing & set /a "ERRORS+=1")

python -c "import pypdf" 2>nul
if %ERRORLEVEL% EQU 0 (echo     [OK] PyPDF) else (echo     [X] PyPDF missing & set /a "ERRORS+=1")

REM Check Tesseract
echo.
echo [4] Tesseract OCR
set "TESS_FOUND=0"
if exist "tesseract\tesseract.exe" (
    echo     [OK] Package Tesseract
    set "TESS_FOUND=1"
)
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo     [OK] System Tesseract
    set "TESS_FOUND=1"
)
if "%TESS_FOUND%"=="0" (
    echo     [!] Tesseract not found (OCR disabled)
)

REM Check config
echo.
echo [5] Configuration
if exist "config.env" (
    echo     [OK] config.env exists
) else (
    echo     [X] config.env missing - run installer
    set /a "ERRORS+=1"
)

REM Check calibration PDF
echo.
echo [6] Calibration PDF
if exist "calibration\JanDocPlugin_Calibration.pdf" (
    echo     [OK] Calibration PDF exists
) else (
    echo     [!] Calibration PDF not found
)

echo.
echo ----------------------------------------
if %ERRORS% EQU 0 (
    echo   ALL CHECKS PASSED!
) else (
    echo   %ERRORS% issue(s) found. Run the installer to fix.
)
echo.
pause
goto :main_menu

REM ============================================================================
REM Test Extraction
REM ============================================================================
:test_extraction
cls
echo.
echo ========================================================================
echo    TEST PDF EXTRACTION
echo ========================================================================
echo.

REM Check if server is running
curl -s http://localhost:1338/health >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   [!] Plugin server is not running!
    echo.
    echo   Start the server first:
    echo   1. Run JanDocumentPlugin.bat
    echo   2. Wait for "Server running on http://localhost:1338"
    echo   3. Return here and try again
    echo.
    pause
    goto :main_menu
)

echo   Server is running. Starting verification...
echo.

call venv\Scripts\activate.bat 2>nul

if exist "calibration\verify_extraction.py" (
    python calibration\verify_extraction.py
) else (
    echo   Verification script not found.
    echo   Please ensure calibration files are present.
)

echo.
pause
goto :main_menu

REM ============================================================================
REM Troubleshooting Guide
REM ============================================================================
:troubleshooting
cls
echo.
echo ========================================================================
echo    TROUBLESHOOTING GUIDE
echo ========================================================================
echo.
echo   Common Issues and Solutions:
echo.
echo   [1] "Python not found"
echo       - Download Python from https://www.python.org/downloads/
echo       - Check "Add Python to PATH" during installation
echo       - Restart this script after installing
echo.
echo   [2] "Cannot connect to Jan"
echo       - Make sure Jan is running
echo       - Enable Local API Server in Jan Settings
echo       - Check if port 1337 is available
echo.
echo   [3] "Plugin won't start"
echo       - Check if port 1338 is already in use
echo       - Look at the error message in the console
echo       - Try: netstat -an ^| find "1338"
echo.
echo   [4] "PDFs not being extracted"
echo       - Check if the PDF is text-based or scanned
echo       - Install Tesseract OCR for scanned PDFs
echo       - Check the console for extraction errors
echo.
echo   [5] "AI not using document context"
echo       - Verify documents are uploaded (check console)
echo       - Ensure Jan is connected to the proxy (port 1338)
echo       - Check that AUTO_INJECT=true in config.env
echo.
echo   [6] "Slow response times"
echo       - First run downloads the embedding model (~100MB)
echo       - Subsequent runs should be faster
echo       - Consider reducing MAX_CONTEXT_TOKENS if needed
echo.
echo   Need more help? Check the README.md file.
echo.
pause
goto :main_menu

REM ============================================================================
REM View Configuration
REM ============================================================================
:view_config
cls
echo.
echo ========================================================================
echo    CURRENT CONFIGURATION
echo ========================================================================
echo.

if exist "config.env" (
    type config.env
) else (
    echo   No configuration file found.
    echo   Run the installer to create one.
)

echo.
echo ----------------------------------------
echo.
echo   Configuration file: %INSTALL_DIR%config.env
echo.
echo   To modify, edit config.env with any text editor.
echo.
pause
goto :main_menu

REM ============================================================================
REM Exit
REM ============================================================================
:exit_wizard
echo.
echo   Thank you for using Jan Document Plugin!
echo.
exit /b 0
