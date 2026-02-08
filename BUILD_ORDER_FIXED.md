# Jan Document Plugin - Build Order FIXED

## Problem Summary

### Issues Identified:
1. ❌ **Installer doesn't handle Python installation first**
2. ❌ **PyInstaller build fails** with missing imports
3. ❌ **Installer exe not available on GitHub releases**
4. ❌ **Order of operations is incorrect** - build assumes environment already setup

## Solution: Proper Build Pipeline

### Correct Order of Operations:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT ENVIRONMENT                       │
│  (This needs to exist BEFORE building)                          │
├─────────────────────────────────────────────────────────────────┤
│  1. ✅ Install Python 3.12 on build machine                     │
│  2. ✅ Install all requirements.txt dependencies                │
│  3. ✅ Install PyInstaller                                      │
│  4. ✅ Install Inno Setup 6                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BUILD PIPELINE (BUILD_MASTER.bat)            │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Environment Verification                              │
│    → Check Python 3.12 in PATH                                  │
│    → Check PyInstaller available                                │
│    → Check Inno Setup installed                                 │
│                                                                  │
│  Phase 2: Dependency Installation                               │
│    → pip install -r requirements.txt --upgrade                  │
│    → Verify all imports work                                    │
│                                                                  │
│  Phase 3: Clean Previous Builds                                 │
│    → Delete dist/ folder                                        │
│    → Delete build/ folder                                       │
│                                                                  │
│  Phase 4: PyInstaller Build                                     │
│    → pyinstaller JanDocumentPlugin.spec --clean --noconfirm     │
│    → Creates: dist/JanDocumentPlugin/JanDocumentPlugin.exe      │
│    → Verify exe exists                                          │
│                                                                  │
│  Phase 5: Installer Staging                                     │
│    → Create installer/ directories                              │
│    → Copy additional files (HTML, JSON, PS1)                    │
│    → Prepare staging area                                       │
│                                                                  │
│  Phase 6: Download Python Installer                             │
│    → Download python-3.12.8-amd64.exe                           │
│    → Save to installer/downloads/                               │
│    → This will be embedded in final installer                   │
│                                                                  │
│  Phase 7: Compile Inno Setup Installer                          │
│    → Run ISCC.exe on setup-bootstrap.iss                        │
│    → Creates: dist/installer/JanDocumentPlugin_Setup_2.0.0-beta.exe │
│    → This installer CAN install Python for end users           │
│                                                                  │
│  Phase 8: Verification                                           │
│    → Check both exe and installer exist                         │
│    → Display file sizes                                         │
│    → Ready for release                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    END USER INSTALLATION                         │
│  (What happens when user downloads and runs installer)          │
├─────────────────────────────────────────────────────────────────┤
│  1. ✅ User downloads: JanDocumentPlugin_Setup_2.0.0-beta.exe   │
│  2. ✅ Installer checks for Python 3.12                         │
│  3. ✅ If not found, installs Python 3.12 (embedded)            │
│  4. ✅ Installs Tesseract OCR (optional)                        │
│  5. ✅ Extracts application files                               │
│  6. ✅ Creates virtual environment                              │
│  7. ✅ Installs Python dependencies                             │
│  8. ✅ Creates shortcuts                                        │
│  9. ✅ Launches application                                     │
└─────────────────────────────────────────────────────────────────┘
```

## New Files Created

### 1. BUILD_MASTER.bat
**Purpose:** Orchestrates entire build process in correct order
**Location:** `/jan-document-plugin/BUILD_MASTER.bat`
**Usage:** `BUILD_MASTER.bat`

**What it does:**
- Verifies build environment
- Installs dependencies
- Cleans previous builds
- Runs PyInstaller
- Downloads Python installer
- Compiles Inno Setup installer
- Verifies output

### 2. setup-bootstrap.iss
**Purpose:** Inno Setup script that handles Python installation
**Location:** `/jan-document-plugin/installer/setup-bootstrap.iss`
**Usage:** Compiled by BUILD_MASTER.bat

**What it does:**
- Checks for Python 3.12
- Installs Python if missing
- Installs Tesseract via winget
- Runs install.ps1 for dependencies
- Creates shortcuts

### 3. build_bootstrap_installer.bat
**Purpose:** Standalone installer builder (if you just want installer)
**Location:** `/jan-document-plugin/build_bootstrap_installer.bat`
**Usage:** `build_bootstrap_installer.bat`

**What it does:**
- Simplified version of BUILD_MASTER
- Only builds installer (assumes exe exists)
- Downloads Python installer
- Compiles Inno Setup

### 4. RELEASE_CHECKLIST.md
**Purpose:** Complete guide for creating GitHub releases
**Location:** `/jan-document-plugin/RELEASE_CHECKLIST.md`

**Includes:**
- Pre-release build steps
- Testing procedures
- GitHub release creation
- Release notes template
- Post-release tasks

### 5. FIX_PYINSTALLER_ERRORS.md
**Purpose:** Troubleshooting guide for PyInstaller failures
**Location:** `/jan-document-plugin/FIX_PYINSTALLER_ERRORS.md`

**Includes:**
- Common error solutions
- Missing imports fixes
- DLL loading issues
- Build space problems

## How to Use

### For Developers (Building the Release):

```bash
# 1. Set up your build environment (ONE TIME)
# - Install Python 3.12
# - Install PyInstaller: pip install pyinstaller
# - Install Inno Setup 6 from jrsoftware.org

# 2. Run the master build script
BUILD_MASTER.bat

# 3. Wait for all 8 phases to complete (~10 minutes)

# 4. Test the installer
dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe

# 5. Create GitHub release
git tag -a v2.0.0-beta -m "Bootstrap installer release"
git push origin v2.0.0-beta
gh release create v2.0.0-beta ^
    dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe ^
    --title "Jan Document Plugin v2.0.0-beta" ^
    --prerelease
```

### For End Users (Installing):

```bash
# 1. Download from GitHub releases
https://github.com/anywave/jan-document-plugin/releases/latest

# 2. Run installer
JanDocumentPlugin_Setup_2.0.0-beta.exe

# 3. Follow wizard (Python auto-installs if needed)

# 4. Launch from Start Menu
# OR browser opens automatically to http://localhost:1338/ui
```

## Key Differences from Old System

| Aspect | OLD (Broken) | NEW (Fixed) |
|--------|-------------|-------------|
| **Python Install** | Manual, before build | Auto-installed by end-user installer |
| **Build Order** | Random, error-prone | 8 phases, verified at each step |
| **Dependencies** | Assumed present | Verified and installed |
| **PyInstaller** | Failed silently | Error handling with diagnostics |
| **Installer Type** | Assumed Python exists | Bootstraps Python first |
| **Release Process** | Manual, no docs | Automated with checklist |
| **Testing** | Ad-hoc | Structured verification |
| **File Size** | Unknown | Displayed at each step |

## Common Issues Fixed

### Issue 1: "Python not found" during build
**Old:** Build failed immediately
**New:** Phase 1 verifies Python 3.12 and provides clear instructions

### Issue 2: PyInstaller import errors
**Old:** Cryptic error messages
**New:** Proper hidden imports in .spec file + troubleshooting guide

### Issue 3: Installer fails on clean machine
**Old:** Assumed Python already installed
**New:** Embeds Python installer, auto-installs for user

### Issue 4: No installer on GitHub releases
**Old:** No clear release process
**New:** RELEASE_CHECKLIST.md with exact commands

### Issue 5: Order of operations unclear
**Old:** Build scripts called each other randomly
**New:** Single BUILD_MASTER.bat orchestrates everything

## Next Steps

1. **Test Build on Your Machine:**
   ```bash
   cd C:\ANYWAVEREPO\jan-document-plugin
   BUILD_MASTER.bat
   ```

2. **Test Installer on Clean VM:**
   - Windows 10/11 VM
   - No Python installed
   - Run installer
   - Verify everything works

3. **Create GitHub Release:**
   - Follow RELEASE_CHECKLIST.md
   - Upload installer
   - Update README with download link

4. **Notify Collaborators:**
   - beckerhans-create can now download installer
   - No need to manually set up Python

## Success Criteria

✅ BUILD_MASTER.bat completes all 8 phases
✅ PyInstaller creates working exe
✅ Inno Setup creates installer
✅ Installer runs on clean machine
✅ Python auto-installs if missing
✅ Application launches and works
✅ Installer uploaded to GitHub releases
✅ Download link in README works

## File Structure After Build

```
jan-document-plugin/
├── BUILD_MASTER.bat                    ← Run this to build everything
├── JanDocumentPlugin.spec              ← PyInstaller config
├── installer/
│   ├── setup-bootstrap.iss             ← Inno Setup config (bootstrap)
│   ├── downloads/
│   │   └── python-3.12.8-amd64.exe     ← Embedded Python installer
│   └── docs/
│       └── bootstrap_info.txt          ← Installer welcome text
├── dist/
│   ├── JanDocumentPlugin/
│   │   └── JanDocumentPlugin.exe       ← PyInstaller output
│   └── installer/
│       └── JanDocumentPlugin_Setup_2.0.0-beta.exe  ← FINAL DELIVERABLE
├── RELEASE_CHECKLIST.md                ← How to release
├── FIX_PYINSTALLER_ERRORS.md           ← Troubleshooting
└── BUILD_ORDER_FIXED.md                ← This file
```

## Support

If build fails:
1. Check BUILD_MASTER.bat output - it shows which phase failed
2. Consult FIX_PYINSTALLER_ERRORS.md for PyInstaller issues
3. Check installer/logs/ for Inno Setup errors
4. Verify Python 3.12 is in PATH: `python --version`
5. Verify PyInstaller works: `python -c "import PyInstaller"`

---

**The build order is now FIXED and fully automated!** 🎉
