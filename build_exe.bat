@echo off
REM ============================================================================
REM Build Windows Executable for Jan Document Plugin
REM ============================================================================
REM Prerequisites:
REM   - Python 3.10+
REM   - All dependencies installed (run install.bat first)
REM   - PyInstaller: pip install pyinstaller
REM ============================================================================

setlocal

echo.
echo ========================================================================
echo    Building Jan Document Plugin Windows Executable
echo ========================================================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install PyInstaller if not present
pip show pyinstaller >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build the executable
echo.
echo Building executable...
echo This may take several minutes...
echo.

pyinstaller JanDocumentPlugin.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

REM Copy additional files to dist
echo.
echo Copying additional files...

copy config.env dist\JanDocumentPlugin\ >nul 2>nul
copy README.md dist\JanDocumentPlugin\ >nul 2>nul
copy start_proxy.bat dist\JanDocumentPlugin\ >nul 2>nul

REM Create tesseract folder in dist
mkdir dist\JanDocumentPlugin\tesseract 2>nul

echo.
echo ========================================================================
echo    Build Complete!
echo ========================================================================
echo.
echo Executable location: dist\JanDocumentPlugin\JanDocumentPlugin.exe
echo.
echo To distribute:
echo   1. Copy the entire dist\JanDocumentPlugin folder
echo   2. Users should install Tesseract to the 'tesseract' subfolder
echo      or have it installed system-wide
echo.
echo ========================================================================
echo.

pause
