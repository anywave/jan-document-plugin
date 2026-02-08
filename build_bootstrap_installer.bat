@echo off
REM Jan Document Plugin - Bootstrap Installer Builder
REM Creates setup.exe that handles Python installation
REM Version 2.0.0-beta

echo.
echo ============================================
echo   Jan Document Plugin Bootstrap Builder
echo   v2.0.0-beta
echo ============================================
echo.

cd /d "%~dp0"

REM Check for Inno Setup
set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" (
    echo [!!] Inno Setup 6 not found at: %INNO_PATH%
    echo.
    echo Please install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

echo [OK] Inno Setup found
echo.

REM Create necessary directories
echo [..] Creating directories...
if not exist "installer\docs" mkdir "installer\docs"
if not exist "installer\downloads" mkdir "installer\downloads"
if not exist "dist\installer" mkdir "dist\installer"

REM Check for Python installer
set "PYTHON_INSTALLER=installer\downloads\python-3.12.8-amd64.exe"
if not exist "%PYTHON_INSTALLER%" (
    echo.
    echo [!!] Python installer not found: %PYTHON_INSTALLER%
    echo.
    echo Download Python 3.12.8 installer:
    echo https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
    echo.
    echo Save to: installer\downloads\python-3.12.8-amd64.exe
    echo.
    set /p DOWNLOAD_NOW="Download now? (y/n): "
    if /i "%DOWNLOAD_NOW%"=="y" (
        echo.
        echo [..] Downloading Python 3.12.8 installer...
        powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%PYTHON_INSTALLER%'"
        if errorlevel 1 (
            echo [!!] Download failed
            pause
            exit /b 1
        )
        echo [OK] Download complete
    ) else (
        echo.
        echo Please download Python installer manually and re-run this script.
        pause
        exit /b 1
    )
)

echo [OK] Python installer ready

REM Optional: Check for bundled LLM
if exist "installer\llm\llama-server.exe" (
    echo [OK] Bundled LLM found (~8GB installer)
) else (
    echo [--] No bundled LLM (smaller installer, requires separate LLM)
)

REM Optional: Check for model
if exist "installer\models\*.gguf" (
    echo [OK] Model file found
) else (
    echo [--] No model file (will need to download separately)
)

echo.
echo [..] Compiling installer with Inno Setup...
"%INNO_PATH%" "installer\setup-bootstrap.iss"

if errorlevel 1 (
    echo.
    echo [!!] Compilation failed
    pause
    exit /b 1
)

echo.
echo [OK] Installer compiled successfully!
echo.
echo Output: dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe
echo.

REM Check file size
for %%I in ("dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe") do (
    set SIZE=%%~zI
)
set /a SIZE_MB=%SIZE% / 1048576
echo Installer size: ~%SIZE_MB% MB

echo.
echo ============================================
echo   BUILD COMPLETE
echo ============================================
echo.
echo Next steps:
echo 1. Test installer: dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe
echo 2. Create GitHub release
echo 3. Upload installer to release
echo.

pause
