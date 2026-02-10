# AVACHATTER - 100% Offline AI Assistant

<p align="center">
  <strong>Privacy-First • Document Intelligence • Voice I/O • Zero Cloud</strong>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-0.7.0-blue"/>
  <img alt="License" src="https://img.shields.io/badge/license-AGPLv3-green"/>
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey"/>
</p>

---

## 🚀 What is AVACHATTER?

AVACHATTER is a **100% offline AI assistant** with advanced document intelligence and voice capabilities. Fork of Jan AI v0.6.8 with major enhancements for privacy, document RAG, and voice interaction.

### Key Features

🔒 **100% Offline** - No internet required, zero data collection
📚 **Document RAG** - Query your PDFs, documents with AI (semantic search)
🎤 **Voice Input** - Speak naturally, text appears in real-time (STT)
🔊 **Voice Output** - Hear AI responses aloud with natural voices (TTS)
🧠 **Local AI Models** - Run LLMs on your hardware (llama.cpp)
🔐 **Privacy-First** - Your data never leaves your device

---

## 📦 Installation

### Quick Install

Download the installer for your platform from [GitHub Releases](https://github.com/anywave/avachatter/releases/latest):

| Platform | Installer | Size |
|----------|-----------|------|
| **Windows 10/11** | AVACHATTER_0.7.0_x64.msi | ~80MB |
| **Windows (Alt)** | AVACHATTER_0.7.0_setup.exe | ~80MB |
| **macOS 10.13+** | AVACHATTER_0.7.0_universal.dmg | ~85MB |
| **Linux (Debian/Ubuntu)** | avachatter_0.7.0_amd64.deb | ~75MB |
| **Linux (Universal)** | avachatter_0.7.0_amd64.AppImage | ~80MB |

### System Requirements

**Windows:**
- Windows 10 (build 1809+) or Windows 11
- WebView2 Runtime (auto-installed)
- 4GB RAM minimum (8GB+ recommended for large models)

**macOS:**
- macOS 10.13 (High Sierra) or later
- Intel or Apple Silicon (M1/M2/M3)
- 4GB RAM minimum (8GB+ recommended)

**Linux:**
- Debian 11+ or Ubuntu 20.04+
- WebKit2GTK 2.40+
- 4GB RAM minimum (8GB+ recommended)

---

## ✨ New in v0.7.0

### 1. Document RAG (Retrieval-Augmented Generation)

**Chat with your documents** - Upload PDFs, text files, and more, then ask questions about their content.

**How it works:**
1. Upload documents through the Document RAG interface
2. Documents are processed and embedded locally (no cloud)
3. Click "Search Documents" in chat to query your knowledge base
4. Select relevant results to add context
5. AI responds using your document content

**Supported Formats:**
- PDF (.pdf)
- Text (.txt, .md)
- Word (.docx) - coming soon
- PowerPoint (.pptx) - coming soon

**Technical:**
- Vector database: ChromaDB (embedded)
- Embeddings: sentence-transformers/all-MiniLM-L6-v2
- Search: Cosine similarity
- Privacy: 100% local processing

### 2. Voice I/O

**Talk to your AI** - Speak your messages and hear responses aloud.

**Speech Recognition:**
- Click microphone button or press `Ctrl+M`
- Speak naturally in your language
- Text appears in real-time
- Continuous recognition mode

**Text-to-Speech:**
- Click play button on any AI message
- Choose from system voices
- Adjust rate, pitch, volume
- Pause/resume controls

**Browser Support:**
- ✅ Chrome 25+
- ✅ Edge 79+
- ✅ Safari 14.1+
- ⚠️ Firefox (TTS only)

### 3. Production Build System

**Professional installers** for Windows, macOS, and Linux with proper branding and deep-link support (`avachatter://`).

---

## 🎯 Quick Start

### 1. Basic Chat

```
1. Launch AVACHATTER
2. Select an AI model (or download one)
3. Type a message
4. Get AI response
```

### 2. Document RAG

```
1. Open Document RAG (sidebar)
2. Upload your documents
3. Wait for processing
4. In chat, click "Search Documents"
5. Query your documents
6. Select results to add context
7. Ask questions - AI uses your docs!
```

### 3. Voice Input

```
1. Click microphone in chat (or Ctrl+M)
2. Grant microphone permission
3. Speak your message
4. Click send
5. AI responds
```

### 4. Voice Output

```
1. Get an AI response
2. Click play button on message
3. Hear response read aloud
4. Use pause/resume/stop controls
```

---

## 🛠️ Build from Source

See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for comprehensive build guide.

### Quick Build

```bash
# Clone repository
git clone https://github.com/anywave/avachatter
cd avachatter

# Install dependencies
npm install

# Run development mode
npm run dev:tauri

# Build for production
./build-installer.sh  # Linux/macOS
build-installer.bat   # Windows
```

### Prerequisites

- Node.js 18+
- Rust 1.70+
- Python 3.11
- Platform-specific build tools (see BUILD_INSTRUCTIONS.md)

---

## 📚 Documentation

- **[Release Notes](RELEASE_NOTES_v0.7.0.md)** - What's new in v0.7.0
- **[Build Instructions](BUILD_INSTRUCTIONS.md)** - How to build from source
- **[Test Plan](PHASE8_TEST_PLAN.md)** - Testing strategy and checklist
- **[Phase Documentation](docs/)** - Development phase details

### Technical Documentation

- **[Phase 5: Document RAG](PHASE5_COMPLETE.md)**
- **[Phase 6: Voice I/O](PHASE6_COMPLETE.md)**
- **[Phase 7: Installer](PHASE7_COMPLETE.md)**
- **[Phase 8: Testing](PHASE8_COMPLETE.md)** - Coming soon

---

## 🔒 Privacy & Security

### What We Collect

**Nothing.** AVACHATTER collects zero data.

### How It Works

1. **No Internet Required**: Core features work 100% offline
2. **No Telemetry**: No analytics, no tracking, no phone-home
3. **No Cloud Sync**: Your data stays on your device
4. **Local Models**: AI runs on your hardware
5. **Local Vectors**: Document embeddings stored locally
6. **Local Voice**: Speech processing in browser

### Data Storage

All data stored locally in:
- **Windows**: `C:\Users\<username>\AppData\Roaming\AVACHATTER`
- **macOS**: `~/Library/Application Support/com.avachatter.app`
- **Linux**: `~/.config/AVACHATTER`

---

## 🤝 Contributing

AVACHATTER is open source (AGPLv3). Contributions welcome!

### Development Workflow

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Areas for Contribution

- Additional document formats (PPT, XLS, etc.)
- More embedding models
- UI/UX improvements
- Performance optimizations
- Bug fixes
- Documentation
- Translations

---

## 📊 Technical Stack

### Frontend
- **Framework**: React 19
- **State Management**: Zustand
- **Styling**: TailwindCSS
- **TypeScript**: Full type safety
- **Build Tool**: Vite

### Backend
- **Desktop**: Tauri v2 (Rust)
- **AI Runtime**: llama.cpp
- **Python**: 3.11 (embedded)
- **Vector DB**: ChromaDB
- **Embeddings**: sentence-transformers

### Voice
- **STT**: Web Speech API (browser-native)
- **TTS**: Speech Synthesis API (browser-native)
- **No Cloud**: 100% local processing

---

## 🐛 Known Issues

1. **Large Documents**: Files >50MB may be slow to process
2. **Firefox Voice**: Speech recognition not supported (TTS works)
3. **Vector Search**: Performance degrades with >5000 chunks
4. **Model Size**: Large models (>7B) need 8GB+ RAM

See [GitHub Issues](https://github.com/anywave/avachatter/issues) for full list.

---

## 🗺️ Roadmap

### v0.8.0 (Planned)
- [ ] More document formats (PPT, XLS, Images)
- [ ] Hybrid search (keyword + semantic)
- [ ] Document metadata filtering
- [ ] Multi-language voice support
- [ ] Performance optimizations

### v0.9.0 (Future)
- [ ] Multi-modal embeddings (images, audio)
- [ ] Plugin system
- [ ] Collaborative features
- [ ] Mobile app
- [ ] Cloud sync (optional, encrypted)

---

## 📞 Support

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/anywave/avachatter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/anywave/avachatter/discussions)
- **Email**: support@anywave.com (coming soon)

### Reporting Bugs

Include:
- AVACHATTER version (v0.7.0)
- Operating system and version
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable

---

## 📄 License

**AGPLv3** - See [LICENSE](LICENSE) for details.

### What This Means

- ✅ Use commercially
- ✅ Modify and distribute
- ✅ Use privately
- ⚠️ Must disclose source
- ⚠️ Same license for derivatives
- ⚠️ Must include copyright and license

---

## 🙏 Acknowledgments

**Based On:**
- [Jan AI v0.6.8](https://github.com/menloresearch/jan) - Base application
- [Tauri](https://tauri.app) - Desktop framework
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Sentence Transformers](https://www.sbert.net/) - Embedding models
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - AI runtime

**Developed By**: ANYWAVE Team

---

## 🌟 Star History

If you find AVACHATTER useful, please star the repository!

---

## 📈 Stats

- **Version**: 0.7.0
- **Release Date**: February 10, 2026
- **Development Time**: ~15 hours (8 phases)
- **Lines of Code**: 2000+ (new features)
- **Files**: 50+ created/modified
- **Commits**: 8 major phases

---

<p align="center">
  <strong>AVACHATTER - Your Sovereign Intelligence</strong><br>
  100% Offline • Privacy-First • Open Source
</p>

<p align="center">
  <a href="https://github.com/anywave/avachatter">GitHub</a> •
  <a href="RELEASE_NOTES_v0.7.0.md">Release Notes</a> •
  <a href="BUILD_INSTRUCTIONS.md">Build Guide</a> •
  <a href="https://github.com/anywave/avachatter/issues">Issues</a>
</p>

---

**© 2026 ANYWAVE. Licensed under AGPLv3.**
