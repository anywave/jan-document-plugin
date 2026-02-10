#!/bin/bash
# AVACHATTER Installer Build Script
# Builds installers for all supported platforms

set -e

echo "======================================"
echo "  AVACHATTER Installer Builder"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're on the right branch
BRANCH=$(git branch --show-current)
echo -e "${BLUE}Current branch:${NC} $BRANCH"
echo ""

# Detect platform
PLATFORM="unknown"
case "$(uname -s)" in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="macos";;
    MINGW*|MSYS*|CYGWIN*)    PLATFORM="windows";;
esac

echo -e "${BLUE}Detected platform:${NC} $PLATFORM"
echo ""

# Build function
build_target() {
    local target=$1
    echo -e "${GREEN}Building $target installer...${NC}"
    npm run tauri build -- --target $target
    echo ""
}

# Main build logic
case $PLATFORM in
    windows)
        echo "Building Windows installers..."
        build_target "msi"
        build_target "nsis"
        echo -e "${GREEN}✓ Windows installers built!${NC}"
        echo "  - MSI: src-tauri/target/release/bundle/msi/"
        echo "  - NSIS: src-tauri/target/release/bundle/nsis/"
        ;;

    macos)
        echo "Building macOS installers..."
        build_target "dmg"
        build_target "app"
        echo -e "${GREEN}✓ macOS installers built!${NC}"
        echo "  - DMG: src-tauri/target/release/bundle/dmg/"
        echo "  - APP: src-tauri/target/release/bundle/macos/"
        ;;

    linux)
        echo "Building Linux packages..."
        build_target "deb"
        build_target "appimage"
        echo -e "${GREEN}✓ Linux packages built!${NC}"
        echo "  - DEB: src-tauri/target/release/bundle/deb/"
        echo "  - AppImage: src-tauri/target/release/bundle/appimage/"
        ;;

    *)
        echo -e "${RED}Unknown platform: $PLATFORM${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}======================================"
echo "  Build Complete!"
echo "======================================${NC}"
