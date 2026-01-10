@echo off
REM ============================================================================
REM Jan Document Plugin - Windows Installer (Debug Version)
REM ============================================================================
REM Enhanced installer with comprehensive debugging and diagnostics
REM ============================================================================

setlocal EnableDelayedExpansion

REM Parse command line arguments
set "DEBUG_MODE=0"
set "VERBOSE=0"
set "SKIP_DEPS=0"
set "LOG_FILE=%~dp0install_log.txt"

:parse_args
if "%~1"=="" goto :start_install
if /i "%~1"=="--debug" set "DEBUG_MODE=1"
if /i "%~1"=="-d" set "DEBUG_MODE=1"
if /i "%~1"=="--verbose" set "VERBOSE=1"
if /i "%~1"=="-v" set "VERBOSE=1"
if /i "%~1"=="--skip-deps" set "SKIP_DEPS=1"
shift
goto :parse_args

:start_install
REM Start logging
echo Jan Document Plugin - Installation Log > "%LOG_FILE%"
echo Timestamp: %DATE% %TIME% >> "%LOG_FILE%"
echo ========================================== >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

echo.
echo ========================================================================
echo    Jan Document Plugin - Windows Installer v1.2.0 (Debug Mode)
echo ========================================================================
if "%DEBUG_MODE%"=="1" echo    [DEBUG MODE ENABLED - Detailed output]
echo.

REM Get the directory where this script is located
set "INSTALL_DIR=%~dp0"
cd /d "%INSTALL_DIR%"

call :log "Install directory: %INSTALL_DIR%"
call :log "Debug Mode: %DEBUG_MODE%"
call :log "Log file: %LOG_FILE%"
echo.

REM ============================================================================
REM STEP 1: System Diagnostics
REM ============================================================================
call :header "STEP 1: System Diagnostics"

REM Check Windows version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set "WINVER=%%i.%%j"
call :log "Windows Version: %WINVER%"

REM Check architecture
if defined PROCESSOR_ARCHITEW6432 (
    call :log "Architecture: 64-bit (WoW64)"
) else (
    if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
        call :log "Architecture: 64-bit"
    ) else (
        call :log "Architecture: 32-bit (Warning: May have limitations)"
    )
)

REM Check available memory
for /f "tokens=2 delims==" %%a in ('wmic OS get TotalVisibleMemorySize /value') do set "TOTALMEM=%%a"
set /a "TOTALMEM_MB=%TOTALMEM% / 1024" 2>nul
if defined TOTALMEM_MB (
    call :log "Total Memory: %TOTALMEM_MB% MB"
    if %TOTALMEM_MB% LSS 4096 (
        call :warn "Low memory detected. Recommend 4GB+ for optimal performance."
    )
)

REM Check disk space
for /f "tokens=3" %%a in ('dir /-c "%INSTALL_DIR%" 2^>nul ^| find "bytes free"') do set "FREESPACE=%%a"
call :log "Free disk space: %FREESPACE% bytes"

echo.

REM ============================================================================
REM STEP 2: Python Installation Check
REM ============================================================================
call :header "STEP 2: Checking Python Installation"

REM Try multiple Python paths
set "PYTHON_EXE="
set "PYTHON_FOUND=0"

REM Check 'python' command
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%p in ('where python') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%p"
    )
    set "PYTHON_FOUND=1"
)

REM Check 'python3' command
if "%PYTHON_FOUND%"=="0" (
    where python3 >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        for /f "tokens=*" %%p in ('where python3') do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%p"
        )
        set "PYTHON_FOUND=1"
    )
)

REM Check common install locations
if "%PYTHON_FOUND%"=="0" (
    for %%p in (
        "C:\Python311\python.exe"
        "C:\Python310\python.exe"
        "C:\Python39\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    ) do (
        if exist %%p (
            set "PYTHON_EXE=%%~p"
            set "PYTHON_FOUND=1"
            goto :python_found
        )
    )
)

:python_found
if "%PYTHON_FOUND%"=="0" (
    call :error "Python not found!"
    echo.
    echo   Please install Python 3.10 or later from:
    echo   https://www.python.org/downloads/
    echo.
    echo   Make sure to check "Add Python to PATH" during installation.
    echo.
    call :log "ERROR: Python installation not found"
    pause
    exit /b 1
)

call :log "Python found at: %PYTHON_EXE%"

REM Check Python version
for /f "tokens=2 delims= " %%v in ('"%PYTHON_EXE%" --version 2^>^&1') do set PYVER=%%v
call :log "Python version: %PYVER%"

REM Parse version numbers
for /f "tokens=1,2,3 delims=." %%a in ("%PYVER%") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)

if %PY_MAJOR% LSS 3 (
    call :error "Python 3.10+ required, found Python %PYVER%"
    pause
    exit /b 1
)
if %PY_MAJOR%==3 if %PY_MINOR% LSS 10 (
    call :warn "Python 3.10+ recommended, found Python %PYVER%"
)

call :success "Python %PYVER% is compatible"
echo.

REM ============================================================================
REM STEP 3: Virtual Environment
REM ============================================================================
call :header "STEP 3: Creating Virtual Environment"

if exist "venv\Scripts\activate.bat" (
    call :log "Virtual environment already exists"
    echo   [EXISTS] Virtual environment found
) else (
    call :log "Creating new virtual environment..."
    "%PYTHON_EXE%" -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        call :error "Failed to create virtual environment"
        call :log "ERROR: venv creation failed with code %ERRORLEVEL%"

        echo.
        echo   Troubleshooting:
        echo   1. Try: %PYTHON_EXE% -m pip install --upgrade virtualenv
        echo   2. Then: %PYTHON_EXE% -m virtualenv venv
        echo.
        pause
        exit /b 1
    )
    call :success "Virtual environment created"
)

REM Activate virtual environment
call :log "Activating virtual environment..."
call venv\Scripts\activate.bat

REM Verify activation
where python > "%TEMP%\pypath.tmp" 2>nul
set /p VENV_PYTHON=<"%TEMP%\pypath.tmp"
call :log "Active Python: %VENV_PYTHON%"
del "%TEMP%\pypath.tmp" 2>nul

echo.

REM ============================================================================
REM STEP 4: Install Dependencies
REM ============================================================================
call :header "STEP 4: Installing Python Dependencies"

if "%SKIP_DEPS%"=="1" (
    call :warn "Skipping dependency installation (--skip-deps)"
    goto :skip_deps
)

call :log "Upgrading pip..."
python -m pip install --upgrade pip >> "%LOG_FILE%" 2>&1

echo   Installing required packages (this may take 2-5 minutes)...
echo.

REM Install with verbose output if debug mode
if "%DEBUG_MODE%"=="1" (
    pip install -r requirements.txt 2>&1 | tee -a "%LOG_FILE%"
) else (
    pip install -r requirements.txt >> "%LOG_FILE%" 2>&1
    if %ERRORLEVEL% NEQ 0 (
        call :error "Dependency installation failed"
        echo.
        echo   Check the log file for details: %LOG_FILE%
        echo.
        echo   Common fixes:
        echo   1. Update pip: python -m pip install --upgrade pip
        echo   2. Install Visual C++ Build Tools for native extensions
        echo   3. Try installing packages individually
        echo.
        pause
        exit /b 1
    )
)

call :success "Dependencies installed"

REM Verify key packages
echo   Verifying key packages...

python -c "import fastapi; print(f'    FastAPI: {fastapi.__version__}')" 2>>"%LOG_FILE%"
python -c "import chromadb; print(f'    ChromaDB: {chromadb.__version__}')" 2>>"%LOG_FILE%"
python -c "import sentence_transformers; print('    Sentence-Transformers: OK')" 2>>"%LOG_FILE%"
python -c "import pypdf; print('    PyPDF: OK')" 2>>"%LOG_FILE%"
python -c "import pytesseract; print('    Pytesseract: OK')" 2>>"%LOG_FILE%"

:skip_deps
echo.

REM ============================================================================
REM STEP 5: Tesseract OCR Setup
REM ============================================================================
call :header "STEP 5: Setting Up Tesseract OCR"

set "TESSERACT_DIR=%INSTALL_DIR%tesseract"
set "TESSERACT_EXE="

REM Check package-local Tesseract
if exist "%TESSERACT_DIR%\tesseract.exe" (
    set "TESSERACT_EXE=%TESSERACT_DIR%\tesseract.exe"
    call :log "Found package Tesseract: %TESSERACT_EXE%"
)

REM Check system installations
if not defined TESSERACT_EXE (
    for %%t in (
        "C:\Program Files\Tesseract-OCR\tesseract.exe"
        "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
        "%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"
    ) do (
        if exist %%t (
            set "TESSERACT_EXE=%%~t"
            call :log "Found system Tesseract: %%~t"
            goto :tesseract_found
        )
    )
)

:tesseract_found
if defined TESSERACT_EXE (
    REM Verify Tesseract works
    "%TESSERACT_EXE%" --version > "%TEMP%\tess_ver.tmp" 2>&1
    if %ERRORLEVEL% EQU 0 (
        set /p TESS_VER=<"%TEMP%\tess_ver.tmp"
        call :success "Tesseract found: !TESS_VER:~0,20!"
    ) else (
        call :warn "Tesseract found but may not work correctly"
    )
    del "%TEMP%\tess_ver.tmp" 2>nul
) else (
    call :warn "Tesseract OCR not found"
    echo.
    echo   OCR features will be disabled. To enable:
    echo   1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
    echo   2. Install to: C:\Program Files\Tesseract-OCR
    echo   3. Re-run this installer
    echo.
    set "TESSERACT_EXE=not_installed"
)

echo.

REM ============================================================================
REM STEP 6: Download Embedding Model
REM ============================================================================
call :header "STEP 6: Pre-downloading Embedding Model"

echo   Downloading all-MiniLM-L6-v2 model (first run only)...
echo   This may take 1-3 minutes depending on connection...
echo.

python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('all-MiniLM-L6-v2'); print(f'    Model loaded: {m.get_sentence_embedding_dimension()} dimensions')"

if %ERRORLEVEL% NEQ 0 (
    call :warn "Model download failed. Will download on first use."
    call :log "WARNING: Embedding model pre-download failed"
) else (
    call :success "Embedding model ready"
)

echo.

REM ============================================================================
REM STEP 7: Create Configuration
REM ============================================================================
call :header "STEP 7: Creating Configuration"

(
echo # Jan Document Plugin Configuration
echo # Generated by installer on %DATE% %TIME%
echo.
echo TESSERACT_PATH=%TESSERACT_EXE%
echo PROXY_PORT=1338
echo JAN_PORT=1337
echo STORAGE_DIR=.\jan_doc_store
echo EMBEDDING_MODEL=all-MiniLM-L6-v2
echo AUTO_INJECT=true
echo MAX_CONTEXT_TOKENS=8000
echo DEBUG_MODE=%DEBUG_MODE%
echo LOG_LEVEL=INFO
) > config.env

call :log "Configuration saved to config.env"
call :success "Configuration created"

echo.

REM ============================================================================
REM STEP 8: Generate Calibration PDF
REM ============================================================================
call :header "STEP 8: Generating Calibration PDF"

if exist "calibration\create_calibration_pdf.py" (
    call :log "Generating calibration PDF..."
    python calibration\create_calibration_pdf.py >> "%LOG_FILE%" 2>&1
    if %ERRORLEVEL% EQU 0 (
        call :success "Calibration PDF created"
        echo   Location: calibration\JanDocPlugin_Calibration.pdf
    ) else (
        call :warn "Could not generate calibration PDF"
    )
) else (
    call :log "Calibration script not found, skipping"
)

echo.

REM ============================================================================
REM STEP 9: Run Diagnostic Tests
REM ============================================================================
call :header "STEP 9: Running Diagnostic Tests"

echo   Testing core functionality...
echo.

REM Test 1: Import checks
echo   [TEST] Core imports...
python -c "import fastapi, chromadb, sentence_transformers, pypdf; print('         All core imports OK')" 2>&1
if %ERRORLEVEL% NEQ 0 (
    call :warn "Some imports failed - check dependencies"
)

REM Test 2: ChromaDB storage
echo   [TEST] ChromaDB initialization...
python -c "import chromadb; c = chromadb.Client(); print('         ChromaDB client OK')" 2>&1
if %ERRORLEVEL% NEQ 0 (
    call :warn "ChromaDB initialization failed"
)

REM Test 3: PDF extraction
echo   [TEST] PDF extraction capability...
python -c "from pypdf import PdfReader; print('         PDF extraction OK')" 2>&1

REM Test 4: Embedding model
echo   [TEST] Embedding generation...
python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('all-MiniLM-L6-v2'); e = m.encode('test'); print(f'         Embedding OK: {len(e)} dims')" 2>&1

echo.

REM ============================================================================
REM Installation Complete
REM ============================================================================
echo ========================================================================
echo    Installation Complete!
echo ========================================================================
echo.
echo   Configuration saved to: config.env
echo   Installation log: %LOG_FILE%
echo.
echo   NEXT STEPS:
echo   -----------
echo   1. Start Jan and enable Local API Server
echo      (Jan -^> Settings -^> Local API Server -^> Enable)
echo.
echo   2. Start the document plugin:
echo      Run: JanDocumentPlugin.bat
echo      Or:  start_proxy.bat
echo.
echo   3. Test with calibration document:
echo      - Upload: calibration\JanDocPlugin_Calibration.pdf
echo      - Ask: "What is the calibration magic string?"
echo      - Expected: "JANDOC_CALIBRATION_V1_VERIFIED"
echo.
echo   4. Access web interface: http://localhost:1338
echo.
echo ========================================================================
echo.

call :log "Installation completed successfully"

pause
exit /b 0

REM ============================================================================
REM Helper Functions
REM ============================================================================

:header
echo.
echo [%~1]
echo ----------------------------------------
echo %~1 >> "%LOG_FILE%"
goto :eof

:log
echo %~1 >> "%LOG_FILE%"
if "%VERBOSE%"=="1" echo   [LOG] %~1
goto :eof

:success
echo   [OK] %~1
echo [OK] %~1 >> "%LOG_FILE%"
goto :eof

:warn
echo   [WARN] %~1
echo [WARN] %~1 >> "%LOG_FILE%"
goto :eof

:error
echo   [ERROR] %~1
echo [ERROR] %~1 >> "%LOG_FILE%"
goto :eof
