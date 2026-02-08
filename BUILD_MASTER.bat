@echo off
REM ============================================================================
REM Jan Document Plugin - MASTER BUILD SCRIPT
REM Correct Order of Operations for Complete Build
REM Version 2.0.0-beta
REM ============================================================================

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ============================================================================
echo   JAN DOCUMENT PLUGIN - MASTER BUILD ORCHESTRATOR
echo   v2.0.0-beta
echo ============================================================================
echo.
echo This script will build the complete distribution in the correct order:
echo   1. Verify Python 3.12 environment
echo   2. Install/verify all dependencies
echo   3. Run tests (optional)
echo   4. Build PyInstaller executable
echo   5. Prepare installer staging
echo   6. Download Python installer
echo   7. Compile Inno Setup installer
echo   8. Verify final package
echo.
pause

REM ============================================================================
REM PHASE 1: Environment Verification
REM ============================================================================

echo.
echo [PHASE 1] Verifying Build Environment
echo ============================================================================
echo.

REM Check Python 3.12
echo [1.1] Checking Python 3.12...
python --version 2>nul | findstr /C:"3.12" >nul
if errorlevel 1 (
    echo [!!] ERROR: Python 3.12 not found in PATH
    echo.
    echo Please install Python 3.12 from:
    echo https://www.python.org/downloads/release/python-3128/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo [OK] Python 3.12 found

REM Check PyInstaller
echo.
echo [1.2] Checking PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [INSTALL] PyInstaller not found, installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo [!!] ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)
echo [OK] PyInstaller ready

REM Check Inno Setup
echo.
echo [1.3] Checking Inno Setup...
set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" (
    echo [!!] ERROR: Inno Setup 6 not found
    echo.
    echo Download and install from:
    echo https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)
echo [OK] Inno Setup 6 found

echo.
echo [OK] Phase 1 Complete - Environment verified
pause

REM ============================================================================
REM PHASE 2: Dependency Installation
REM ============================================================================

echo.
echo [PHASE 2] Installing/Verifying Dependencies
echo ============================================================================
echo.

echo [2.1] Installing requirements...
pip install -r requirements.txt --upgrade
if errorlevel 1 (
    echo [!!] ERROR: Failed to install requirements
    pause
    exit /b 1
)
echo [OK] Dependencies installed

echo.
echo [OK] Phase 2 Complete - Dependencies ready
pause

REM ============================================================================
REM PHASE 3: Clean Previous Builds
REM ============================================================================

echo.
echo [PHASE 3] Cleaning Previous Builds
echo ============================================================================
echo.

if exist "dist" (
    echo [CLEAN] Removing dist/...
    rmdir /s /q "dist"
)

if exist "build" (
    echo [CLEAN] Removing build/...
    rmdir /s /q "build"
)

echo [OK] Phase 3 Complete - Clean workspace
pause

REM ============================================================================
REM PHASE 4: PyInstaller Build
REM ============================================================================

echo.
echo [PHASE 4] Building Executable with PyInstaller
echo ============================================================================
echo.

echo [4.1] Running PyInstaller...
echo.

pyinstaller JanDocumentPlugin.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [!!] ERROR: PyInstaller build failed
    echo.
    echo Common issues:
    echo   - Missing hidden imports in .spec file
    echo   - Import errors in source code
    echo   - Insufficient disk space
    echo.
    echo Check build log above for details
    pause
    exit /b 1
)

REM Verify exe was created
if not exist "dist\JanDocumentPlugin\JanDocumentPlugin.exe" (
    echo [!!] ERROR: Executable not found after build
    pause
    exit /b 1
)

echo.
echo [OK] Executable built: dist\JanDocumentPlugin\JanDocumentPlugin.exe
pause

REM ============================================================================
REM PHASE 5: Installer Staging
REM ============================================================================

echo.
echo [PHASE 5] Preparing Installer Staging
echo ============================================================================
echo.

echo [5.1] Creating installer directories...
if not exist "installer\docs" mkdir "installer\docs"
if not exist "installer\downloads" mkdir "installer\downloads"
if not exist "dist\installer" mkdir "dist\installer"
echo [OK] Directories created

echo.
echo [5.2] Copying additional files...
copy /y chat_ui.html dist\JanDocumentPlugin\ >nul 2>&1
copy /y config.env.example dist\JanDocumentPlugin\ >nul 2>&1
copy /y rollback_jan.ps1 dist\JanDocumentPlugin\ >nul 2>&1
copy /y soul_registry_state.json dist\JanDocumentPlugin\ >nul 2>&1
echo [OK] Files copied

echo.
echo [OK] Phase 5 Complete - Staging ready
pause

REM ============================================================================
REM PHASE 6: Download Python Installer
REM ============================================================================

echo.
echo [PHASE 6] Python Installer for Bootstrap
echo ============================================================================
echo.

set "PYTHON_INSTALLER=installer\downloads\python-3.12.8-amd64.exe"

if exist "%PYTHON_INSTALLER%" (
    echo [OK] Python installer already downloaded
) else (
    echo [DOWNLOAD] Python 3.12.8 installer...
    echo.
    echo Downloading from python.org (~30MB)...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%PYTHON_INSTALLER%'"

    if errorlevel 1 (
        echo.
        echo [!!] WARNING: Download failed
        echo.
        echo Manual download required:
        echo   URL: https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
        echo   Save to: installer\downloads\python-3.12.8-amd64.exe
        echo.
        echo Press any key to continue anyway (installer will be smaller)
        pause >nul
    ) else (
        echo [OK] Python installer downloaded
    )
)

echo.
echo [OK] Phase 6 Complete
pause

REM ============================================================================
REM PHASE 7: Compile Inno Setup Installer
REM ============================================================================

echo.
echo [PHASE 7] Compiling Final Installer
echo ============================================================================
echo.

echo [7.1] Compiling with Inno Setup...
echo.

"%INNO_PATH%" "installer\setup-bootstrap.iss"

if errorlevel 1 (
    echo.
    echo [!!] ERROR: Inno Setup compilation failed
    echo.
    echo Check the log above for syntax errors or missing files
    pause
    exit /b 1
)

REM Verify installer was created
if not exist "dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe" (
    echo [!!] ERROR: Installer not found after compilation
    pause
    exit /b 1
)

echo.
echo [OK] Installer compiled successfully!

REM ============================================================================
REM PHASE 8: Verification
REM ============================================================================

echo.
echo [PHASE 8] Final Verification
echo ============================================================================
echo.

echo [8.1] Checking files...
if exist "dist\JanDocumentPlugin\JanDocumentPlugin.exe" (
    echo [OK] Executable: dist\JanDocumentPlugin\JanDocumentPlugin.exe
) else (
    echo [!!] MISSING: Executable
)

if exist "dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe" (
    echo [OK] Installer: dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe
    for %%I in ("dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe") do (
        set SIZE=%%~zI
        set /a SIZE_MB=!SIZE! / 1048576
        echo      Size: ~!SIZE_MB! MB
    )
) else (
    echo [!!] MISSING: Installer
)

REM ============================================================================
REM BUILD COMPLETE
REM ============================================================================

echo.
echo ============================================================================
echo   BUILD COMPLETE!
echo ============================================================================
echo.
echo Deliverables:
echo   [EXE]       dist\JanDocumentPlugin\JanDocumentPlugin.exe
echo   [INSTALLER] dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe
echo.
echo Next Steps:
echo   1. Test installer on clean Windows VM
echo   2. Create GitHub release tag: v2.0.0-beta
echo   3. Upload installer to GitHub releases
echo   4. Update README with download link
echo.
echo Quick test:
echo   dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe
echo.
echo Create release:
echo   git tag -a v2.0.0-beta -m "Release v2.0.0-beta"
echo   git push origin v2.0.0-beta
echo   gh release create v2.0.0-beta dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe --prerelease
echo.
pause

endlocal
