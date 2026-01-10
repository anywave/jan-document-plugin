# ============================================================================
# Jan Document Plugin - Windows PowerShell Installer
# ============================================================================
# Run with: PowerShell -ExecutionPolicy Bypass -File install.ps1
# ============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   Jan Document Plugin - Windows Installer v1.0.0" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $InstallDir

Write-Host "Install directory: $InstallDir"
Write-Host ""

# ============================================================================
# Check Python Installation
# ============================================================================
Write-Host "[1/6] Checking Python installation..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.10 or later from:"
    Write-Host "  https://www.python.org/downloads/"
    Write-Host ""
    Write-Host "Make sure to check 'Add Python to PATH' during installation."
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# ============================================================================
# Create Virtual Environment
# ============================================================================
Write-Host ""
Write-Host "[2/6] Creating virtual environment..." -ForegroundColor Yellow

if (Test-Path "venv") {
    Write-Host "  Virtual environment already exists, skipping..." -ForegroundColor Gray
} else {
    python -m venv venv
    Write-Host "  Created virtual environment" -ForegroundColor Green
}

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1"

# ============================================================================
# Install Python Dependencies
# ============================================================================
Write-Host ""
Write-Host "[3/6] Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "  This may take a few minutes on first run..."
Write-Host ""

pip install --upgrade pip | Out-Null
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "  Dependencies installed successfully" -ForegroundColor Green

# ============================================================================
# Download and Install Tesseract OCR
# ============================================================================
Write-Host ""
Write-Host "[4/6] Setting up Tesseract OCR..." -ForegroundColor Yellow

$TesseractDir = Join-Path $InstallDir "tesseract"
$TesseractExe = Join-Path $TesseractDir "tesseract.exe"
$TesseractZip = Join-Path $InstallDir "tesseract-portable.zip"

# Tesseract portable URL (using GitHub releases)
$TesseractUrl = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"

if (Test-Path $TesseractExe) {
    Write-Host "  Tesseract already installed in package" -ForegroundColor Green
} else {
    # Check system installation first
    $SystemTesseract = "C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    if (Test-Path $SystemTesseract) {
        Write-Host "  Found system Tesseract: $SystemTesseract" -ForegroundColor Green
        $TesseractExe = $SystemTesseract
    } else {
        Write-Host "  Tesseract not found. Attempting to install via winget..." -ForegroundColor Yellow
        
        try {
            # Try winget first
            winget install --id UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements
            
            if (Test-Path $SystemTesseract) {
                Write-Host "  Tesseract installed via winget" -ForegroundColor Green
                $TesseractExe = $SystemTesseract
            }
        } catch {
            Write-Host ""
            Write-Host "  Could not auto-install Tesseract." -ForegroundColor Yellow
            Write-Host "  Please install manually from:" -ForegroundColor Yellow
            Write-Host "    https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "  OCR features will be disabled until Tesseract is installed." -ForegroundColor Yellow
            $TesseractExe = ""
        }
    }
}

# ============================================================================
# Download Embedding Model
# ============================================================================
Write-Host ""
Write-Host "[5/6] Pre-downloading embedding model..." -ForegroundColor Yellow
Write-Host "  This happens once and may take 1-2 minutes..."

python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); print('  Model downloaded successfully')"

# ============================================================================
# Create Launcher Scripts
# ============================================================================
Write-Host ""
Write-Host "[6/6] Creating launcher..." -ForegroundColor Yellow

# Create config file
$ConfigContent = @"
# Jan Document Plugin Configuration
TESSERACT_PATH=$TesseractExe
PROXY_PORT=1338
JAN_PORT=1337
STORAGE_DIR=.\jan_doc_store
EMBEDDING_MODEL=all-MiniLM-L6-v2
AUTO_INJECT=true
MAX_CONTEXT_TOKENS=8000
"@

$ConfigContent | Out-File -FilePath "config.env" -Encoding UTF8
Write-Host "  Configuration saved to config.env" -ForegroundColor Green

# ============================================================================
# Create Desktop Shortcut (Optional)
# ============================================================================
Write-Host ""
$createShortcut = Read-Host "Create desktop shortcut? (Y/N)"

if ($createShortcut -eq "Y" -or $createShortcut -eq "y") {
    $WshShell = New-Object -ComObject WScript.Shell
    $Desktop = [Environment]::GetFolderPath("Desktop")
    $Shortcut = $WshShell.CreateShortcut("$Desktop\Jan Document Plugin.lnk")
    $Shortcut.TargetPath = Join-Path $InstallDir "JanDocumentPlugin.exe"
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.Description = "Jan Document Plugin - Offline Document Processing"
    $Shortcut.Save()
    Write-Host "  Desktop shortcut created" -ForegroundColor Green
}

# ============================================================================
# Installation Complete
# ============================================================================
Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "   Installation Complete!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the Jan Document Plugin:"
Write-Host ""
Write-Host "  1. Make sure Jan is running with Local API Server enabled"
Write-Host "     (Jan Settings -> Local API Server -> Enable)"
Write-Host ""
Write-Host "  2. Double-click: JanDocumentPlugin.exe"
Write-Host "     Or run: .\start_proxy.bat"
Write-Host ""
Write-Host "  3. Access the web interface at:"
Write-Host "     http://localhost:1338" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""

Read-Host "Press Enter to exit"
