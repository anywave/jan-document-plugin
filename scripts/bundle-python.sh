#!/bin/bash
# Bundle a portable Python 3.12 distribution for MOBIUS
# This creates a self-contained Python in src-tauri/resources/python312/
# that doesn't depend on system Python installation.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUNDLE_DIR="$PROJECT_ROOT/src-tauri/resources/python312"
SYSTEM_PYTHON="/c/Users/abc/AppData/Local/Programs/Python/Python312"
VENV_SITE_PACKAGES="$PROJECT_ROOT/extensions/document-rag/venv312/Lib/site-packages"
PYTHON_SCRIPTS="$PROJECT_ROOT/extensions/document-rag/python"

echo "=== MOBIUS Python Bundler ==="
echo "System Python: $SYSTEM_PYTHON"
echo "Venv packages: $VENV_SITE_PACKAGES"
echo "Bundle target: $BUNDLE_DIR"
echo ""

# Validate sources exist
if [ ! -f "$SYSTEM_PYTHON/python.exe" ]; then
    echo "ERROR: System Python not found at $SYSTEM_PYTHON"
    exit 1
fi

if [ ! -d "$VENV_SITE_PACKAGES" ]; then
    echo "ERROR: Venv site-packages not found at $VENV_SITE_PACKAGES"
    exit 1
fi

# Clean and create bundle directory
if [ -d "$BUNDLE_DIR" ]; then
    echo "Removing existing bundle..."
    rm -rf "$BUNDLE_DIR"
fi
mkdir -p "$BUNDLE_DIR"

# 1. Copy Python runtime core
echo "[1/7] Copying Python runtime..."
cp "$SYSTEM_PYTHON/python.exe" "$BUNDLE_DIR/"
cp "$SYSTEM_PYTHON/python3.dll" "$BUNDLE_DIR/"
cp "$SYSTEM_PYTHON/python312.dll" "$BUNDLE_DIR/"
cp "$SYSTEM_PYTHON/vcruntime140.dll" "$BUNDLE_DIR/"
cp "$SYSTEM_PYTHON/vcruntime140_1.dll" "$BUNDLE_DIR/"

# 2. Copy DLLs directory (compiled extension modules)
echo "[2/7] Copying DLLs..."
cp -r "$SYSTEM_PYTHON/DLLs" "$BUNDLE_DIR/DLLs"

# 3. Copy standard library (trimmed)
echo "[3/7] Copying standard library (trimmed)..."
mkdir -p "$BUNDLE_DIR/Lib"

# Copy everything except large unnecessary dirs
cd "$SYSTEM_PYTHON/Lib"
for item in *; do
    case "$item" in
        test|tests|site-packages|idlelib|tkinter|turtledemo|lib2to3|__pycache__)
            echo "  Skipping: $item"
            ;;
        *)
            cp -r "$item" "$BUNDLE_DIR/Lib/$item"
            ;;
    esac
done
cd "$PROJECT_ROOT"

# 4. Copy site-packages from venv (the ML packages)
echo "[4/7] Copying site-packages from venv..."
mkdir -p "$BUNDLE_DIR/Lib/site-packages"
cp -r "$VENV_SITE_PACKAGES"/* "$BUNDLE_DIR/Lib/site-packages/"

# Remove unnecessary files from site-packages to trim size
echo "  Trimming unnecessary files..."
find "$BUNDLE_DIR/Lib/site-packages" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUNDLE_DIR/Lib/site-packages" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$BUNDLE_DIR/Lib/site-packages" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
# NOTE: Do NOT remove .dist-info directories — they contain entry_points metadata
# required by packages like opentelemetry, chromadb, etc.
# NOTE: pip and setuptools are kept — needed by ensure_python_deps() runtime safety net

# 5. Copy document processing scripts
echo "[5/7] Copying document processing scripts..."
mkdir -p "$BUNDLE_DIR/scripts"
cp "$PYTHON_SCRIPTS/document_processor.py" "$BUNDLE_DIR/scripts/"
cp "$PYTHON_SCRIPTS/docx_processor.py" "$BUNDLE_DIR/scripts/"
cp "$PYTHON_SCRIPTS/embedder.py" "$BUNDLE_DIR/scripts/"
cp "$PYTHON_SCRIPTS/image_processor.py" "$BUNDLE_DIR/scripts/"
cp "$PYTHON_SCRIPTS/pdf_processor.py" "$BUNDLE_DIR/scripts/"
cp "$PYTHON_SCRIPTS/vector_store.py" "$BUNDLE_DIR/scripts/"
cp "$PYTHON_SCRIPTS/requirements.txt" "$BUNDLE_DIR/scripts/"

# 6. Copy TTS and voice relay scripts
echo "[6/7] Copying TTS and voice relay scripts..."
cp "$PYTHON_SCRIPTS/tts_engine.py" "$BUNDLE_DIR/scripts/"
cp "$PYTHON_SCRIPTS/voice_relay.py" "$BUNDLE_DIR/scripts/"

# 7. Install TTS/relay pip dependencies into bundle's site-packages
echo "[7/7] Installing TTS/relay dependencies..."
SYSTEM_PYTHON_EXE="$SYSTEM_PYTHON/python.exe"
"$SYSTEM_PYTHON_EXE" -m pip install \
    --target "$BUNDLE_DIR/Lib/site-packages" \
    --no-input --no-compile --quiet \
    pyttsx3 websockets "qrcode[pil]" 2>&1 | while read -r line; do
    echo "  pip: $line"
done
echo "  Verifying installed packages..."
for pkg in pyttsx3 websockets qrcode; do
    if [ -d "$BUNDLE_DIR/Lib/site-packages/$pkg" ]; then
        echo "  ✓ $pkg"
    else
        echo "  ✗ $pkg — MISSING (bundle may be incomplete)"
    fi
done

# Create python312._pth to configure import paths
# This tells the embedded Python where to find modules
cat > "$BUNDLE_DIR/python312._pth" << 'EOF'
DLLs
Lib
Lib/site-packages
scripts
.
import site
EOF

echo ""
echo "=== Bundle complete ==="
BUNDLE_SIZE=$(du -sh "$BUNDLE_DIR" | cut -f1)
echo "Bundle size: $BUNDLE_SIZE"
echo "Location: $BUNDLE_DIR"
echo ""
echo "Contents:"
ls -la "$BUNDLE_DIR/"
