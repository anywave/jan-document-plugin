# Jan Document Plugin - Automated Installer
# Childproof installation with verification at each step
# Version 2.0.0

param(
    [switch]$SkipPythonCheck,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Configuration
$RequiredPythonMajor = 3
$RequiredPythonMinor = 12
$PluginDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $PluginDir "venv"
$LogFile = Join-Path $PluginDir "install.log"

# Colors
function Write-Step { param($msg) Write-Host "[..] $msg" -ForegroundColor Yellow }
function Write-Pass { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Fail { param($msg) Write-Host "[!!] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "[--] $msg" -ForegroundColor Gray }

# Logging
function Log { param($msg) Add-Content -Path $LogFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" }

# ============================================================
# Phase 1: System Prerequisites
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Jan Document Plugin Installer v2.0.0" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Log "=== Installation started ==="
Set-Location $PluginDir

# 1.1 Python 3.12 Check
Write-Step "Checking Python version..."

$pythonCmd = $null
$pythonPaths = @(
    "python",
    "python3",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "C:\Python312\python.exe"
)

foreach ($path in $pythonPaths) {
    try {
        $version = & $path --version 2>&1
        if ($version -match "Python 3\.12") {
            $pythonCmd = $path
            break
        }
    } catch { continue }
}

if (-not $pythonCmd) {
    Write-Fail "Python 3.12 not found!"
    Write-Info "Installing via winget..."

    try {
        winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
        Start-Sleep -Seconds 5

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        $pythonCmd = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"

        if (-not (Test-Path $pythonCmd)) {
            $pythonCmd = "python"
        }
    } catch {
        Write-Fail "Failed to install Python 3.12"
        Write-Info "Please install manually from: https://www.python.org/downloads/release/python-3120/"
        Log "FAILED: Python 3.12 installation"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Verify Python
try {
    $version = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
    if ($version -eq "3.12") {
        Write-Pass "Python 3.12 verified"
        Log "PASS: Python $version"
    } else {
        throw "Wrong version: $version (need 3.12)"
    }
} catch {
    Write-Fail "Python 3.12 verification failed: $_"
    Log "FAILED: Python verification - $_"
    Read-Host "Press Enter to exit"
    exit 1
}

# 1.2 uv Package Manager
Write-Step "Checking uv package manager..."

$uvAvailable = $false
try {
    $uvVersion = uv --version 2>&1
    if ($uvVersion -match "uv") {
        $uvAvailable = $true
        Write-Pass "uv available: $uvVersion"
    }
} catch {}

if (-not $uvAvailable) {
    Write-Info "Installing uv..."
    try {
        & $pythonCmd -m pip install uv --quiet
        Write-Pass "uv installed"
        Log "PASS: uv installed"
    } catch {
        Write-Fail "Failed to install uv: $_"
        Log "FAILED: uv installation - $_"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# 1.3 Tesseract OCR (REQUIRED)
Write-Step "Checking Tesseract OCR..."

$tesseractPath = $null
$tesseractPaths = @(
    "C:\Program Files\Tesseract-OCR\tesseract.exe",
    "C:\Tesseract-OCR\tesseract.exe",
    "$env:LOCALAPPDATA\Programs\Tesseract-OCR\tesseract.exe"
)

# Check if tesseract is in PATH
try {
    $tesseractVersion = tesseract --version 2>&1
    if ($tesseractVersion -match "tesseract") {
        $tesseractPath = (Get-Command tesseract).Source
    }
} catch {}

# Check common paths
if (-not $tesseractPath) {
    foreach ($path in $tesseractPaths) {
        if (Test-Path $path) {
            $tesseractPath = $path
            break
        }
    }
}

if (-not $tesseractPath) {
    Write-Info "Tesseract not found. Installing via winget..."

    try {
        winget install UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements
        Start-Sleep -Seconds 5

        # Check again
        foreach ($path in $tesseractPaths) {
            if (Test-Path $path) {
                $tesseractPath = $path
                break
            }
        }

        if (-not $tesseractPath) {
            throw "Tesseract installed but not found in expected locations"
        }
    } catch {
        Write-Fail "Failed to install Tesseract: $_"
        Write-Info "Please install manually from: https://github.com/UB-Mannheim/tesseract/wiki"
        Log "FAILED: Tesseract installation - $_"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Verify Tesseract
try {
    $version = & $tesseractPath --version 2>&1 | Select-Object -First 1
    Write-Pass "Tesseract verified: $version"
    Write-Info "Path: $tesseractPath"
    Log "PASS: Tesseract - $tesseractPath"

    # Set environment variable for Python
    [Environment]::SetEnvironmentVariable("TESSERACT_CMD", $tesseractPath, "User")
    $env:TESSERACT_CMD = $tesseractPath
} catch {
    Write-Fail "Tesseract verification failed: $_"
    Log "FAILED: Tesseract verification - $_"
    Read-Host "Press Enter to exit"
    exit 1
}

# 1.4 Jan AI / llama-server
Write-Step "Checking Jan AI installation..."

$janPath = "$env:APPDATA\jan"
$llamaServer = $null
$modelPath = $null

if (Test-Path $janPath) {
    $llamaServers = Get-ChildItem -Path "$janPath\data\engines\llama.cpp" -Recurse -Filter "llama-server.exe" -ErrorAction SilentlyContinue

    # Prefer AVX2 version
    $llamaServer = $llamaServers | Where-Object { $_.Directory.Name -like "win-avx2-*" } | Select-Object -First 1
    if (-not $llamaServer) {
        $llamaServer = $llamaServers | Select-Object -First 1
    }
}

if ($llamaServer) {
    Write-Pass "llama-server found: $($llamaServer.FullName)"
    Log "PASS: llama-server - $($llamaServer.FullName)"
    $llamaServerPath = $llamaServer.FullName
} else {
    Write-Fail "Jan AI / llama-server not found"
    Write-Info "Please install Jan from: https://jan.ai"
    Log "WARNING: llama-server not found"
    $llamaServerPath = ""
}

# 1.4.1 Jan Version Compatibility Check
Write-Step "Checking Jan version compatibility..."

$requiredJanVersion = "0.6.8"
$janInstallDir = "$env:LOCALAPPDATA\Programs\jan"
$janDetectedVersion = $null

$packageJsonPaths = @(
    "$janInstallDir\resources\app.asar.unpacked\package.json",
    "$janInstallDir\resources\app\package.json"
)

foreach ($pjPath in $packageJsonPaths) {
    if (Test-Path $pjPath) {
        try {
            $pjContent = Get-Content $pjPath -Raw | ConvertFrom-Json
            $janDetectedVersion = $pjContent.version
            break
        } catch {
            Write-Info "Could not parse $pjPath"
        }
    }
}

if ($janDetectedVersion) {
    if ($janDetectedVersion -like "$requiredJanVersion*") {
        Write-Pass "Jan version $janDetectedVersion is compatible (requires $requiredJanVersion)"
        Log "PASS: Jan version $janDetectedVersion"
    } else {
        Write-Fail "Jan version $janDetectedVersion detected (recommended: $requiredJanVersion)"
        Write-Info "Newer Jan versions may have breaking API changes."
        Write-Info "Download Jan v${requiredJanVersion}: https://github.com/janhq/jan/releases/tag/v${requiredJanVersion}"
        Write-Info "A rollback_jan.ps1 script is included for convenience."
        Log "WARNING: Jan version mismatch - found $janDetectedVersion, need $requiredJanVersion"

        $continue = Read-Host "Continue anyway? (Y/n)"
        if ($continue -eq 'n' -or $continue -eq 'N') {
            Write-Info "Installation cancelled. Please install Jan v$requiredJanVersion first."
            exit 0
        }
    }
} else {
    Write-Info "Jan not detected (plugin can run standalone with bundled llama-server)"
    Log "INFO: Jan not detected"
}

# 1.5 Model File
Write-Step "Checking for GGUF model..."

$modelYmlFiles = Get-ChildItem -Path "$janPath\data\llamacpp\models" -Recurse -Filter "model.yml" -ErrorAction SilentlyContinue

foreach ($yml in $modelYmlFiles) {
    $content = Get-Content $yml.FullName -Raw
    if ($content -match "model_path:\s*(.+)") {
        $candidatePath = $Matches[1].Trim()
        if (Test-Path $candidatePath) {
            $modelPath = $candidatePath
            break
        }
    }
}

if ($modelPath) {
    $modelSize = [math]::Round((Get-Item $modelPath).Length / 1GB, 2)
    Write-Pass "Model found: $(Split-Path $modelPath -Leaf) ($modelSize GB)"
    Log "PASS: Model - $modelPath"
} else {
    Write-Fail "No GGUF model found"
    Write-Info "Please download a model in Jan (Settings > Models > Hub)"
    Log "WARNING: No model found"
    $modelPath = ""
}

# ============================================================
# Phase 2: Virtual Environment & Dependencies
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Phase 2: Python Environment Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 2.1 Create Virtual Environment
Write-Step "Creating virtual environment..."

if (Test-Path $VenvDir) {
    Write-Info "Existing venv found, removing..."
    Remove-Item -Recurse -Force $VenvDir
}

try {
    uv venv --python 3.12 $VenvDir
    Write-Pass "Virtual environment created"
    Log "PASS: venv created"
} catch {
    Write-Fail "Failed to create venv: $_"
    Log "FAILED: venv creation - $_"
    Read-Host "Press Enter to exit"
    exit 1
}

$venvPython = Join-Path $VenvDir "Scripts\python.exe"

# Verify venv Python
$venvVersion = & $venvPython --version
Write-Info "venv Python: $venvVersion"

# 2.2 Install Dependencies (in order - this matters!)

$dependencies = @(
    @{Name="PyTorch (CPU)"; Cmd="uv pip install torch --index-url https://download.pytorch.org/whl/cpu"; Test="import torch; print(torch.__version__)"},
    @{Name="Sentence Transformers"; Cmd="uv pip install sentence-transformers"; Test="from sentence_transformers import SentenceTransformer; print('OK')"},
    @{Name="ChromaDB"; Cmd="uv pip install chromadb"; Test="import chromadb; print(chromadb.__version__)"},
    @{Name="FastAPI + Uvicorn"; Cmd="uv pip install fastapi uvicorn httpx"; Test="import fastapi, uvicorn, httpx; print('OK')"},
    @{Name="PyMuPDF"; Cmd="uv pip install pymupdf"; Test="import fitz; print(fitz.version)"},
    @{Name="Document processors"; Cmd="uv pip install python-docx openpyxl PyPDF2 python-pptx Pillow"; Test="import docx, openpyxl, PyPDF2, pptx, PIL; print('OK')"},
    @{Name="Tesseract binding"; Cmd="uv pip install pytesseract"; Test="import pytesseract; print('OK')"},
    @{Name="Image processing (OCR pre/post)"; Cmd="uv pip install opencv-python-headless numpy scipy"; Test="import cv2, numpy, scipy; print('OK')"},
    @{Name="Utilities"; Cmd="uv pip install pydantic python-multipart aiofiles tiktoken"; Test="import pydantic, tiktoken; print('OK')"}
)

foreach ($dep in $dependencies) {
    Write-Step "Installing $($dep.Name)..."

    try {
        Invoke-Expression $dep.Cmd 2>&1 | Out-Null

        # Verify installation
        $result = & $venvPython -c $dep.Test 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Pass "$($dep.Name) installed: $result"
            Log "PASS: $($dep.Name)"
        } else {
            throw "Verification failed: $result"
        }
    } catch {
        Write-Fail "Failed to install $($dep.Name): $_"
        Log "FAILED: $($dep.Name) - $_"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# 2.3 Full Verification
Write-Step "Running full dependency verification..."

$verifyScript = @"
import sys
modules = [
    'torch', 'sentence_transformers', 'chromadb',
    'fastapi', 'uvicorn', 'httpx', 'fitz',
    'docx', 'openpyxl', 'PyPDF2', 'pptx', 'PIL',
    'pytesseract', 'pydantic', 'tiktoken',
    'cv2', 'numpy', 'scipy'
]
failed = []
for m in modules:
    try:
        __import__(m)
    except ImportError as e:
        failed.append(f'{m}: {e}')
if failed:
    print('FAILED:')
    for f in failed:
        print(f'  {f}')
    sys.exit(1)
print('All modules OK')
"@

$result = & $venvPython -c $verifyScript 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Pass "All dependencies verified"
    Log "PASS: Full verification"
} else {
    Write-Fail "Dependency verification failed:"
    Write-Host $result
    Log "FAILED: Full verification - $result"
    Read-Host "Press Enter to exit"
    exit 1
}

# ============================================================
# Phase 3: Code Patches
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Phase 3: Applying Code Patches" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 3.1 Fix Unicode Banner in jan_proxy.py
Write-Step "Patching Unicode characters for Windows console..."

$proxyFile = Join-Path $PluginDir "jan_proxy.py"
if (Test-Path $proxyFile) {
    $content = Get-Content $proxyFile -Raw -Encoding UTF8
    $originalContent = $content

    # Replace Unicode box-drawing with ASCII
    $content = $content -replace [char]0x2554, '+' # U+2554
    $content = $content -replace [char]0x2557, '+' # U+2557
    $content = $content -replace [char]0x255A, '+' # U+255A
    $content = $content -replace [char]0x255D, '+' # U+255D
    $content = $content -replace [char]0x2550, '=' # U+2550
    $content = $content -replace [char]0x2551, '|' # U+2551
    $content = $content -replace [char]0x2560, '+' # U+2560
    $content = $content -replace [char]0x2563, '+' # U+2563

    if ($content -ne $originalContent) {
        Set-Content $proxyFile $content -Encoding UTF8
        Write-Pass "Unicode characters patched"
        Log "PASS: Unicode patch applied"
    } else {
        Write-Info "No Unicode characters to patch (already fixed)"
    }
} else {
    Write-Fail "jan_proxy.py not found!"
    Log "WARNING: jan_proxy.py not found"
}

# ============================================================
# Phase 4: Configuration Files
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Phase 4: Creating Configuration" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 4.1 Update start-stack.ps1 with detected paths
Write-Step "Updating start-stack.ps1 configuration..."

$startStackFile = Join-Path $PluginDir "start-stack.ps1"
if ((Test-Path $startStackFile) -and $llamaServerPath -and $modelPath) {
    $content = Get-Content $startStackFile -Raw

    # Update llama-server path
    $content = $content -replace '\$LlamaServer = ".+"', "`$LlamaServer = `"$($llamaServerPath -replace '\\','\\')`""

    # Update model path
    $content = $content -replace '\$ModelPath = ".+"', "`$ModelPath = `"$($modelPath -replace '\\','\\')`""

    Set-Content $startStackFile $content -Encoding UTF8
    Write-Pass "start-stack.ps1 updated with detected paths"
    Log "PASS: start-stack.ps1 updated"
} else {
    Write-Info "Skipping start-stack.ps1 update (missing paths)"
}

# 4.2 Create Jan model configuration
Write-Step "Creating Jan model configuration..."

$janModelsDir = "$env:APPDATA\Jan\data\models\document-plugin"
if (-not (Test-Path $janModelsDir)) {
    New-Item -ItemType Directory -Path $janModelsDir -Force | Out-Null
}

$modelJson = @{
    id = "jan-nano-128k"
    object = "model"
    name = "Jan Nano + Document RAG"
    version = "1.0"
    description = "Jan Nano 128K with document retrieval via Jan Document Plugin. Uploaded documents are automatically searched and injected as context."
    format = "api"
    settings = @{
        ctx_len = 8192
        api_base = "http://localhost:1338/v1"
    }
    parameters = @{
        temperature = 0.7
        top_p = 0.95
        stream = $true
        max_tokens = 4096
    }
    metadata = @{
        author = "Jan Document Plugin"
        tags = @("rag", "document", "local", "jan-nano")
    }
    engine = "openai"
} | ConvertTo-Json -Depth 10

Set-Content "$janModelsDir\model.json" $modelJson -Encoding UTF8
Write-Pass "Jan model configuration created"
Log "PASS: Jan model config"

# 4.3 Update Jan OpenAI extension settings
Write-Step "Updating Jan OpenAI extension settings..."

$openaiSettingsDir = "$env:APPDATA\jan\settings\@janhq\inference-openai-extension"
if (-not (Test-Path $openaiSettingsDir)) {
    New-Item -ItemType Directory -Path $openaiSettingsDir -Force | Out-Null
}

$openaiSettings = @{
    apiKey = "local"
    apiBaseUrl = "http://localhost:1338/v1"
    models = @(
        @{
            id = "jan-nano-128k"
            name = "Jan Nano + Document RAG"
            owned_by = "local"
        }
    )
} | ConvertTo-Json -Depth 10

Set-Content "$openaiSettingsDir\settings.json" $openaiSettings -Encoding UTF8
Write-Pass "Jan OpenAI extension configured"
Log "PASS: Jan OpenAI settings"

# 4.4 Create config.env
Write-Step "Creating config.env..."

$configEnv = @"
# Jan Document Plugin Configuration
# Auto-generated by installer

TESSERACT_PATH=$tesseractPath
PROXY_PORT=1338
JAN_PORT=11435
STORAGE_DIR=.\jan_doc_store
EMBEDDING_MODEL=all-MiniLM-L6-v2
AUTO_INJECT=true
MAX_CONTEXT_TOKENS=8000
LLAMA_SERVER=$llamaServerPath
MODEL_PATH=$modelPath
"@

Set-Content (Join-Path $PluginDir "config.env") $configEnv -Encoding UTF8
Write-Pass "config.env created"
Log "PASS: config.env"

# ============================================================
# Phase 5: Pre-download Models
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Phase 5: Downloading Embedding Model" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Step "Pre-downloading sentence-transformers model..."
Write-Info "This happens once and may take 1-2 minutes..."

try {
    & $venvPython -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('all-MiniLM-L6-v2'); print('Model ready')" 2>&1
    Write-Pass "Embedding model downloaded"
    Log "PASS: Embedding model"
} catch {
    Write-Fail "Failed to download embedding model: $_"
    Log "WARNING: Embedding model download failed"
}

# ============================================================
# Phase 6: Final Verification
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Phase 6: Installation Verification" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true
$checkResults = @()

# Checklist
$checks = @(
    @{Name="Python 3.12 in venv"; Pass=$false},
    @{Name="PyTorch"; Pass=$false},
    @{Name="Sentence Transformers"; Pass=$false},
    @{Name="ChromaDB"; Pass=$false},
    @{Name="FastAPI"; Pass=$false},
    @{Name="Tesseract configured"; Pass=$false},
    @{Name="OpenCV (OCR processing)"; Pass=$false},
    @{Name="jan_proxy.py exists"; Pass=$false},
    @{Name="document_processor.py exists"; Pass=$false}
)

# Run checks
$checks[0].Pass = (& $venvPython -c "import sys; exit(0 if sys.version_info[:2]==(3,12) else 1)" 2>&1; $LASTEXITCODE -eq 0)
$checks[1].Pass = (& $venvPython -c "import torch" 2>&1; $LASTEXITCODE -eq 0)
$checks[2].Pass = (& $venvPython -c "from sentence_transformers import SentenceTransformer" 2>&1; $LASTEXITCODE -eq 0)
$checks[3].Pass = (& $venvPython -c "import chromadb" 2>&1; $LASTEXITCODE -eq 0)
$checks[4].Pass = (& $venvPython -c "import fastapi" 2>&1; $LASTEXITCODE -eq 0)
$checks[5].Pass = (Test-Path $tesseractPath)
$checks[6].Pass = (& $venvPython -c "import cv2" 2>&1; $LASTEXITCODE -eq 0)
$checks[7].Pass = (Test-Path (Join-Path $PluginDir "jan_proxy.py"))
$checks[8].Pass = (Test-Path (Join-Path $PluginDir "document_processor.py"))

foreach ($check in $checks) {
    if ($check.Pass) {
        Write-Pass $check.Name
    } else {
        Write-Fail $check.Name
        $allPassed = $false
    }
}

# ============================================================
# Summary
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

if ($allPassed) {
    Write-Host "  Installation Complete!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Start the stack: .\start-stack.ps1" -ForegroundColor White
    Write-Host "  2. Open Jan and select 'Jan Nano + Document RAG' model" -ForegroundColor White
    Write-Host "  3. Upload documents:" -ForegroundColor White
    Write-Host "     curl -X POST http://localhost:1338/documents -F 'file=@doc.pdf'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Architecture:" -ForegroundColor Gray
    Write-Host "  Jan UI --> Plugin (1338) --> llama-server (11435)" -ForegroundColor Gray
    Write-Host ""
    Log "=== Installation completed successfully ==="
} else {
    Write-Host "  Installation Incomplete" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Some checks failed. Review the log: $LogFile" -ForegroundColor Yellow
    Log "=== Installation completed with errors ==="
}

Write-Host ""
Read-Host "Press Enter to exit"
