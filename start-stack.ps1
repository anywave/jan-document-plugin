# Jan Document Plugin Stack Startup Script
# Starts: llama-server (jan-nano model) + Jan Document Plugin (RAG middleware)
# Jan UI connects to Plugin on port 1338

param(
    [switch]$SkipLlama,
    [int]$PluginPort = 1338,
    [int]$LlamaPort = 11435
)

# Configuration
# Path options - uncomment the one that matches your system
# Option 1: Standard Jan AppData location
# $LlamaServer = "$env:APPDATA\jan\data\engines\llama.cpp\win-avx2-x64\b5857\llama-server.exe"
# $ModelPath = "$env:APPDATA\Jan\data\models\huggingface.co\Menlo\Jan-nano-128k-gguf\jan-nano-128k-iQ4_XS.gguf"

# Option 2: Custom D: drive location (RADIX-Interface)
$LlamaServer = "D:\jan appdata\engines\llama.cpp\win-avx2-x64\b5857\llama-server.exe"
$ModelPath = "$env:APPDATA\Jan\data\models\huggingface.co\Menlo\Jan-nano-128k-gguf\jan-nano-128k-iQ4_XS.gguf"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   Jan Document Plugin Stack Launcher" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipLlama) {
    # Check if llama-server is already running on the port
    $portInUse = Get-NetTCPConnection -LocalPort $LlamaPort -ErrorAction SilentlyContinue

    if ($portInUse) {
        Write-Host "[OK] llama-server already running on port $LlamaPort" -ForegroundColor Green
    } else {
        # Verify model file exists
        if (-not (Test-Path $ModelPath)) {
            Write-Host "[!!] Model not found: $ModelPath" -ForegroundColor Red
            exit 1
        }

        Write-Host "[..] Starting llama-server with jan-nano-128k..." -ForegroundColor Yellow
        Start-Process -FilePath $LlamaServer -ArgumentList "--model `"$ModelPath`" --port $LlamaPort --host 127.0.0.1 --ctx-size 8192 --alias jan-nano-128k" -WindowStyle Hidden
        Start-Sleep -Seconds 8
        Write-Host "[OK] llama-server started on port $LlamaPort" -ForegroundColor Green
    }

    # Verify llama-server is responding
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$LlamaPort/v1/models" -TimeoutSec 10
        Write-Host "[OK] llama-server responding - model: $($response.data[0].id)" -ForegroundColor Green
    } catch {
        Write-Host "[!!] Warning: llama-server not responding yet (model still loading?)" -ForegroundColor Yellow
    }
}

# Check if plugin port is already in use
$portInUse = Get-NetTCPConnection -LocalPort $PluginPort -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[!!] Port $PluginPort already in use - killing existing process" -ForegroundColor Yellow
    $process = Get-Process -Id $portInUse.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $process.Id -Force
        Start-Sleep -Seconds 1
    }
}

# Start Jan Document Plugin
Write-Host ""
Write-Host "[..] Starting Jan Document Plugin..." -ForegroundColor Yellow

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $scriptDir "venv\Scripts\python.exe"
$proxyScript = Join-Path $scriptDir "jan_proxy.py"

if (-not (Test-Path $venvPython)) {
    Write-Host "[!!] Virtual environment not found at $venvPython" -ForegroundColor Red
    Write-Host "     Run: uv venv --python 3.12 venv && uv pip install -r requirements.txt" -ForegroundColor Gray
    exit 1
}

# Start the plugin
Start-Process -FilePath $venvPython -ArgumentList "$proxyScript --port $PluginPort --jan-port $LlamaPort" -NoNewWindow

Start-Sleep -Seconds 5

# Verify plugin is running
try {
    $models = Invoke-RestMethod -Uri "http://localhost:$PluginPort/v1/models" -TimeoutSec 5
    Write-Host "[OK] Plugin started on port $PluginPort" -ForegroundColor Green
    Write-Host "[OK] Available models: $($models.data.id -join ', ')" -ForegroundColor Green
} catch {
    Write-Host "[!!] Plugin may not have started correctly" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   Stack Ready!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Architecture:" -ForegroundColor Gray
Write-Host "  Jan UI --> Plugin ($PluginPort) --> llama-server ($LlamaPort)" -ForegroundColor Gray
Write-Host "  Model: jan-nano-128k (4B parameters)" -ForegroundColor Gray
Write-Host ""
Write-Host "To configure Jan:" -ForegroundColor Yellow
Write-Host "  1. Open Jan" -ForegroundColor White
Write-Host "  2. Go to Settings > Model Providers > OpenAI" -ForegroundColor White
Write-Host "  3. Set API Base URL: http://localhost:$PluginPort/v1" -ForegroundColor White
Write-Host "  4. Set API Key: local (any string works)" -ForegroundColor White
Write-Host "  5. Select model 'jan-nano-128k' in your chat" -ForegroundColor White
Write-Host ""
Write-Host "To upload documents:" -ForegroundColor Yellow
Write-Host "  curl -X POST http://localhost:$PluginPort/documents -F 'file=@yourfile.pdf'" -ForegroundColor White
Write-Host ""
