@echo off
REM AVACHATTER Installer Build Script for Windows
REM Builds MSI and NSIS installers

echo ======================================
echo   AVACHATTER Installer Builder
echo ======================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Node.js is not installed or not in PATH
    exit /b 1
)

REM Check if npm is available
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: npm is not installed or not in PATH
    exit /b 1
)

echo Building Windows installers...
echo.

REM Build MSI installer
echo [1/2] Building MSI installer...
call npm run tauri build -- --target msi
if %ERRORLEVEL% NEQ 0 (
    echo Error: MSI build failed
    exit /b 1
)
echo.

REM Build NSIS installer
echo [2/2] Building NSIS installer...
call npm run tauri build -- --target nsis
if %ERRORLEVEL% NEQ 0 (
    echo Error: NSIS build failed
    exit /b 1
)
echo.

echo ======================================
echo   Build Complete!
echo ======================================
echo.
echo Installers created:
echo   - MSI: src-tauri\target\release\bundle\msi\
echo   - NSIS: src-tauri\target\release\bundle\nsis\
echo.
pause
