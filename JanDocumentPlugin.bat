@echo off
REM ============================================================================
REM JanDocumentPlugin - Enhanced Launcher with Debug Mode
REM ============================================================================
REM Usage: JanDocumentPlugin.bat [options]
REM   --debug, -d     Enable debug mode with verbose logging
REM   --test          Run in test mode (exit after startup checks)
REM   --port PORT     Override proxy port (default: 1338)
REM   --help, -h      Show this help message
REM ============================================================================

setlocal EnableDelayedExpansion

REM Get script directory
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

REM Set window title
title Jan Document Plugin

REM Default values
set "DEBUG_MODE=0"
set "TEST_MODE=0"
set "OVERRIDE_PORT="
set "LOG_FILE=%APP_DIR%server.log"

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :start_server
if /i "%~1"=="--debug" set "DEBUG_MODE=1"
if /i "%~1"=="-d" set "DEBUG_MODE=1"
if /i "%~1"=="--test" set "TEST_MODE=1"
if /i "%~1"=="--port" (
    set "OVERRIDE_PORT=%~2"
    shift
)
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help
shift
goto :parse_args

:show_help
echo.
echo Jan Document Plugin - Launcher
echo.
echo Usage: JanDocumentPlugin.bat [options]
echo.
echo Options:
echo   --debug, -d     Enable debug mode with verbose logging
echo   --test          Run startup checks and exit
echo   --port PORT     Override proxy port (default: 1338)
echo   --help, -h      Show this help message
echo.
echo Examples:
echo   JanDocumentPlugin.bat                  Start normally
echo   JanDocumentPlugin.bat --debug          Start with debug logging
echo   JanDocumentPlugin.bat --port 8080      Use port 8080 instead
echo.
exit /b 0

:start_server
REM ============================================================================
REM Startup Checks
REM ============================================================================

if "%DEBUG_MODE%"=="1" (
    echo [DEBUG] Starting in debug mode
    echo [DEBUG] App directory: %APP_DIR%
    echo [DEBUG] Log file: %LOG_FILE%
    echo.
)

REM Check for virtual environment
if exist "venv\Scripts\python.exe" (
    set "PYTHON=venv\Scripts\python.exe"
    if "%DEBUG_MODE%"=="1" echo [DEBUG] Using venv Python: %PYTHON%
) else (
    set "PYTHON=python"
    if "%DEBUG_MODE%"=="1" echo [DEBUG] Using system Python
)

REM Check if Python is available
%PYTHON% --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Python not found!
    echo.
    echo Please run install.bat first, or install Python from:
    echo   https://www.python.org/downloads/
    echo.
    echo For troubleshooting, run: tutorial.bat
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('%PYTHON% --version 2^>^&1') do set "PYVER=%%v"
if "%DEBUG_MODE%"=="1" echo [DEBUG] Python version: %PYVER%

REM Load configuration
set "PROXY_PORT=1338"
set "JAN_PORT=1337"
set "TESSERACT_PATH="
set "STORAGE_DIR=.\jan_doc_store"
set "AUTO_INJECT=true"
set "MAX_CONTEXT_TOKENS=8000"
set "LOG_LEVEL=INFO"

if exist "config.env" (
    if "%DEBUG_MODE%"=="1" echo [DEBUG] Loading config.env
    for /f "usebackq tokens=1,* delims==" %%a in ("config.env") do (
        REM Skip comments and empty lines
        set "line=%%a"
        if not "!line:~0,1!"=="#" (
            set "%%a=%%b"
            if "%DEBUG_MODE%"=="1" echo [DEBUG] Config: %%a=%%b
        )
    )
) else (
    echo [WARN] config.env not found, using defaults
)

REM Override port if specified
if not "%OVERRIDE_PORT%"=="" (
    set "PROXY_PORT=%OVERRIDE_PORT%"
    if "%DEBUG_MODE%"=="1" echo [DEBUG] Port overridden to: %PROXY_PORT%
)

REM Find Tesseract if not configured
if "%TESSERACT_PATH%"=="" (
    if exist "%APP_DIR%tesseract\tesseract.exe" (
        set "TESSERACT_PATH=%APP_DIR%tesseract\tesseract.exe"
        if "%DEBUG_MODE%"=="1" echo [DEBUG] Found package Tesseract
    ) else if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        set "TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe"
        if "%DEBUG_MODE%"=="1" echo [DEBUG] Found system Tesseract
    )
)

REM Verify Tesseract
set "OCR_STATUS=Disabled"
if not "%TESSERACT_PATH%"=="" (
    if exist "%TESSERACT_PATH%" (
        set "OCR_STATUS=Enabled"
    ) else (
        echo [WARN] Tesseract path configured but file not found: %TESSERACT_PATH%
        set "TESSERACT_PATH="
    )
)

REM ============================================================================
REM Pre-flight Checks
REM ============================================================================

echo.
echo ========================================================================
echo    Jan Document Plugin v1.2.0
echo    Offline Document Processing for Local LLMs
echo ========================================================================
if "%DEBUG_MODE%"=="1" echo    [DEBUG MODE - Verbose logging enabled]
echo.
echo    Configuration:
echo    --------------
echo    Proxy Server:  http://localhost:%PROXY_PORT%
echo    Jan Backend:   http://localhost:%JAN_PORT%
echo    OCR Support:   %OCR_STATUS%
echo    Storage:       %STORAGE_DIR%
echo    Log Level:     %LOG_LEVEL%
echo.

REM Check if Jan is running
if "%DEBUG_MODE%"=="1" echo [DEBUG] Checking Jan API connection...

curl -s http://localhost:%JAN_PORT%/v1/models >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo    [WARN] Cannot connect to Jan on port %JAN_PORT%
    echo.
    echo    Please ensure:
    echo    1. Jan is running
    echo    2. Local API Server is enabled in Jan Settings
    echo.
    echo    The plugin will start, but proxying won't work until Jan is ready.
    echo.
) else (
    echo    [OK] Jan API is responding
    echo.
)

REM Check if port is available
netstat -an 2>nul | find ":%PROXY_PORT% " | find "LISTENING" >nul
if %ERRORLEVEL% EQU 0 (
    echo    [ERROR] Port %PROXY_PORT% is already in use!
    echo.
    echo    Either:
    echo    1. Close the application using port %PROXY_PORT%
    echo    2. Use a different port: JanDocumentPlugin.bat --port 8080
    echo.
    pause
    exit /b 1
)

if "%TEST_MODE%"=="1" (
    echo.
    echo [TEST] Pre-flight checks completed. Exiting test mode.
    echo.
    pause
    exit /b 0
)

echo ========================================================================
echo.
echo    Starting server... Press Ctrl+C to stop.
echo.
echo    Web Interface: http://localhost:%PROXY_PORT%
echo    Upload documents at the web interface or via API.
echo.
echo    For help, run: tutorial.bat
echo.
echo ========================================================================
echo.

REM Build command line arguments
set "ARGS=--port %PROXY_PORT% --jan-port %JAN_PORT%"

if not "%TESSERACT_PATH%"=="" (
    set "ARGS=%ARGS% --tesseract "%TESSERACT_PATH%""
)

if not "%STORAGE_DIR%"=="" (
    set "ARGS=%ARGS% --storage "%STORAGE_DIR%""
)

if "%DEBUG_MODE%"=="1" (
    set "ARGS=%ARGS% --debug"
    echo [DEBUG] Launch command: %PYTHON% jan_proxy.py %ARGS%
    echo.
)

REM Start logging if in debug mode
if "%DEBUG_MODE%"=="1" (
    echo [%DATE% %TIME%] Starting Jan Document Plugin >> "%LOG_FILE%"
    echo [%DATE% %TIME%] Args: %ARGS% >> "%LOG_FILE%"
    %PYTHON% jan_proxy.py %ARGS% 2>&1 | tee -a "%LOG_FILE%"
) else (
    %PYTHON% jan_proxy.py %ARGS%
)

REM If we get here, server stopped
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo ========================================================================

if %EXIT_CODE% EQU 0 (
    echo    Server stopped normally.
) else (
    echo    Server stopped with error code: %EXIT_CODE%
    echo.
    echo    For troubleshooting:
    echo    1. Run: tutorial.bat
    echo    2. Check log: %LOG_FILE%
    echo    3. Try: JanDocumentPlugin.bat --debug
)

echo ========================================================================
echo.

if "%DEBUG_MODE%"=="1" (
    echo [DEBUG] Exit code: %EXIT_CODE%
    echo [%DATE% %TIME%] Server stopped with code %EXIT_CODE% >> "%LOG_FILE%"
)

pause
exit /b %EXIT_CODE%
