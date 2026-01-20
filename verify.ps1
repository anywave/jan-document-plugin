# Jan Document Plugin - Installation Verification Script
# Runs all functional tests to validate the installation
# Version 2.0.0

param(
    [switch]$SkipServerTests,
    [int]$PluginPort = 1338,
    [int]$LlamaPort = 11435
)

$ErrorActionPreference = "Continue"  # Don't stop on errors during tests

# Configuration
$PluginDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $PluginDir "venv\Scripts\python.exe"
$TestResults = @()

# Colors
function Write-TestName { param($msg) Write-Host "  Testing: $msg" -ForegroundColor Cyan -NoNewline }
function Write-Pass { Write-Host " [PASS]" -ForegroundColor Green }
function Write-Fail { Write-Host " [FAIL]" -ForegroundColor Red }
function Write-Skip { Write-Host " [SKIP]" -ForegroundColor Yellow }

function Add-Result {
    param($Name, $Passed, $Details = "")
    $script:TestResults += @{
        Name = $Name
        Passed = $Passed
        Details = $Details
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Jan Document Plugin - Verification" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# Section 1: Environment Tests
# ============================================================

Write-Host "Section 1: Environment Tests" -ForegroundColor Yellow
Write-Host "--------------------------------------------"

# Test 1.1: Python 3.12 in venv
Write-TestName "Python 3.12 in venv"
try {
    $version = & $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
    if ($version -eq "3.12") {
        Write-Pass
        Add-Result "Python 3.12 in venv" $true
    } else {
        Write-Fail
        Add-Result "Python 3.12 in venv" $false "Got: $version"
    }
} catch {
    Write-Fail
    Add-Result "Python 3.12 in venv" $false $_
}

# Test 1.2: Tesseract available
Write-TestName "Tesseract OCR"
try {
    $tesseractPath = $env:TESSERACT_CMD
    if (-not $tesseractPath) {
        $tesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"
    }
    if (Test-Path $tesseractPath) {
        $version = & $tesseractPath --version 2>&1 | Select-Object -First 1
        Write-Pass
        Add-Result "Tesseract OCR" $true $version
    } else {
        Write-Fail
        Add-Result "Tesseract OCR" $false "Not found at $tesseractPath"
    }
} catch {
    Write-Fail
    Add-Result "Tesseract OCR" $false $_
}

Write-Host ""

# ============================================================
# Section 2: Python Module Tests
# ============================================================

Write-Host "Section 2: Python Module Tests" -ForegroundColor Yellow
Write-Host "--------------------------------------------"

$modules = @(
    @{Name="torch"; Import="import torch"},
    @{Name="sentence_transformers"; Import="from sentence_transformers import SentenceTransformer"},
    @{Name="chromadb"; Import="import chromadb"},
    @{Name="fastapi"; Import="import fastapi"},
    @{Name="uvicorn"; Import="import uvicorn"},
    @{Name="httpx"; Import="import httpx"},
    @{Name="fitz (PyMuPDF)"; Import="import fitz"},
    @{Name="docx"; Import="import docx"},
    @{Name="openpyxl"; Import="import openpyxl"},
    @{Name="pytesseract"; Import="import pytesseract"},
    @{Name="cv2 (OpenCV)"; Import="import cv2"},
    @{Name="numpy"; Import="import numpy"},
    @{Name="PIL (Pillow)"; Import="from PIL import Image"},
    @{Name="pydantic"; Import="import pydantic"},
    @{Name="tiktoken"; Import="import tiktoken"}
)

foreach ($mod in $modules) {
    Write-TestName $mod.Name
    try {
        & $VenvPython -c $mod.Import 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Pass
            Add-Result $mod.Name $true
        } else {
            Write-Fail
            Add-Result $mod.Name $false "Import failed"
        }
    } catch {
        Write-Fail
        Add-Result $mod.Name $false $_
    }
}

# Test OCR Pipeline module
Write-TestName "ocr_processor module"
try {
    & $VenvPython -c "from ocr_processor import OCRPipeline, preprocess_image, postprocess_text" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Pass
        Add-Result "ocr_processor module" $true
    } else {
        Write-Fail
        Add-Result "ocr_processor module" $false "Import failed"
    }
} catch {
    Write-Fail
    Add-Result "ocr_processor module" $false $_
}

Write-Host ""

# ============================================================
# Section 3: OCR Processing Tests
# ============================================================

Write-Host "Section 3: OCR Processing Tests" -ForegroundColor Yellow
Write-Host "--------------------------------------------"

# Test 3.1: OCR Pre-processing
Write-TestName "OCR Pre-processing (image enhancement)"
$preProcessTest = @"
from PIL import Image
import numpy as np
from ocr_processor import OCRPreProcessor

# Create a test image
img = Image.new('RGB', (100, 100), color='white')
preprocessor = OCRPreProcessor()
processed = preprocessor.process(img)
print('OK' if processed is not None else 'FAIL')
"@

try {
    $result = & $VenvPython -c $preProcessTest 2>&1
    if ($result -match "OK") {
        Write-Pass
        Add-Result "OCR Pre-processing" $true
    } else {
        Write-Fail
        Add-Result "OCR Pre-processing" $false $result
    }
} catch {
    Write-Fail
    Add-Result "OCR Pre-processing" $false $_
}

# Test 3.2: OCR Post-processing
Write-TestName "OCR Post-processing (artifact cleanup)"
$postProcessTest = @"
from ocr_processor import OCRPostProcessor

postprocessor = OCRPostProcessor()
# Test broken word fix
text1 = postprocessor.process('docu-\nment')
# Test common word fix
text2 = postprocessor.process('tbe quick brown fox')
# Test whitespace normalization
text3 = postprocessor.process('hello   world')

if 'document' in text1 and 'the' in text2 and 'hello world' in text3:
    print('OK')
else:
    print(f'FAIL: {text1}, {text2}, {text3}')
"@

try {
    $result = & $VenvPython -c $postProcessTest 2>&1
    if ($result -match "OK") {
        Write-Pass
        Add-Result "OCR Post-processing" $true
    } else {
        Write-Fail
        Add-Result "OCR Post-processing" $false $result
    }
} catch {
    Write-Fail
    Add-Result "OCR Post-processing" $false $_
}

# Test 3.3: Full OCR Pipeline with Tesseract
Write-TestName "Full OCR Pipeline (with Tesseract)"
$fullOcrTest = @"
from PIL import Image, ImageDraw, ImageFont
from ocr_processor import OCRPipeline
import pytesseract

# Create test image with text
img = Image.new('RGB', (300, 100), color='white')
draw = ImageDraw.Draw(img)
draw.text((10, 30), 'TEST_OCR_12345', fill='black')

pipeline = OCRPipeline()
text, metadata = pipeline.process_image(img)

if 'TEST' in text or '12345' in text:
    print('OK')
else:
    print(f'FAIL: Could not read text, got: {text[:50]}')
"@

try {
    $result = & $VenvPython -c $fullOcrTest 2>&1
    if ($result -match "OK") {
        Write-Pass
        Add-Result "Full OCR Pipeline" $true
    } else {
        Write-Fail
        Add-Result "Full OCR Pipeline" $false $result
    }
} catch {
    Write-Fail
    Add-Result "Full OCR Pipeline" $false $_
}

Write-Host ""

# ============================================================
# Section 4: Document Processor Tests
# ============================================================

Write-Host "Section 4: Document Processor Tests" -ForegroundColor Yellow
Write-Host "--------------------------------------------"

# Test 4.1: Document Processor initialization
Write-TestName "DocumentProcessor init"
$dpInitTest = @"
from document_processor import DocumentProcessor
import tempfile
import os

temp_dir = tempfile.mkdtemp()
try:
    dp = DocumentProcessor(persist_directory=temp_dir)
    print('OK')
finally:
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
"@

try {
    $result = & $VenvPython -c $dpInitTest 2>&1
    if ($result -match "OK") {
        Write-Pass
        Add-Result "DocumentProcessor init" $true
    } else {
        Write-Fail
        Add-Result "DocumentProcessor init" $false $result
    }
} catch {
    Write-Fail
    Add-Result "DocumentProcessor init" $false $_
}

# Test 4.2: Text file ingestion
Write-TestName "Text file ingestion"
$textIngestTest = @"
from document_processor import DocumentProcessor
import tempfile
import os

temp_dir = tempfile.mkdtemp()
test_file = os.path.join(temp_dir, 'test.txt')

try:
    # Create test file
    with open(test_file, 'w') as f:
        f.write('VERIFY_TEST_CONTENT_12345')

    dp = DocumentProcessor(persist_directory=temp_dir)
    result = dp.ingest(test_file)

    if result.chunks and len(result.chunks) > 0:
        print('OK')
    else:
        print('FAIL: No chunks created')
finally:
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
"@

try {
    $result = & $VenvPython -c $textIngestTest 2>&1
    if ($result -match "OK") {
        Write-Pass
        Add-Result "Text file ingestion" $true
    } else {
        Write-Fail
        Add-Result "Text file ingestion" $false $result
    }
} catch {
    Write-Fail
    Add-Result "Text file ingestion" $false $_
}

# Test 4.3: Context retrieval (RAG query)
Write-TestName "Context retrieval (RAG)"
$ragTest = @"
from document_processor import DocumentProcessor
import tempfile
import os

temp_dir = tempfile.mkdtemp()
test_file = os.path.join(temp_dir, 'test.txt')

try:
    # Create test file with unique content
    with open(test_file, 'w') as f:
        f.write('The magic password is UNICORN_RAINBOW_42.')

    dp = DocumentProcessor(persist_directory=temp_dir)
    dp.ingest(test_file)

    # Query for the content
    context = dp.get_context('What is the magic password?')

    if 'UNICORN_RAINBOW_42' in context:
        print('OK')
    else:
        print(f'FAIL: Content not found in context: {context[:100]}')
finally:
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
"@

try {
    $result = & $VenvPython -c $ragTest 2>&1
    if ($result -match "OK") {
        Write-Pass
        Add-Result "Context retrieval (RAG)" $true
    } else {
        Write-Fail
        Add-Result "Context retrieval (RAG)" $false $result
    }
} catch {
    Write-Fail
    Add-Result "Context retrieval (RAG)" $false $_
}

Write-Host ""

# ============================================================
# Section 5: Server Tests (if not skipped)
# ============================================================

if (-not $SkipServerTests) {
    Write-Host "Section 5: Server Tests" -ForegroundColor Yellow
    Write-Host "--------------------------------------------"

    # Test 5.1: llama-server connectivity
    Write-TestName "llama-server (port $LlamaPort)"
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$LlamaPort/v1/models" -TimeoutSec 5 -ErrorAction Stop
        if ($response.data) {
            Write-Pass
            Add-Result "llama-server" $true $response.data[0].id
        } else {
            Write-Fail
            Add-Result "llama-server" $false "No models returned"
        }
    } catch {
        Write-Fail
        Add-Result "llama-server" $false "Not running or not responding"
    }

    # Test 5.2: Plugin connectivity
    Write-TestName "Plugin (port $PluginPort)"
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$PluginPort/v1/models" -TimeoutSec 5 -ErrorAction Stop
        if ($response.data) {
            Write-Pass
            Add-Result "Plugin" $true $response.data[0].id
        } else {
            Write-Fail
            Add-Result "Plugin" $false "No models returned"
        }
    } catch {
        Write-Fail
        Add-Result "Plugin" $false "Not running or not responding"
    }

    # Test 5.3: Document upload endpoint
    Write-TestName "Document upload endpoint"
    try {
        # Create a test file
        $testFile = Join-Path $env:TEMP "verify_test.txt"
        "VERIFY_UPLOAD_TEST_$(Get-Date -Format 'yyyyMMddHHmmss')" | Out-File -FilePath $testFile -Encoding UTF8 -NoNewline

        # Use curl.exe for multipart form upload (more compatible than Invoke-RestMethod -Form)
        $curlResult = & curl.exe -s -X POST "http://localhost:$PluginPort/documents" -F "file=@$testFile" 2>&1
        $response = $curlResult | ConvertFrom-Json

        Remove-Item $testFile -Force -ErrorAction SilentlyContinue

        if ($response.success) {
            Write-Pass
            Add-Result "Document upload" $true "Chunks: $($response.chunks)"
        } else {
            Write-Fail
            Add-Result "Document upload" $false $response.error
        }
    } catch {
        Write-Fail
        Add-Result "Document upload" $false $_
    }

    # Test 5.4: Document query endpoint
    Write-TestName "Document query endpoint"
    try {
        # Use curl.exe with form data (endpoint is /documents/query with form params)
        $curlResult = & curl.exe -s -X POST "http://localhost:$PluginPort/documents/query" -F "query=VERIFY" -F "n_results=1" 2>&1
        $response = $curlResult | ConvertFrom-Json

        if ($response.context -ne $null) {
            Write-Pass
            Add-Result "Document query" $true "Context length: $($response.context_length)"
        } else {
            Write-Fail
            Add-Result "Document query" $false "No context field"
        }
    } catch {
        Write-Fail
        Add-Result "Document query" $false $_
    }

    # Test 5.5: Chat completion (RAG)
    Write-TestName "Chat completion (RAG)"
    try {
        $body = @{
            model = "jan-nano-128k"
            messages = @(
                @{role = "user"; content = "Say hello"}
            )
            max_tokens = 50
        } | ConvertTo-Json -Depth 10

        $response = Invoke-RestMethod -Uri "http://localhost:$PluginPort/v1/chat/completions" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 180 -ErrorAction Stop

        if ($response.choices -and $response.choices[0].message.content) {
            Write-Pass
            Add-Result "Chat completion" $true "Tokens: $($response.usage.total_tokens)"
        } else {
            Write-Fail
            Add-Result "Chat completion" $false "No response content"
        }
    } catch {
        Write-Fail
        Add-Result "Chat completion" $false $_
    }

    Write-Host ""
} else {
    Write-Host "Section 5: Server Tests [SKIPPED]" -ForegroundColor Yellow
    Write-Host "--------------------------------------------"
    Write-Host "  Use -SkipServerTests:$false to run server tests" -ForegroundColor Gray
    Write-Host ""
}

# ============================================================
# Summary
# ============================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Verification Summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$passed = ($TestResults | Where-Object { $_.Passed }).Count
$failed = ($TestResults | Where-Object { -not $_.Passed }).Count
$total = $TestResults.Count

Write-Host "Total Tests: $total" -ForegroundColor White
Write-Host "Passed:      $passed" -ForegroundColor Green
Write-Host "Failed:      $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""

if ($failed -gt 0) {
    Write-Host "Failed Tests:" -ForegroundColor Red
    foreach ($result in ($TestResults | Where-Object { -not $_.Passed })) {
        Write-Host "  - $($result.Name): $($result.Details)" -ForegroundColor Red
    }
    Write-Host ""
}

if ($failed -eq 0) {
    Write-Host "All tests passed! Installation verified." -ForegroundColor Green
} else {
    Write-Host "Some tests failed. Please review and fix the issues above." -ForegroundColor Yellow
}

Write-Host ""

# Return exit code
exit $failed
