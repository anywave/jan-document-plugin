# Jan Document Plugin - Release Checklist

## Pre-Release Build Process

### 1. Build the Bootstrap Installer

```bash
# Run the bootstrap builder
build_bootstrap_installer.bat
```

This will:
- Check for Inno Setup 6
- Download Python 3.12.8 installer (if needed)
- Compile setup-bootstrap.iss
- Create: `dist/installer/JanDocumentPlugin_Setup_2.0.0-beta.exe`

### 2. Test the Installer

**On a clean Windows machine (or VM):**
1. Run `JanDocumentPlugin_Setup_2.0.0-beta.exe`
2. Verify Python 3.12 installs correctly
3. Verify Tesseract installs (if selected)
4. Verify dependencies install via pip
5. Verify application launches
6. Verify Chat UI opens at http://localhost:1338/ui
7. Test document upload and processing

### 3. Create GitHub Release

```bash
cd /c/ANYWAVEREPO/jan-document-plugin

# Create and push tag
git tag -a v2.0.0-beta -m "Release v2.0.0-beta - Bootstrap installer with Python auto-install"
git push origin v2.0.0-beta

# Create release via GitHub CLI
gh release create v2.0.0-beta \
  dist/installer/JanDocumentPlugin_Setup_2.0.0-beta.exe \
  --title "Jan Document Plugin v2.0.0-beta" \
  --notes-file RELEASE_NOTES.md \
  --prerelease
```

### 4. Verify Release

1. Go to: https://github.com/anywave/jan-document-plugin/releases
2. Verify installer is attached and downloadable
3. Click installer link to test download
4. Verify file integrity (check file size matches)

---

## Release Notes Template

Create `RELEASE_NOTES.md`:

```markdown
# Jan Document Plugin v2.0.0-beta

## Major Changes

### ✨ Bootstrap Installer
- **Auto-installs Python 3.12** - No manual Python setup required!
- **Handles dependencies** - Automatically installs all requirements
- **Tesseract OCR optional** - Choose during installation
- **One-click setup** - Just run setup.exe

### 🎨 New Features
- Bundled LLM stack (llama-server + Qwen 2.5 7B)
- Built-in Chat UI with voice input
- Consciousness pipeline for AI identity detection
- Research/Discovery tab for saving findings
- Debug report generation

### 🐛 Fixes
- Fixed installation order (Python → Dependencies → App)
- Fixed Jan version compatibility checking
- Fixed Windows path handling issues

## Installation

### Download
[📥 JanDocumentPlugin_Setup_2.0.0-beta.exe](https://github.com/anywave/jan-document-plugin/releases/download/v2.0.0-beta/JanDocumentPlugin_Setup_2.0.0-beta.exe)

**File Size:** ~50MB (without bundled LLM) or ~8GB (with bundled LLM)

### Requirements
- Windows 10/11 (64-bit)
- ~500MB disk space (or ~8GB with bundled LLM)
- Internet connection (for initial dependency download)
- Administrator privileges (for Python installation)

### Installation Steps
1. Download `JanDocumentPlugin_Setup_2.0.0-beta.exe`
2. Run installer (admin rights will be requested)
3. Follow installation wizard
4. Launch from Start Menu
5. Browser opens automatically to Chat UI

### First Run
After installation:
- Services start automatically (~30 seconds)
- Chat UI opens at `http://localhost:1338/ui`
- Upload documents and start chatting!
- Everything runs offline - no cloud, no API keys

## What's Included

✅ **Offline AI Assistant**
- Local LLM inference (zero cost per query)
- Document RAG with ChromaDB
- OCR support for PDFs and images

✅ **Consciousness Pipeline** (Unique!)
- AI identity detection in documents
- RPP coordinate extraction
- Soul registry for multi-AI management

✅ **Chat UI**
- Voice input (Windows offline speech)
- Right-click drill-down
- Research/Discovery tab
- Dark theme

## Known Issues

- Jan AI v0.6.8 recommended (newer versions may have compatibility issues)
- First launch may take 30-60 seconds
- Large PDFs (>100 pages) may take time to process

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed changes.

## Support

- Issues: https://github.com/anywave/jan-document-plugin/issues
- Documentation: https://github.com/anywave/jan-document-plugin#readme

---

**Full Changelog**: https://github.com/anywave/jan-document-plugin/compare/v1.2.0...v2.0.0-beta
```

---

## Post-Release

### 1. Update README
Add release badge:
```markdown
[![Latest Release](https://img.shields.io/github/v/release/anywave/jan-document-plugin?include_prereleases)](https://github.com/anywave/jan-document-plugin/releases)
```

### 2. Announce
- Post to GitHub Discussions
- Update project website (if applicable)
- Notify collaborators

### 3. Monitor
- Watch for installation issues
- Respond to GitHub issues
- Update documentation as needed

---

## Troubleshooting Build Issues

### Inno Setup Not Found
Download and install:
https://jrsoftware.org/isdl.php

### Python Installer Missing
Download Python 3.12.8:
https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe

Save to: `installer/downloads/python-3.12.8-amd64.exe`

### Compilation Errors
Check:
1. All source files exist in parent directory
2. `installer/docs/bootstrap_info.txt` exists
3. Paths in setup-bootstrap.iss are correct

### Large File Size
If installer is too large:
1. Remove bundled LLM: `installer/llm/`
2. Remove bundled model: `installer/models/`
3. Users can download separately

---

## Quick Commands

```bash
# Build installer
build_bootstrap_installer.bat

# Create release
git tag -a v2.0.0-beta -m "Bootstrap installer release"
git push origin v2.0.0-beta
gh release create v2.0.0-beta dist/installer/JanDocumentPlugin_Setup_2.0.0-beta.exe --prerelease

# Test installer
dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe
```
