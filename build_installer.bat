@echo off
REM ============================================================================
REM Build Installer for Jan Document Plugin v2.0.0-beta
REM ============================================================================
REM Prerequisites:
REM   1. Run build_exe.bat first (creates dist\JanDocumentPlugin\)
REM   2. Stage llama-server + Vulkan DLLs in installer\llm\
REM   3. Stage GGUF model files in installer\models\
REM   4. Install Inno Setup: https://jrsoftware.org/isinfo.php
REM
REM This script validates everything, then compiles the installer.
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ========================================================================
echo    Jan Document Plugin v2.0.0-beta - Installer Builder
echo ========================================================================
echo.

set "ERRORS=0"
set "WARNINGS=0"

REM ---- Step 1: Check PyInstaller dist output ----
echo [1/5] Checking PyInstaller build output...

if not exist "dist\JanDocumentPlugin\JanDocumentPlugin.exe" (
    echo   [FAIL] dist\JanDocumentPlugin\JanDocumentPlugin.exe not found
    echo         Run build_exe.bat first!
    set /a ERRORS+=1
) else (
    echo   [OK]   JanDocumentPlugin.exe found
)

if not exist "dist\JanDocumentPlugin\chat_ui.html" (
    echo   [FAIL] dist\JanDocumentPlugin\chat_ui.html not found
    set /a ERRORS+=1
) else (
    echo   [OK]   chat_ui.html found
)

if not exist "dist\JanDocumentPlugin\rollback_jan.ps1" (
    echo   [WARN] rollback_jan.ps1 not in dist (will be sourced from repo root)
    set /a WARNINGS+=1
) else (
    echo   [OK]   rollback_jan.ps1 found
)

echo.

REM ---- Step 2: Check installer source files ----
echo [2/5] Checking installer source files...

if not exist "LICENSE" (
    echo   [FAIL] LICENSE file not found in repo root
    set /a ERRORS+=1
) else (
    echo   [OK]   LICENSE
)

if not exist "docs\pre_install_info.txt" (
    echo   [FAIL] docs\pre_install_info.txt not found
    set /a ERRORS+=1
) else (
    echo   [OK]   docs\pre_install_info.txt
)

if not exist "installer\setup.iss" (
    echo   [FAIL] installer\setup.iss not found
    set /a ERRORS+=1
) else (
    echo   [OK]   installer\setup.iss
)

if not exist "calibration\JanDocPlugin_Calibration.pdf" (
    echo   [WARN] calibration\JanDocPlugin_Calibration.pdf not found (non-critical)
    set /a WARNINGS+=1
) else (
    echo   [OK]   JanDocPlugin_Calibration.pdf
)

echo.

REM ---- Step 3: Check LLM staging ----
echo [3/5] Checking LLM engine staging (installer\llm\)...

if not exist "installer\llm\llama-server.exe" (
    echo   [WARN] installer\llm\llama-server.exe NOT FOUND
    echo         The installer will skip bundling the LLM engine.
    echo         Users will need Jan AI or another LLM server.
    echo.
    echo         To fix: download llama.cpp Vulkan build from
    echo         https://github.com/ggerganov/llama.cpp/releases
    echo         and place llama-server.exe + DLLs in installer\llm\
    set /a WARNINGS+=1
) else (
    echo   [OK]   llama-server.exe found
    REM Check for Vulkan DLLs
    set "VULKAN_FOUND=0"
    for %%f in (installer\llm\*.dll) do set "VULKAN_FOUND=1"
    if "!VULKAN_FOUND!"=="0" (
        echo   [WARN] No .dll files found in installer\llm\ (Vulkan DLLs may be needed)
        set /a WARNINGS+=1
    ) else (
        echo   [OK]   DLL files present
    )
)

echo.

REM ---- Step 4: Check model staging ----
echo [4/5] Checking model staging (installer\models\)...

set "MODEL_FOUND=0"
for %%f in (installer\models\*.gguf) do set "MODEL_FOUND=1"

if "!MODEL_FOUND!"=="0" (
    echo   [WARN] No .gguf model files found in installer\models\
    echo         The installer will skip bundling a model.
    echo         Users will need to provide their own model.
    echo.
    echo         Recommended: Qwen 2.5 7B Instruct q4_k_m (~5 GB)
    echo         https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF
    set /a WARNINGS+=1
) else (
    echo   [OK]   GGUF model files found
    for %%f in (installer\models\*.gguf) do (
        echo          - %%~nxf
    )
)

echo.

REM ---- Step 5: Check Inno Setup ----
echo [5/5] Checking Inno Setup compiler...

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
) else (
    where iscc >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        set "ISCC=iscc"
    )
)

if "!ISCC!"=="" (
    echo   [FAIL] Inno Setup compiler (ISCC.exe) not found
    echo         Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
    set /a ERRORS+=1
) else (
    echo   [OK]   Inno Setup found: !ISCC!
)

echo.
echo ========================================================================

REM ---- Summary ----
if !ERRORS! GTR 0 (
    echo   RESULT: !ERRORS! error(s), !WARNINGS! warning(s)
    echo   Cannot build installer. Fix errors above and retry.
    echo ========================================================================
    echo.
    pause
    exit /b 1
)

if !WARNINGS! GTR 0 (
    echo   RESULT: 0 errors, !WARNINGS! warning(s)
    echo   Installer will build but may be missing bundled components.
    echo ========================================================================
    echo.
    set /p CONTINUE="Continue anyway? (Y/N): "
    if /i "!CONTINUE!" NEQ "Y" (
        echo Cancelled.
        pause
        exit /b 0
    )
) else (
    echo   RESULT: All checks passed!
    echo ========================================================================
)

echo.

REM ---- Compile ----
echo Compiling installer with Inno Setup...
echo.

"!ISCC!" installer\setup.iss

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Inno Setup compilation failed!
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo    Installer Built Successfully!
echo ========================================================================
echo.
echo Output: dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe
echo.

if exist "dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe" (
    for %%f in (dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe) do (
        echo Size: %%~zf bytes
    )
)

echo.
echo To test: run the installer on a clean Windows machine.
echo.
echo ========================================================================
echo.

pause
