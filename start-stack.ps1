# Jan Document Plugin Stack Startup Script
# Starts: llama-server + Jan Document Plugin (RAG middleware)
# Jan UI connects to Plugin on port 1338

param(
    [switch]$SkipLlama,
    [switch]$Installed,       # Use bundled paths (.\llm\, .\models\)
    [int]$PluginPort = 1338,
    [int]$LlamaPort = 11435,
    [ValidateSet("jan-nano", "qwen2.5-7b")]
    [string]$Model = "qwen2.5-7b"
)

# Configuration — auto-detect machine and engine variant
$hostname = hostname

# Engine variant: prefer Vulkan (GPU) over AVX2 (CPU)
$VulkanServer = "$env:APPDATA\Jan\data\engines\llama.cpp\win-vulkan-x64\b5857\llama-server.exe"
$Avx2Server = "$env:APPDATA\Jan\data\engines\llama.cpp\win-avx2-x64\b5857\llama-server.exe"

# Model paths by name
$ModelPaths = @{
    "jan-nano" = @{
        "DELL"    = "$env:USERPROFILE\Documents\Jan Stuff\Previous Jan\jan-nano-128k-iQ4_XS.gguf"
        "RADIX"   = "$env:APPDATA\Jan\data\models\huggingface.co\Menlo\Jan-nano-128k-gguf\jan-nano-128k-iQ4_XS.gguf"
        "DEFAULT" = "$env:APPDATA\Jan\data\models\huggingface.co\Menlo\Jan-nano-128k-gguf\jan-nano-128k-iQ4_XS.gguf"
        "Alias"   = "jan-nano-128k"
        "Params"  = "4B"
        "CtxSize" = 8192
    }
    "qwen2.5-7b" = @{
        "DELL"    = "$env:USERPROFILE\Documents\Jan Stuff\Models\Qwen2.5-7B-Instruct-GGUF\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
        "RADIX"   = "$env:USERPROFILE\Documents\Jan Stuff\Models\Qwen2.5-7B-Instruct-GGUF\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
        "DEFAULT" = "$env:USERPROFILE\Documents\Jan Stuff\Models\Qwen2.5-7B-Instruct-GGUF\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
        "Alias"   = "qwen2.5-7b-instruct"
        "Params"  = "7B"
        "CtxSize" = 8192
    }
}

$modelConfig = $ModelPaths[$Model]
$ModelAlias = $modelConfig["Alias"]
$ModelParams = $modelConfig["Params"]
$CtxSize = $modelConfig["CtxSize"]

# Select engine and model path based on hostname
if ($hostname -match "DELL") {
    if (Test-Path $VulkanServer) {
        $LlamaServer = $VulkanServer
        $EngineType = "Vulkan (GPU)"
    } else {
        $LlamaServer = $Avx2Server
        $EngineType = "AVX2 (CPU)"
    }
    $ModelPath = $modelConfig["DELL"]
} elseif ($hostname -match "RADIX") {
    $LlamaServer = "D:\jan appdata\engines\llama.cpp\win-vulkan-x64\b5857\llama-server.exe"
    if (-not (Test-Path $LlamaServer)) {
        $LlamaServer = "D:\jan appdata\engines\llama.cpp\win-avx2-x64\b5857\llama-server.exe"
        $EngineType = "AVX2 (CPU)"
    } else {
        $EngineType = "Vulkan (GPU)"
    }
    $ModelPath = $modelConfig["RADIX"]
} else {
    $LlamaServer = $Avx2Server
    $EngineType = "AVX2 (CPU)"
    $ModelPath = $modelConfig["DEFAULT"]
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   Jan Document Plugin Stack Launcher" -ForegroundColor Cyan
Write-Host "   v2.0.0-beta" -ForegroundColor DarkCyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- Installed mode: use bundled llama-server and model ---
if ($Installed) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $LlamaServer = Join-Path $scriptDir "llm\llama-server.exe"
    $ModelPath = (Get-ChildItem -Path (Join-Path $scriptDir "models") -Filter "*.gguf" | Sort-Object Name | Select-Object -First 1).FullName
    $EngineType = "Vulkan (GPU)"
    $ModelAlias = "bundled-model"
    $ModelParams = "bundled"
    $CtxSize = 4096
    $LlamaPort = 1337  # Default port for installed mode

    if (-not (Test-Path $LlamaServer)) {
        Write-Host "[!!] Bundled llama-server not found at: $LlamaServer" -ForegroundColor Red
        Write-Host "     Falling back to dev mode..." -ForegroundColor Yellow
        $Installed = $false
    } elseif (-not $ModelPath) {
        Write-Host "[!!] No .gguf model found in: $(Join-Path $scriptDir 'models')" -ForegroundColor Red
        Write-Host "     Falling back to dev mode..." -ForegroundColor Yellow
        $Installed = $false
    } else {
        Write-Host "[OK] Installed mode — using bundled components" -ForegroundColor Green
        Write-Host "     Engine: $LlamaServer" -ForegroundColor DarkGray
        Write-Host "     Model:  $(Split-Path $ModelPath -Leaf)" -ForegroundColor DarkGray
    }
}

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

        Write-Host "[..] Starting llama-server with $ModelAlias ($ModelParams, $EngineType)..." -ForegroundColor Yellow
        $LlamaArgs = "--model `"$ModelPath`" --port $LlamaPort --host 127.0.0.1 --ctx-size $CtxSize --alias $ModelAlias"
        if ($EngineType -match "Vulkan") {
            $LlamaArgs += " -ngl 99"
        }
        Start-Process -FilePath $LlamaServer -ArgumentList $LlamaArgs -WindowStyle Hidden
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

if (-not $scriptDir) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

if ($Installed) {
    # Installed mode — use the bundled executable
    $pluginExe = Join-Path $scriptDir "JanDocumentPlugin.exe"
    if (Test-Path $pluginExe) {
        Start-Process -FilePath $pluginExe -NoNewWindow
    } else {
        Write-Host "[!!] Bundled executable not found at $pluginExe" -ForegroundColor Red
        Write-Host "     Falling back to Python venv..." -ForegroundColor Yellow
        $Installed = $false
    }
}

if (-not $Installed) {
    $venvPython = Join-Path $scriptDir "venv\Scripts\python.exe"
    $proxyScript = Join-Path $scriptDir "jan_proxy.py"

    if (-not (Test-Path $venvPython)) {
        Write-Host "[!!] Virtual environment not found at $venvPython" -ForegroundColor Red
        Write-Host "     Run: uv venv --python 3.12 venv && uv pip install -r requirements.txt" -ForegroundColor Gray
        exit 1
    }

    # Start the plugin
    Start-Process -FilePath $venvPython -ArgumentList "$proxyScript --port $PluginPort --jan-port $LlamaPort" -NoNewWindow
}

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
Write-Host "  Chat UI --> Plugin ($PluginPort) --> llama-server ($LlamaPort)" -ForegroundColor Gray
Write-Host "  Engine: $EngineType" -ForegroundColor Gray
Write-Host "  Model: $ModelAlias ($ModelParams parameters)" -ForegroundColor Gray
Write-Host ""
Write-Host "Chat UI:" -ForegroundColor Yellow
Write-Host "  http://localhost:$PluginPort/ui" -ForegroundColor White
Write-Host ""
Write-Host "To configure Jan (optional):" -ForegroundColor Yellow
Write-Host "  1. Open Jan" -ForegroundColor White
Write-Host "  2. Go to Settings > Model Providers > OpenAI" -ForegroundColor White
Write-Host "  3. Set API Base URL: http://localhost:$PluginPort/v1" -ForegroundColor White
Write-Host "  4. Set API Key: local (any string works)" -ForegroundColor White
Write-Host ""
Write-Host "To upload documents:" -ForegroundColor Yellow
Write-Host "  Use the Chat UI upload button, or:" -ForegroundColor White
Write-Host "  curl -X POST http://localhost:$PluginPort/documents -F 'file=@yourfile.pdf'" -ForegroundColor White
Write-Host ""
