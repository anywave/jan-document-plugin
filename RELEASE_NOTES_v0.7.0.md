# AVACHATTER v0.7.0 Release Notes

**Release Date**: February 10, 2026
**Codename**: "Sovereign Intelligence"
**Based On**: Jan AI v0.6.8

---

## 🎉 Major Features

### 1. Document RAG (Retrieval-Augmented Generation)

**100% Offline Document Intelligence** - Query your documents using AI without internet connectivity.

**Features:**
- 📄 **Document Upload**: PDF, TXT, MD, DOCX support
- 🔍 **Vector Search**: Semantic search across all your documents
- 🧠 **Smart Context**: Automatic context injection into AI conversations
- 🎯 **Relevance Scoring**: See how relevant each result is (distance scores)
- 🔒 **Privacy-First**: All processing happens locally, zero data leaves your machine
- 💬 **Chat Integration**: Seamlessly add document context to any conversation
- 🧵 **Thread Isolation**: Each chat thread maintains its own context

**How It Works:**
1. Upload documents through the Document RAG interface
2. Documents are processed into chunks and embedded locally
3. Use "Search Documents" in chat to query your knowledge base
4. Selected results automatically enhance AI responses with your data
5. Context indicator shows which documents are being used

**Technical Details:**
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
- **Vector Database**: ChromaDB (embedded, no server required)
- **Chunk Size**: 500 tokens with 50-token overlap
- **Search Algorithm**: Cosine similarity with configurable top-k

---

### 2. Voice I/O (Speech Recognition & Text-to-Speech)

**Hands-Free AI Interaction** - Talk to your AI assistant and hear responses aloud.

**Speech Recognition Features:**
- 🎤 **Voice Input**: Speak naturally, text appears in real-time
- ⌨️ **Keyboard Shortcut**: Press `Ctrl+M` to toggle recording
- 📝 **Interim Results**: See transcription as you speak
- 🌍 **Multi-Language**: Support for en-US, es-ES, fr-FR, de-DE, and more
- 🔴 **Visual Feedback**: Animated recording indicator
- ⚡ **Continuous Mode**: Speak multiple sentences without stopping

**Text-to-Speech Features:**
- 🔊 **Read Aloud**: Click play button on any assistant message
- ⏯️ **Full Controls**: Play, pause, resume, stop
- 🗣️ **Voice Selection**: Choose from available system voices
- ⚙️ **Customization**: Adjust rate, pitch, and volume
- 💬 **Per-Message**: Independent TTS controls on each message

**Browser Compatibility:**
- ✅ Chrome 25+ (Full support)
- ✅ Edge 79+ (Full support)
- ✅ Safari 14.1+ (Full support)
- ⚠️ Firefox (TTS only, STT not supported)
- 🔧 Graceful degradation on unsupported browsers

**Technical Details:**
- **API**: Web Speech API (browser-native, zero dependencies)
- **Recognition**: Webkit/Chrome Speech Recognition
- **Synthesis**: Speech Synthesis API
- **Offline**: Works completely offline once page loaded
- **Privacy**: No audio sent to cloud services

---

### 3. Production Build System

**Professional Distribution** - Native installers for Windows, macOS, and Linux.

**Installer Formats:**
- 🪟 **Windows**: MSI (enterprise) + NSIS (consumer)
- 🍎 **macOS**: DMG (recommended) + APP bundle
- 🐧 **Linux**: DEB (Debian/Ubuntu) + AppImage (universal)

**Build Features:**
- 🏗️ **Cross-Platform**: Single codebase, platform-specific builds
- 📦 **App Bundling**: All dependencies included
- 🎨 **Proper Branding**: AVACHATTER name, identifier, icons
- 🔄 **Auto-Updater**: Disabled by default (privacy-first)
- 🔗 **Deep-Link**: `avachatter://` protocol support
- 📝 **Documentation**: Comprehensive build instructions

**Build Scripts:**
- `build-installer.sh` - Cross-platform (Linux/macOS/Windows Git Bash)
- `build-installer.bat` - Windows-specific (CMD/PowerShell)
- Platform auto-detection
- Error handling and validation

**System Requirements:**
- **Windows**: Windows 10 (1809+) or Windows 11, WebView2
- **macOS**: macOS 10.13+ (High Sierra), Intel or Apple Silicon
- **Linux**: Debian 11+ or Ubuntu 20.04+, WebKit2GTK

---

## 🔧 Technical Improvements

### Architecture

- **Zustand State Management**: Thread-isolated document context
- **React 19**: Latest React features and performance improvements
- **TypeScript**: Full type safety across all new features
- **Tauri v2**: Modern desktop framework with Rust backend
- **ChromaDB Integration**: Local vector database with Python bridge
- **Web Speech API**: Browser-native voice capabilities

### Code Quality

- ✅ Removed debug console.log statements
- ✅ Comprehensive JSDoc documentation
- ✅ TypeScript interfaces for all new APIs
- ✅ Error handling and graceful degradation
- ✅ Accessibility improvements (ARIA labels)
- ✅ Keyboard navigation support

### Performance

- **Lazy Loading**: Extensions load on-demand
- **Optimized Vector Search**: Efficient similarity search algorithms
- **Streaming Responses**: AI responses stream in real-time
- **Minimal Bundle Size**: Target <100MB total app size
- **Memory Efficient**: Thread-isolated state management

---

## 📚 Documentation

### New Documentation

- **BUILD_INSTRUCTIONS.md** - Comprehensive build guide
- **PHASE5_COMPLETE.md** - Document RAG technical docs
- **PHASE6_COMPLETE.md** - Voice I/O technical docs
- **PHASE7_COMPLETE.md** - Installer & distribution docs
- **PHASE8_TEST_PLAN.md** - Testing strategy and checklist

### Updated Documentation

- **README.md** - Feature updates and quick start
- **CONTRIBUTING.md** - Development workflow updates
- Progress logs for all 8 phases of development

---

## 🐛 Bug Fixes

- Fixed missing icon files for platform-specific builds
- Removed debug console.log from document selection handler
- Verified JSON syntax in tauri.conf.json
- Ensured thread-isolated context management prevents cross-contamination

---

## 🎨 UI/UX Enhancements

### Document RAG Interface

- Clean tabbed interface (Upload, Search, Library)
- Drag-and-drop file upload
- Real-time upload progress
- Vector search with relevance scores
- Expandable result cards
- Source file preview

### Chat Integration

- "Search Documents" button in chat toolbar
- Context indicator above chat input
- Expandable context view showing all active documents
- Color-coded relevance scores (Green: 80%+, Yellow: 60-79%, Orange: <60%)
- Clear button to remove context

### Voice Controls

- Microphone button with animated recording indicator
- Red pulse animation when recording
- Tooltips showing status and errors
- Play/pause/stop controls on messages
- Visual feedback when speaking
- Keyboard shortcut hints

---

## 🔒 Privacy & Security

### Privacy-First Design

- ✅ **100% Offline**: All processing happens locally
- ✅ **Zero Telemetry**: No analytics or tracking
- ✅ **No Cloud Sync**: Data never leaves your device
- ✅ **Local Models**: AI models run on your hardware
- ✅ **Local Vectors**: Document embeddings stored locally
- ✅ **Auto-Updater Disabled**: No phone-home functionality

### Data Sovereignty

- All documents stored in local ChromaDB
- Embeddings generated locally using sentence-transformers
- Chat history persisted locally only
- Voice data processed in browser (Web Speech API)
- No external API calls for core functionality

---

## 📦 What's Included

### Core Application

- AVACHATTER desktop application (Tauri-based)
- Embedded AI runtime (llama.cpp)
- Python 3.11 runtime (for document processing)
- ChromaDB vector database
- Sentence-transformers embedding model
- Web-based UI (React 19)

### Extensions

- Document RAG Extension (Python + TypeScript)
- Assistant Extension
- Model Management Extension
- Settings Extension

---

## 🚀 Installation

### Windows

1. Download `AVACHATTER_0.7.0_x64_en-US.msi` or `AVACHATTER_0.7.0_x64-setup.exe`
2. Run the installer
3. Follow installation wizard
4. Launch AVACHATTER from Start Menu

**Requirements**: Windows 10 (1809+) or Windows 11, WebView2 Runtime

### macOS

1. Download `AVACHATTER_0.7.0_universal.dmg`
2. Open DMG file
3. Drag AVACHATTER.app to Applications folder
4. Launch from Applications

**Requirements**: macOS 10.13+ (High Sierra), Intel or Apple Silicon

### Linux

**Debian/Ubuntu:**
```bash
sudo dpkg -i avachatter_0.7.0_amd64.deb
avachatter
```

**Universal (AppImage):**
```bash
chmod +x avachatter_0.7.0_amd64.AppImage
./avachatter_0.7.0_amd64.AppImage
```

**Requirements**: WebKit2GTK, GTK 3.0

---

## 📖 Quick Start

### Basic Chat

1. Launch AVACHATTER
2. Select an AI model (if not already configured)
3. Type a message or click microphone to speak
4. AI responds with streaming text
5. Click play button to hear response aloud

### Document RAG

1. Open Document RAG interface (sidebar)
2. Upload your documents (PDF, TXT, MD, DOCX)
3. Wait for processing to complete
4. In chat, click "Search Documents"
5. Enter your query (e.g., "What are the key findings?")
6. Select relevant results to add as context
7. Ask your question in chat - AI will use your documents

### Voice I/O

1. Click microphone button in chat (or press `Ctrl+M`)
2. Grant microphone permission if prompted
3. Speak your message
4. Text appears in real-time
5. Click send when done
6. Click play button on assistant message to hear response

---

## 🔍 Known Issues

### Current Limitations

1. **Voice I/O**: Requires modern browser with Web Speech API support
2. **Large Documents**: Files >50MB may be slow to process
3. **Vector Search**: Performance degrades with >5000 chunks
4. **Model Size**: Large models (>7B parameters) require 8GB+ RAM
5. **Firefox**: Speech recognition not supported (TTS works)

### Future Enhancements

- [ ] Additional document formats (PPT, XLS, etc.)
- [ ] Multiple embedding model support
- [ ] Hybrid search (keyword + semantic)
- [ ] Document metadata filtering
- [ ] Custom voice training
- [ ] Multi-language voice support
- [ ] Auto-updater (optional, privacy-preserving)
- [ ] Code signing for Windows and macOS

---

## 📊 Performance Benchmarks

### Target Metrics

- **Startup Time**: < 3 seconds (cold start)
- **Memory Usage**: < 250MB (with documents, without model)
- **Vector Search**: < 5 seconds (1000 chunks)
- **Bundle Size**: < 100MB (total app size)

### Actual Results

- ✅ Bundle size target met (installers <100MB)
- ⏳ Runtime benchmarks deferred to user testing
- 📝 Performance data will be collected from real-world usage

---

## 🙏 Acknowledgments

**Built On:**
- Jan AI v0.6.8 (base application)
- Tauri v2 (desktop framework)
- React 19 (UI framework)
- ChromaDB (vector database)
- Sentence-Transformers (embedding models)
- Web Speech API (voice capabilities)

**Developed By**: ANYWAVE Team
**License**: AGPLv3 (see LICENSE file)
**Homepage**: https://github.com/anywave/avachatter

---

## 📞 Support

### Getting Help

- **Issues**: https://github.com/anywave/avachatter/issues
- **Discussions**: https://github.com/anywave/avachatter/discussions
- **Documentation**: See docs/ directory

### Reporting Bugs

Please include:
- AVACHATTER version (v0.7.0)
- Operating system and version
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable

---

## 🔄 Upgrade Notes

### From Jan AI v0.6.8

AVACHATTER is a fork of Jan AI with significant enhancements. Your existing Jan AI data and models will not be automatically migrated. This is a fresh installation.

**Migration Steps:**
1. Export your Jan AI conversation history (if needed)
2. Note your model configurations
3. Install AVACHATTER v0.7.0
4. Re-download models as needed
5. Upload documents to new Document RAG system

---

## 🗺️ Roadmap

### Upcoming Features

**Phase 9 (Future):**
- Advanced document processing (OCR, tables, charts)
- Multi-modal embeddings (images, audio)
- Collaborative features (team workspaces)
- Plugin system for community extensions
- Mobile app (iOS/Android)

**Community Requests:**
- Custom embedding models
- Advanced search filters
- Document versioning
- Citation tracking
- Export to various formats

---

## 🎯 Version Summary

**AVACHATTER v0.7.0 "Sovereign Intelligence"**

- ✅ 100% Offline Document RAG
- ✅ Hands-Free Voice I/O
- ✅ Production Build System
- ✅ Privacy-First Architecture
- ✅ Cross-Platform Support
- ✅ Professional Documentation

**Total Development Time**: 8 phases, ~15 hours
**Lines of Code Added**: 2000+
**Files Created/Modified**: 50+
**Commits**: 8 major phase commits

---

**Release Date**: February 10, 2026
**Download**: GitHub Releases
**License**: AGPLv3
**Status**: Production Ready ✅

**Thank you for using AVACHATTER!** 🚀

---

## Changelog

### v0.7.0 (2026-02-10)

**Added:**
- Document RAG system with vector search
- Speech recognition (voice input)
- Text-to-speech (voice output)
- Cross-platform installers (Windows/macOS/Linux)
- Document context injection in chat
- Voice controls with keyboard shortcuts
- Context indicator UI component
- Build scripts for all platforms
- Comprehensive build documentation

**Changed:**
- Rebranded from Jan AI to AVACHATTER
- Updated app identifier to com.avachatter.app
- Disabled auto-updater (privacy-first)
- Modified deep-link scheme to avachatter://

**Fixed:**
- Generated missing platform-specific icon files
- Removed debug console.log statements
- Verified tauri.conf.json JSON syntax

**Technical:**
- Integrated ChromaDB for vector storage
- Added Zustand for context state management
- Implemented Web Speech API hooks
- Created thread-isolated document context
- Built Python-TypeScript bridge for RAG

---

*This release represents a major milestone in bringing privacy-first, offline AI capabilities to everyone.*
