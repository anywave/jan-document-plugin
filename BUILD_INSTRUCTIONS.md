# MOBIUS Build Instructions

## Prerequisites

### All Platforms
- **Node.js** 18+ and npm
- **Rust** 1.70+ (install from https://rustup.rs/)
- **Git**

### Windows
- **Visual Studio 2022** with C++ build tools
- **Windows SDK**
- Optional: WiX Toolset (for MSI builds)
- Optional: NSIS (for .exe installer)

### macOS
- **Xcode** 13+ and Command Line Tools
- Optional: Apple Developer account (for code signing)

### Linux (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install libwebkit2gtk-4.1-dev \
    build-essential \
    curl \
    wget \
    file \
    libxdo-dev \
    libssl-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev
```

---

## Quick Start

### 1. Install Dependencies
```bash
# Install npm packages
npm install

# Or using yarn
yarn install
```

### 2. Development Build
```bash
# Run in development mode
npm run dev:tauri

# Or using yarn
yarn dev:tauri
```

### 3. Production Build

#### Windows
```bash
# Using batch script (recommended)
build-installer.bat

# Or manually
npm run build:tauri:win32
```

#### macOS
```bash
# Using shell script
./build-installer.sh

# Or manually
npm run build:tauri:darwin
```

#### Linux
```bash
# Using shell script
./build-installer.sh

# Or manually
npm run build:tauri:linux
```

---

## Build Outputs

### Windows
- **MSI**: `src-tauri/target/release/bundle/msi/MOBIUS_0.7.0_x64_en-US.msi`
- **NSIS**: `src-tauri/target/release/bundle/nsis/MOBIUS_0.7.0_x64-setup.exe`

### macOS
- **DMG**: `src-tauri/target/release/bundle/dmg/MOBIUS_0.7.0_universal.dmg`
- **APP**: `src-tauri/target/release/bundle/macos/MOBIUS.app`

### Linux
- **DEB**: `src-tauri/target/release/bundle/deb/mobius_0.7.0_amd64.deb`
- **AppImage**: `src-tauri/target/release/bundle/appimage/mobius_0.7.0_amd64.AppImage`

---

## Build Configuration

### tauri.conf.json
Main configuration file for Tauri builds:
- **productName**: MOBIUS
- **version**: 0.7.0
- **identifier**: com.mobius.app
- **bundle targets**: msi, nsis, dmg, app, deb, appimage

### Icons
Icons are generated from `src-tauri/icons/icon.png`:
```bash
npm run build:icon
```

This creates:
- `icon.ico` (Windows)
- `icon.icns` (macOS)
- Various PNG sizes (Linux)

---

## Troubleshooting

### Windows

**Error: "WebView2 not found"**
- Install WebView2 Runtime: https://developer.microsoft.com/microsoft-edge/webview2/

**Error: "WiX Toolset not found"**
- Install WiX v3: https://wixtoolset.org/releases/
- Add to PATH: `C:\Program Files (x86)\WiX Toolset v3.xx\bin`

**Error: "NSIS not found"**
- Install NSIS: https://nsis.sourceforge.io/Download
- Add to PATH: `C:\Program Files (x86)\NSIS`

### macOS

**Error: "Code signing failed"**
- Builds will work unsigned for local testing
- For distribution, obtain Apple Developer ID certificate
- Configure in tauri.conf.json under `bundle.macOS`

**Error: "No such file or directory"**
- Run `chmod +x build-installer.sh` first
- Ensure Xcode Command Line Tools are installed: `xcode-select --install`

### Linux

**Error: "libwebkit2gtk not found"**
- Install WebKit dependencies (see Prerequisites above)

**Error: "AppImage build failed"**
- Ensure build-utils are executable: `chmod +x src-tauri/build-utils/*.sh`

---

## Manual Build Steps

### 1. Build Web App
```bash
npm run build:web
```

### 2. Build Tauri App
```bash
npm run tauri build
```

### 3. Build Specific Target
```bash
# Windows MSI
npm run tauri build -- --target msi

# Windows NSIS
npm run tauri build -- --target nsis

# macOS DMG
npm run tauri build -- --target dmg

# macOS Universal
npm run tauri build -- --target universal-apple-darwin

# Linux DEB
npm run tauri build -- --target deb

# Linux AppImage
npm run tauri build -- --target appimage
```

---

## Clean Build

To perform a clean build:

```bash
# Clean build artifacts
npm run clean  # or yarn clean

# Or manually
rm -rf src-tauri/target
rm -rf web-app/dist
rm -rf node_modules

# Reinstall and rebuild
npm install
npm run build
```

---

## Code Signing (Optional)

### Windows
1. Obtain Authenticode certificate (.pfx file)
2. Set environment variables:
   ```cmd
   set TAURI_SIGNING_PRIVATE_KEY=path/to/cert.pfx
   set TAURI_SIGNING_PRIVATE_KEY_PASSWORD=your_password
   ```
3. Build normally - installer will be signed

### macOS
1. Obtain Apple Developer ID certificate
2. Configure in tauri.conf.json:
   ```json
   "macOS": {
     "signing": {
       "identity": "Developer ID Application: Your Name (TEAM_ID)"
     }
   }
   ```
3. Build normally - app will be signed

### Linux
- Code signing not typically used for Linux packages

---

## Distribution

### GitHub Releases
1. Create a new release tag
2. Upload installers as release assets
3. Users download directly

### Auto-Updater (Future)
Currently disabled. To enable:
1. Configure `updater` in tauri.conf.json
2. Set up update server
3. Enable `createUpdaterArtifacts: true`

---

## Version Management

Update version in:
1. `src-tauri/tauri.conf.json` - `version` field
2. `package.json` - `version` field
3. `src-tauri/Cargo.toml` - `version` field

Or use version bump script (coming soon).

---

## Development Tips

- Use `npm run dev:tauri` for hot-reload during development
- Use `npm run build:icon` to regenerate icons after changes
- Test installers on clean VMs before distribution
- Check installer sizes (should be < 100MB)

---

## Support

For build issues:
- Check Tauri docs: https://tauri.app
- MOBIUS issues: https://github.com/anywave/mobius/issues

---

**Last Updated**: February 10, 2026
**MOBIUS Version**: 0.7.0
