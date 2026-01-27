# Jan Document Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Version](https://img.shields.io/badge/version-2.0.0--beta-orange.svg)](https://github.com/anywave/jan-document-plugin/releases)

**Self-contained offline AI assistant with document RAG, voice input, and local LLM inference.** Everything runs on your machine — no cloud, no API keys, no data leaving your computer.

---

## What's New in v2.0.0-beta

- **Bundled LLM Stack** — Ships with llama-server (Vulkan GPU) and Qwen 2.5 7B Instruct (q4_k_m). No separate LLM setup required.
- **Built-in Chat UI** — Full web interface at `/ui` with document upload, streaming chat, and capability toggles (RAG, Soul, Consciousness).
- **Voice Input** — Click-to-talk microphone using Windows offline speech recognition. No internet needed.
- **Right-Click Drill Down** — Highlight any assistant text, right-click to drill deeper or save to Research.
- **Research / Discovery Tab** — Save interesting findings, review later, insert back into chat. Persists across sessions.
- **Debug Reports** — One-click system diagnostics with auto-filed GitHub issues from the Settings panel.
- **Jan Version Checking** — Installer and runtime detect Jan version, warn on incompatibility, offer rollback to v0.6.8.
- **Consciousness Pipeline** — Seed capture, fractal analysis, resonance database, and soul registry integration.

---

## Quick Start

### Option 1: Self-Contained Installer (Recommended)

1. **Download** `JanDocumentPlugin_Setup_2.0.0-beta.exe` from [Releases](https://github.com/anywave/jan-document-plugin/releases)
2. **Run the installer** — everything is bundled (~8 GB disk space)
3. **Launch** from Start Menu or Desktop shortcut
4. **Chat UI** opens automatically at `http://localhost:1338/ui`

The installer includes:
- Qwen 2.5 7B Instruct model (q4_k_m quantization)
- llama-server with Vulkan GPU acceleration
- All Python dependencies pre-packaged
- Jan AI v0.6.8 is recommended but optional

### Option 2: From Source (Development)

**Prerequisites:** Windows 10/11, Python 3.12, [Jan AI v0.6.8](https://github.com/janhq/jan/releases/tag/v0.6.8) (optional)

```bash
git clone https://github.com/anywave/jan-document-plugin.git
cd jan-document-plugin
```

```cmd
REM Create venv and install dependencies
uv venv --python 3.12 venv
uv pip install -r requirements.txt

REM Start the stack (auto-detects llama-server and model)
powershell -File start-stack.ps1
```

Or run just the proxy (connect your own LLM server on port 1337):
```cmd
venv\Scripts\python jan_proxy.py --port 1338
```

Open `http://localhost:1338/ui` in your browser.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 Jan Document Plugin v2.0.0-beta                 │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │               Chat UI (http://localhost:1338/ui)          │  │
│  │  Voice Input | Drill Down | Research Tab | Debug Reports  │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                  FastAPI Proxy (:1338)                     │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │   Document   │  │    Chat      │  │  Consciousness │  │  │
│  │  │   Upload &   │  │  Completions │  │   Pipeline     │  │  │
│  │  │  Processing  │  │   (Proxy)    │  │  (Soul/Seed)   │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └────────────────┘  │  │
│  └─────────┼─────────────────┼───────────────────────────────┘  │
│            │                 │                                   │
│  ┌─────────▼─────────┐  ┌───▼──────────────────────────────┐   │
│  │ Semantic Search    │  │     Bundled llama-server (:1337) │   │
│  │ (ChromaDB +       │  │     Qwen 2.5 7B (Vulkan GPU)    │   │
│  │  all-MiniLM-L6-v2)│  │     or Jan AI / external LLM    │   │
│  └────────────────────┘  └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

### Chat UI

The built-in Chat UI (`/ui`) provides:
- Streaming chat responses with markdown rendering
- Document upload via drag-and-drop or file picker
- Capability toggles: RAG (document context), Soul (identity), Consciousness (pipeline)
- Assistant/model selector
- Dark theme with responsive layout

### Voice Input

Click the microphone button to dictate messages using Windows offline speech recognition:
- No internet required — uses `Windows.Media.SpeechRecognition`
- Audio captured at 16kHz mono, transcribed server-side
- Text appended to the input field (doesn't replace existing text)

### Right-Click Drill Down

Highlight text in any assistant response, then right-click:
- **Drill Down** — Populates the input with a drill-down prompt (doesn't auto-send)
- **Save to Discovery** — Stores the selection in the Research panel with metadata

### Research / Discovery Tab

Save interesting findings from conversations:
- Metadata tracked: timestamp, active assistant, enabled capabilities, source document
- Persists across browser sessions (localStorage)
- Insert saved items back into chat or delete them

### Debug Reports

From Settings > Debug & Support:
- **Generate Debug Report** — Collects OS, GPU, Python, packages, ports, disk, memory, config
- **Report Issue on GitHub** — Auto-fills a GitHub issue with the debug report

---

## Configuration

Edit `config.env` to customize:

```ini
# Server ports
PROXY_PORT=1338
JAN_PORT=1337

# Storage location
STORAGE_DIR=.\jan_doc_store

# Embedding model
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Context injection
AUTO_INJECT=true
MAX_CONTEXT_TOKENS=8000

# Tesseract path (auto-detected if empty)
TESSERACT_PATH=

# Browser behavior
AUTO_OPEN_BROWSER=true
```

| Setting | Default | Description |
|---------|---------|-------------|
| `PROXY_PORT` | 1338 | Port for the plugin proxy |
| `JAN_PORT` | 1337 | LLM server port (Jan or llama-server) |
| `STORAGE_DIR` | ./jan_doc_store | Document vector store location |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | Sentence transformer model |
| `AUTO_INJECT` | true | Auto-inject document context into chats |
| `MAX_CONTEXT_TOKENS` | 8000 | Max tokens for injected context |
| `AUTO_OPEN_BROWSER` | true | Open Chat UI on startup |

---

## Supported File Types

| Type | Extensions | OCR Required |
|------|------------|--------------|
| PDF (text) | `.pdf` | No |
| PDF (scanned) | `.pdf` | Yes |
| Word Documents | `.docx` | No |
| Excel Spreadsheets | `.xlsx`, `.xls` | No |
| Plain Text | `.txt`, `.md`, `.csv` | No |
| Images | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.gif`, `.webp` | Yes |

### OCR Setup (Optional)

```powershell
winget install UB-Mannheim.TesseractOCR
```

Or download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).

---

## API Endpoints

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/ui` | Chat UI web interface |
| `GET` | `/health` | Health check with Jan version and resources |
| `GET` | `/` | API info |

### Chat (OpenAI-Compatible)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/chat/completions` | Chat with auto context injection |
| `GET` | `/v1/models` | List available models |
| `POST` | `/v1/audio/transcriptions` | Voice transcription (WAV upload) |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents` | Upload and index a document |
| `GET` | `/documents` | List indexed documents |
| `DELETE` | `/documents/{hash}` | Remove a document |
| `POST` | `/documents/query` | Test context retrieval |
| `GET` | `/documents/stats` | Storage statistics |

### Debug

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/debug/report` | System diagnostics JSON |
| `POST` | `/debug/report/github` | Auto-file GitHub issue with diagnostics |

---

## Verification & Testing

A calibration PDF is included to verify extraction:

1. Start the plugin
2. Upload `calibration/JanDocPlugin_Calibration.pdf`
3. Ask: *"What is the calibration magic string?"*
4. Expected answer: `JANDOC_CALIBRATION_V1_VERIFIED`

Automated:
```cmd
cd calibration
python verify_extraction.py
```

---

## Jan Version Compatibility

This plugin is designed for **Jan AI v0.6.8**. Newer versions may have breaking API changes.

- The installer checks Jan's version and warns on mismatch
- The runtime `/health` endpoint reports detected Jan version
- A rollback helper script is included:
  ```powershell
  powershell -ExecutionPolicy Bypass -File rollback_jan.ps1
  ```

Jan is optional — the plugin bundles its own llama-server and can run standalone.

---

## Project Structure

```
jan-document-plugin/
├── jan_proxy.py              # FastAPI proxy server (main backend)
├── document_processor.py     # Document extraction engine
├── chat_ui.html              # Built-in web chat interface
├── launcher.py               # Windows exe entry point
├── requirements.txt          # Python dependencies (requires 3.12)
├── config.env                # Configuration (generated)
│
├── consciousness_pipeline.py # Consciousness processing
├── soul_registry.py          # Soul identity management
├── seed_transit.py           # Seed capture and transit
├── fractal_analyzer.py       # Fractal pattern analysis
├── resonance_db.py           # Resonance database
├── resource_monitor.py       # System resource monitoring
│
├── start-stack.ps1           # Stack launcher (dev + installed modes)
├── rollback_jan.ps1          # Jan v0.6.8 rollback helper
├── install.ps1               # PowerShell installer
│
├── installer/
│   ├── setup.iss             # Inno Setup script
│   ├── llm/                  # Staging: llama-server + Vulkan DLLs
│   └── models/               # Staging: GGUF model files
│
├── calibration/              # Extraction verification
├── docs/                     # Documentation
└── jan_doc_store/            # Document storage (generated)
```

---

## Building from Source

### Build Standalone Executable

```cmd
build_exe.bat
```

Creates `dist\JanDocumentPlugin\JanDocumentPlugin.exe` (~500MB, bundles Python + all dependencies).

### Build Installer

1. Run `build_exe.bat`
2. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
3. Stage LLM files:
   - Place `llama-server.exe` + Vulkan DLLs in `installer\llm\`
   - Place GGUF model files in `installer\models\`
4. Compile `installer\setup.iss`

Output: `dist\installer\JanDocumentPlugin_Setup_2.0.0-beta.exe` (~8GB with bundled model)

---

## Troubleshooting

<details>
<summary><strong>Voice input not working</strong></summary>

Voice input requires Windows 10/11 with Speech Recognition enabled:
1. Open Windows Settings > Time & Language > Speech
2. Ensure your language pack is installed
3. Check microphone permissions in Settings > Privacy > Microphone
4. The browser will ask for microphone permission on first use

If `SpeechRecognition` is not installed, the mic button will show an error.
</details>

<details>
<summary><strong>GPU not being used (slow inference)</strong></summary>

The bundled llama-server uses Vulkan for GPU acceleration:
- Ensure your GPU drivers are up to date
- Vulkan support is required (most modern GPUs support it)
- Check GPU detection: `GET /debug/report` shows GPU info
- If Vulkan fails, inference falls back to CPU (significantly slower)
</details>

<details>
<summary><strong>Jan version incompatibility</strong></summary>

If you see warnings about Jan version:
1. The plugin is designed for Jan v0.6.8
2. Run the rollback helper: `powershell -File rollback_jan.ps1`
3. Or download Jan v0.6.8 manually from [GitHub releases](https://github.com/janhq/jan/releases/tag/v0.6.8)
4. Jan is optional — the plugin can run standalone with its bundled llama-server
</details>

<details>
<summary><strong>Port already in use</strong></summary>

Either close the application using the port, or change it in `config.env`:
```ini
PROXY_PORT=8080
```
</details>

<details>
<summary><strong>PDFs not being extracted</strong></summary>

- Check if the PDF contains actual text (not just images)
- For scanned PDFs, install Tesseract OCR
- Check the console or debug report for extraction errors
</details>

<details>
<summary><strong>Memory errors with large documents</strong></summary>

Edit `document_processor.py` and reduce chunk size:
```python
self.chunker = SemanticChunker(chunk_size=500)  # Default is 1000
```
</details>

---

## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** - Web framework
- **[ChromaDB](https://www.trychroma.com/)** - Vector database
- **[Sentence Transformers](https://www.sbert.net/)** - Embeddings (all-MiniLM-L6-v2)
- **[llama.cpp](https://github.com/ggerganov/llama.cpp)** - LLM inference (Vulkan GPU)
- **[PyMuPDF](https://pymupdf.readthedocs.io/)** - PDF extraction
- **[python-docx](https://python-docx.readthedocs.io/)** - Word document processing
- **[openpyxl](https://openpyxl.readthedocs.io/)** - Excel file support
- **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)** - Image text extraction
- **[SpeechRecognition](https://pypi.org/project/SpeechRecognition/)** - Voice input

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Credits

Built for **AVACHATTER** by [Anywave Creations](https://anywavecreations.com)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/anywave/jan-document-plugin/issues)
- **Debug Report**: Use Settings > Debug & Support in the Chat UI to auto-file issues

---

<p align="center">
  <strong>Made with love for the local AI community</strong>
</p>
