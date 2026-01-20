# Jan Document Plugin - Setup Requirements & Order of Operations

**Goal:** Childproof installation that tests each component before proceeding.

---

## Phase 1: System Prerequisites

### 1.1 Python 3.12 (NOT 3.13+)
**Why:** onnxruntime, chromadb lack wheels for Python 3.13+

```powershell
# Check
python --version  # Must be 3.12.x

# Install if missing
winget install Python.Python.3.12

# Verify
python -c "import sys; assert sys.version_info[:2] == (3, 12), 'Wrong Python version'"
```

**Test:** Exit code 0 = PASS

---

### 1.2 uv Package Manager
**Why:** More reliable than pip for complex dependency resolution

```powershell
# Check
uv --version

# Install if missing
pip install uv

# Verify
uv --version
```

**Test:** Returns version string = PASS

---

### 1.3 Tesseract OCR
**Why:** Required for OCR of scanned PDFs and images

```powershell
# Check
tesseract --version

# Install if missing
winget install UB-Mannheim.TesseractOCR

# Add to PATH (installer should do this)
# Default: C:\Program Files\Tesseract-OCR

# Verify
tesseract --version
```

**Test:** Returns version string = PASS

**Auto-correction:** If not in PATH, installer must:
1. Search common locations: `C:\Program Files\Tesseract-OCR`, `C:\Tesseract-OCR`
2. Add to system PATH
3. Or set `TESSERACT_CMD` environment variable

---

### 1.4 Jan AI Installation
**Why:** We use Jan's llama-server.exe for the LLM backend

```powershell
# Check for Jan
$janPath = "$env:APPDATA\jan"
Test-Path $janPath

# Check for llama-server
$llamaServer = Get-ChildItem -Path "$janPath\data\engines\llama.cpp" -Recurse -Filter "llama-server.exe" | Select-Object -First 1
$llamaServer.FullName
```

**Test:** llama-server.exe path found = PASS

**Auto-correction:** If Jan not installed:
1. Prompt user to install Jan from https://jan.ai
2. Or download llama-server binaries directly from llama.cpp releases

---

### 1.5 Model File
**Why:** Need a GGUF model for inference

```powershell
# Check Jan's model registry
$modelYml = "$env:APPDATA\jan\data\llamacpp\models\*\model.yml"
Get-Content $modelYml | Select-String "model_path"

# Parse actual model path from model.yml
# Example: model_path: C:\Users\abc\Documents\...\jan-nano-128k-iQ4_XS.gguf
```

**Test:** .gguf file exists at parsed path = PASS

**Auto-correction:** If no model found:
1. Download default model (jan-nano or similar)
2. Or prompt user to download via Jan UI first

---

## Phase 2: Virtual Environment & Dependencies

### 2.1 Create Virtual Environment

```powershell
cd C:\ANYWAVEREPO\jan-document-plugin
uv venv --python 3.12 venv

# Verify
.\venv\Scripts\python.exe --version
```

**Test:** Python 3.12.x in venv = PASS

---

### 2.2 Install Core Dependencies

**Order matters - install in sequence:**

```powershell
# 1. PyTorch (CPU) - foundation for ML
uv pip install torch --index-url https://download.pytorch.org/whl/cpu

# Verify
.\venv\Scripts\python.exe -c "import torch; print(torch.__version__)"
```

**Test:** torch imports = PASS

```powershell
# 2. Sentence Transformers - embeddings
uv pip install sentence-transformers

# Verify
.\venv\Scripts\python.exe -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

**Test:** sentence_transformers imports = PASS

```powershell
# 3. ChromaDB - vector store
uv pip install chromadb

# Verify
.\venv\Scripts\python.exe -c "import chromadb; print(chromadb.__version__)"
```

**Test:** chromadb imports = PASS

```powershell
# 4. FastAPI + Uvicorn - web server
uv pip install fastapi uvicorn httpx

# Verify
.\venv\Scripts\python.exe -c "import fastapi, uvicorn, httpx; print('OK')"
```

**Test:** All three import = PASS

```powershell
# 5. Document processing
uv pip install python-docx openpyxl PyPDF2 python-pptx Pillow

# Verify
.\venv\Scripts\python.exe -c "import docx, openpyxl, PyPDF2, pptx, PIL; print('OK')"
```

**Test:** All document processors import = PASS

```powershell
# 6. Tesseract Python binding
uv pip install pytesseract

# Verify (requires Tesseract installed)
.\venv\Scripts\python.exe -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

**Test:** Returns Tesseract version = PASS

```powershell
# 7. Remaining dependencies
uv pip install pydantic python-multipart aiofiles tiktoken

# Verify
.\venv\Scripts\python.exe -c "import pydantic, tiktoken; print('OK')"
```

**Test:** All imports succeed = PASS

---

### 2.3 Full Dependency Verification

```powershell
.\venv\Scripts\python.exe -c "
import sys
modules = [
    'torch', 'sentence_transformers', 'chromadb',
    'fastapi', 'uvicorn', 'httpx',
    'docx', 'openpyxl', 'PyPDF2', 'pptx', 'PIL',
    'pytesseract', 'pydantic', 'tiktoken'
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
"
```

**Test:** Exit code 0 = PASS

---

## Phase 3: Code Patches (Auto-Corrections)

### 3.1 Fix Unicode Banner

**Problem:** Windows console (cp1252) can't display Unicode box-drawing characters

**File:** `jan_proxy.py` line ~758

**Before:**
```python
print(f"""
╔══════════════════════════════════════════════════════════════╗
║            Jan Document Plugin v1.0.0                       ║
```

**After:**
```python
print(f"""
+==============================================================+
|            Jan Document Plugin v1.0.0                        |
```

**Auto-patch script:**
```powershell
$file = "jan_proxy.py"
$content = Get-Content $file -Raw
$content = $content -replace '╔', '+' -replace '╗', '+' -replace '╚', '+' -replace '╝', '+'
$content = $content -replace '═', '=' -replace '║', '|' -replace '╠', '+' -replace '╣', '+'
Set-Content $file $content -Encoding UTF8
```

---

### 3.2 Tesseract Path Configuration

**Problem:** pytesseract needs to know Tesseract location

**File:** `document_processor.py` (or add to jan_proxy.py startup)

**Add at top:**
```python
import pytesseract
import os

# Auto-detect Tesseract
tesseract_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Tesseract-OCR\tesseract.exe",
    os.environ.get("TESSERACT_CMD", ""),
]
for path in tesseract_paths:
    if path and os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        break
```

---

## Phase 4: Backend Setup

### 4.1 Start llama-server

```powershell
# Find llama-server
$llamaServer = (Get-ChildItem "$env:APPDATA\jan\data\engines\llama.cpp" -Recurse -Filter "llama-server.exe" |
    Where-Object { $_.Directory.Name -like "win-avx2-x64*" } |
    Select-Object -First 1).FullName

# Find model (parse from model.yml)
$modelYml = Get-ChildItem "$env:APPDATA\jan\data\llamacpp\models" -Recurse -Filter "model.yml" | Select-Object -First 1
$modelPath = (Get-Content $modelYml.FullName | Select-String "model_path:").Line.Split(":")[1].Trim()

# Start server
Start-Process -FilePath $llamaServer -ArgumentList "--model `"$modelPath`" --port 11435 --host 127.0.0.1 --ctx-size 8192" -WindowStyle Hidden

# Wait for startup
Start-Sleep -Seconds 8

# Verify
Invoke-RestMethod -Uri "http://localhost:11435/v1/models"
```

**Test:** Returns model list JSON = PASS

---

### 4.2 Start Plugin

```powershell
Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "jan_proxy.py --port 1338 --jan-port 11435" -NoNewWindow

Start-Sleep -Seconds 5

# Verify
Invoke-RestMethod -Uri "http://localhost:1338/v1/models"
```

**Test:** Returns model list JSON = PASS

---

## Phase 5: Functional Tests

### 5.1 Document Upload Test

```powershell
# Create test file
"This is a test document with magic word: INSTALLER_TEST_12345" | Out-File -FilePath "test_doc.txt"

# Upload
$response = Invoke-RestMethod -Uri "http://localhost:1338/documents" -Method Post -Form @{
    file = Get-Item "test_doc.txt"
}
$response.success

# Cleanup
Remove-Item "test_doc.txt"
```

**Test:** `$response.success` = True = PASS

---

### 5.2 Search/Retrieval Test

```powershell
$response = Invoke-RestMethod -Uri "http://localhost:1338/documents/search" -Method Post -Body (@{
    query = "magic word"
    top_k = 1
} | ConvertTo-Json) -ContentType "application/json"

$response.results[0].content -match "INSTALLER_TEST_12345"
```

**Test:** Match found = PASS

---

### 5.3 RAG Chat Test

```powershell
$response = Invoke-RestMethod -Uri "http://localhost:1338/v1/chat/completions" -Method Post -Body (@{
    model = "jan-nano-128k"
    messages = @(@{role = "user"; content = "What is the magic word in the test document?"})
    max_tokens = 100
} | ConvertTo-Json) -ContentType "application/json"

$response.choices[0].message.content -match "INSTALLER_TEST_12345"
```

**Test:** Response contains magic word = PASS

---

### 5.4 OCR Test (Tesseract)

```powershell
# This requires a test image with text
# Installer should include a test image

$response = Invoke-RestMethod -Uri "http://localhost:1338/documents" -Method Post -Form @{
    file = Get-Item "test_image.png"  # Image with known text
}
$response.success -and $response.chunks -gt 0
```

**Test:** Image processed with chunks > 0 = PASS

---

## Phase 6: Installation Complete Checklist

Before showing tutorial, ALL must pass:

- [ ] Python 3.12 installed and verified
- [ ] uv installed and verified
- [ ] Tesseract installed and in PATH
- [ ] Jan/llama-server found
- [ ] Model file found
- [ ] Virtual environment created
- [ ] All Python dependencies installed
- [ ] All Python imports verified
- [ ] Code patches applied (Unicode fix)
- [ ] llama-server starts and responds
- [ ] Plugin starts and responds
- [ ] Document upload works
- [ ] Document search works
- [ ] RAG chat works
- [ ] OCR works (Tesseract)

---

## Error Recovery Procedures

### If Python wrong version:
1. Install Python 3.12 via winget
2. Recreate venv with `uv venv --python 3.12 venv`

### If dependency install fails:
1. Clear cache: `uv cache clean`
2. Try individual installs in order
3. Check for conflicting packages

### If port in use:
1. Check: `netstat -ano | findstr :1338`
2. Kill process or use alternate port

### If Tesseract not found:
1. Reinstall: `winget install UB-Mannheim.TesseractOCR`
2. Manually add to PATH
3. Set TESSERACT_CMD environment variable

### If model not found:
1. Open Jan UI
2. Download a model (jan-nano recommended)
3. Re-run installer detection

---

## Files to Include in setup.exe

1. `jan_proxy.py` (pre-patched for Unicode)
2. `document_processor.py`
3. `requirements.txt`
4. `start-stack.ps1`
5. `test_image.png` (for OCR test)
6. `SETUP_REQUIREMENTS.md` (this file)
7. `install.ps1` (automated installer script)
8. `verify.ps1` (runs all tests)
