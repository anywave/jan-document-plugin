# rollback_jan.ps1 — Jan v0.6.8 Rollback Helper
# Downloads and installs Jan v0.6.8 for compatibility with Jan Document Plugin
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File rollback_jan.ps1

param(
    [string]$JanVersion = "0.6.8"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Jan v$JanVersion Rollback Helper" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- Detect current Jan version ---
$JanDir = "$env:LOCALAPPDATA\Programs\jan"
$CurrentVersion = $null

if (Test-Path $JanDir) {
    $PkgCandidates = @(
        "$JanDir\resources\app.asar.unpacked\package.json",
        "$JanDir\resources\app\package.json"
    )
    foreach ($PkgPath in $PkgCandidates) {
        if (Test-Path $PkgPath) {
            try {
                $PkgJson = Get-Content $PkgPath -Raw | ConvertFrom-Json
                $CurrentVersion = $PkgJson.version
            } catch {
                # Ignore parse errors
            }
            break
        }
    }
}

if ($CurrentVersion) {
    Write-Host "Current Jan version: v$CurrentVersion" -ForegroundColor Yellow
    if ($CurrentVersion -like "$JanVersion*") {
        Write-Host "Jan v$JanVersion is already installed. No rollback needed." -ForegroundColor Green
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 0
    }
} else {
    Write-Host "No existing Jan installation detected." -ForegroundColor Yellow
}

# --- Confirm with user ---
Write-Host ""
Write-Host "This script will download and install Jan v$JanVersion." -ForegroundColor White
if ($CurrentVersion) {
    Write-Host "Your current Jan v$CurrentVersion will be replaced." -ForegroundColor Red
}
Write-Host ""
$Confirm = Read-Host "Continue? (y/N)"
if ($Confirm -notin @("y", "Y", "yes", "Yes")) {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

# --- Download installer ---
$InstallerUrl = "https://github.com/janhq/jan/releases/download/v$JanVersion/jan-win-x64-$JanVersion.exe"
$TempDir = [System.IO.Path]::GetTempPath()
$InstallerPath = Join-Path $TempDir "jan-v$JanVersion-setup.exe"

Write-Host ""
Write-Host "Downloading Jan v$JanVersion installer..." -ForegroundColor Cyan
Write-Host "URL: $InstallerUrl" -ForegroundColor DarkGray

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $InstallerUrl -OutFile $InstallerPath -UseBasicParsing
    $ProgressPreference = 'Continue'
} catch {
    Write-Host ""
    Write-Host "Download failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "You can manually download Jan v$JanVersion from:" -ForegroundColor Yellow
    Write-Host "  https://github.com/janhq/jan/releases/tag/v$JanVersion" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

$FileSize = (Get-Item $InstallerPath).Length / 1MB
Write-Host "Downloaded: $([math]::Round($FileSize, 1)) MB" -ForegroundColor Green

# --- Close Jan if running ---
$JanProcs = Get-Process -Name "jan" -ErrorAction SilentlyContinue
if ($JanProcs) {
    Write-Host ""
    Write-Host "Closing running Jan process..." -ForegroundColor Yellow
    $JanProcs | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# --- Run installer ---
Write-Host ""
Write-Host "Launching Jan v$JanVersion installer..." -ForegroundColor Cyan
Write-Host "Follow the installer prompts to complete the rollback." -ForegroundColor DarkGray
Write-Host ""

try {
    Start-Process -FilePath $InstallerPath -Wait
} catch {
    Write-Host "Failed to launch installer: $_" -ForegroundColor Red
    Write-Host "Installer saved at: $InstallerPath" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# --- Verify ---
$NewVersion = $null
foreach ($PkgPath in $PkgCandidates) {
    if (Test-Path $PkgPath) {
        try {
            $PkgJson = Get-Content $PkgPath -Raw | ConvertFrom-Json
            $NewVersion = $PkgJson.version
        } catch { }
        break
    }
}

Write-Host ""
if ($NewVersion -and $NewVersion -like "$JanVersion*") {
    Write-Host "Jan v$NewVersion installed successfully!" -ForegroundColor Green
} elseif ($NewVersion) {
    Write-Host "Jan v$NewVersion detected (expected v$JanVersion)." -ForegroundColor Yellow
    Write-Host "You may need to manually install the correct version." -ForegroundColor Yellow
} else {
    Write-Host "Could not verify Jan version after install." -ForegroundColor Yellow
}

# --- Cleanup ---
if (Test-Path $InstallerPath) {
    Remove-Item $InstallerPath -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Rollback complete. You can now use Jan Document Plugin." -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"
