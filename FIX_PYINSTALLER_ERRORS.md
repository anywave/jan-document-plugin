# Fixing PyInstaller Build Errors

## Common Issues and Solutions

### 1. Import Errors

**Error:** `ModuleNotFoundError` during build

**Fix:** Add hidden imports to `JanDocumentPlugin.spec`:

```python
hiddenimports=[
    'fastapi',
    'uvicorn',
    'chromadb',
    'sentence_transformers',
    'PIL',
    'pdf2image',
    'pytesseract',
    'speech_recognition',
    'pyaudio',
    # Consciousness pipeline
    'consciousness_pipeline',
    'soul_registry',
    'seed_transit',
    'fractal_analyzer',
    'resonance_db',
    # Other modules
    'resource_monitor',
    'document_processor',
    'ocr_processor',
    'batch_processor',
],
```

### 2. Missing Data Files

**Error:** Files not found at runtime

**Fix:** Add to `datas` in spec file:

```python
datas=[
    ('chat_ui.html', '.'),
    ('config.env.example', '.'),
    ('soul_registry_state.json', '.'),
    ('rollback_jan.ps1', '.'),
    ('calibration', 'calibration'),
],
```

### 3. DLL Loading Errors

**Error:** `ImportError: DLL load failed`

**Fix:** Add to spec file:

```python
binaries=[],
```

And ensure Visual C++ Redistributable is installed.

### 4. Build Space Issues

**Error:** `No space left on device`

**Solution:**
1. Clean previous builds: `rmdir /s /q dist build`
2. Ensure at least 2GB free space
3. Close other applications

### 5. Hook Errors

**Error:** PyInstaller hooks failing

**Fix:** Update PyInstaller:
```bash
pip install --upgrade pyinstaller
```

### 6. Console Window Issues

**Problem:** Console window stays open

**Fix:** Change in spec file:
```python
exe = EXE(
    # ...
    console=False,  # Hide console for GUI app
    # Or
    console=True,   # Show console for debugging
)
```

## Complete Fixed .spec File

See `JanDocumentPlugin-fixed.spec` for a working configuration.

## Testing Build

```bash
# Clean build
rmdir /s /q dist build

# Build with verbose output
pyinstaller JanDocumentPlugin.spec --clean --noconfirm --log-level DEBUG

# Check for errors
# Look for lines starting with "WARNING:" or "ERROR:"
```

## Quick Fixes Checklist

- [ ] Python 3.12 installed and in PATH
- [ ] All requirements.txt dependencies installed
- [ ] PyInstaller updated to latest version
- [ ] At least 2GB free disk space
- [ ] No antivirus blocking build process
- [ ] All source .py files present
- [ ] Hidden imports added for all modules
- [ ] Data files specified in datas list
- [ ] Previous dist/build folders deleted

## Emergency Fallback

If PyInstaller continues to fail, use source distribution instead:

```bash
# Just zip the source files
7z a dist\JanDocumentPlugin_Source_2.0.0-beta.zip *.py *.html *.ps1 *.bat requirements.txt README.md LICENSE

# Users run directly:
# python jan_proxy.py --port 1338
```
