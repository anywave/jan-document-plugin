# Jan Document Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Jan AI](https://img.shields.io/badge/Jan-AI-green.svg)](https://jan.ai/)

**Offline Document Processing for Local LLMs** - Enable your local AI assistant to read and understand your documents without sending data to the cloud.

---

## What is This?

Jan Document Plugin is a **local proxy server** that adds document understanding capabilities to [Jan AI](https://jan.ai/). It intercepts your chat requests, finds relevant content from your uploaded documents, and injects that context into your conversations - all running locally on your machine.

### Key Features

- **100% Offline** - Your documents never leave your computer
- **Multiple Formats** - PDF, DOCX, XLSX, TXT, and images
- **OCR Support** - Extract text from scanned documents and images
- **Semantic Search** - Find relevant content using AI embeddings
- **Auto-Context Injection** - Seamlessly adds document context to your chats
- **Simple Setup** - One-click installer with interactive tutorial

---

## Quick Start

### Prerequisites

- **Windows 10/11** (64-bit)
- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **Jan AI** ([Download](https://jan.ai/))

### Installation

1. **Download** the latest release or clone this repository:
   ```bash
   git clone https://github.com/anywave/jan-document-plugin.git
   cd jan-document-plugin
   ```

2. **Run the installer**:
   ```cmd
   install.bat
   ```
   Or for detailed output with diagnostics:
   ```cmd
   install_debug.bat --debug
   ```

3. **Start Jan** and enable the Local API Server:
   - Open Jan → Settings → Local API Server → Enable

4. **Launch the plugin**:
   ```cmd
   JanDocumentPlugin.bat
   ```

5. **Upload documents** at `http://localhost:1338`

6. **Chat with your documents** in Jan!

### First Time? Use the Tutorial

```cmd
tutorial.bat
```

The interactive tutorial will guide you through setup, verification, and troubleshooting.

---

## How It Works

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────┐
│     Jan      │────▶│  Jan Document Plugin │────▶│   Jan API    │
│   (Chat UI)  │     │     (Port 1338)      │     │  (Port 1337) │
└──────────────┘     └─────────────────────┘     └──────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │   Your Documents │
                     │   (ChromaDB)     │
                     └─────────────────┘
```

1. You upload documents to the plugin
2. Documents are processed and stored locally in ChromaDB
3. When you chat in Jan, the plugin finds relevant document chunks
4. Context is automatically injected into your conversation
5. The LLM responds with knowledge from your documents

---

## Verification & Testing

### Calibration PDF

A calibration PDF is included to verify extraction is working correctly:

1. Start the plugin
2. Upload `calibration/JanDocPlugin_Calibration.pdf`
3. Ask: *"What is the calibration magic string?"*
4. Expected answer: `JANDOC_CALIBRATION_V1_VERIFIED`

### Automated Verification

```cmd
cd calibration
python verify_extraction.py
```

This will:
- Upload the calibration PDF automatically
- Ask known verification questions
- Validate responses against expected answers
- Provide clear pass/fail results

---

## Command Line Options

```cmd
# Start normally
JanDocumentPlugin.bat

# Start with debug logging
JanDocumentPlugin.bat --debug

# Use a different port
JanDocumentPlugin.bat --port 8080

# Run startup checks only (test mode)
JanDocumentPlugin.bat --test

# Show help
JanDocumentPlugin.bat --help
```

---

## Configuration

Edit `config.env` to customize:

```ini
# Tesseract path (auto-detected if empty)
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe

# Server ports
PROXY_PORT=1338
JAN_PORT=1337

# Storage location
STORAGE_DIR=.\jan_doc_store

# Embedding model
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Context injection settings
AUTO_INJECT=true
MAX_CONTEXT_TOKENS=8000

# Logging
DEBUG_MODE=0
LOG_LEVEL=INFO
```

### Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `PROXY_PORT` | 1338 | Port for the document plugin |
| `JAN_PORT` | 1337 | Jan's Local API Server port |
| `STORAGE_DIR` | ./jan_doc_store | Where documents are stored |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | Sentence transformer model |
| `AUTO_INJECT` | true | Auto-inject document context |
| `MAX_CONTEXT_TOKENS` | 8000 | Max tokens for context |

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

For scanned PDFs and images, install Tesseract OCR:

**Option A: Winget (Easiest)**
```powershell
winget install UB-Mannheim.TesseractOCR
```

**Option B: Manual Download**
1. Download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
2. Install to `C:\Program Files\Tesseract-OCR`
3. Re-run the installer or update `config.env`

---

## API Endpoints

### Document Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents` | Upload and index a document |
| `GET` | `/documents` | List all indexed documents |
| `DELETE` | `/documents/{hash}` | Remove a document |
| `POST` | `/documents/query` | Test context retrieval |
| `GET` | `/documents/stats` | Get statistics |

### Chat (OpenAI-Compatible)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/chat/completions` | Chat with auto context injection |
| `GET` | `/v1/models` | List available models |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Check server and Jan connection |
| `GET` | `/` | API info and documentation |

### Upload via API

```bash
curl -X POST http://localhost:1338/documents \
  -F "file=@document.pdf"
```

### Search Documents

```bash
curl -X POST http://localhost:1338/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the main topic?"}'
```

---

## Project Structure

```
jan-document-plugin/
├── jan_proxy.py              # Main proxy server
├── document_processor.py     # Document extraction engine
├── requirements.txt          # Python dependencies
├── config.env               # Configuration (generated)
│
├── JanDocumentPlugin.bat     # Main launcher with debug mode
├── install.bat              # Standard installer
├── install_debug.bat        # Debug installer with diagnostics
├── tutorial.bat             # Interactive setup wizard
│
├── calibration/
│   ├── create_calibration_pdf.py    # Generate test PDF
│   ├── verify_extraction.py         # Automated verification
│   └── JanDocPlugin_Calibration.pdf # Pre-generated test PDF
│
├── docs/                    # Documentation
├── tesseract/              # Portable Tesseract (optional)
├── venv/                   # Python virtual environment (generated)
└── jan_doc_store/          # Document storage (generated)
```

---

## Troubleshooting

<details>
<summary><strong>Python not found</strong></summary>

Install Python from [python.org](https://www.python.org/downloads/) and check "Add Python to PATH" during installation. Restart your terminal after installation.
</details>

<details>
<summary><strong>Cannot connect to Jan</strong></summary>

1. Make sure Jan is running
2. Enable Local API Server: Jan → Settings → Local API Server → Enable
3. Check that port 1337 is not blocked
</details>

<details>
<summary><strong>Port 1338 already in use</strong></summary>

Either close the application using port 1338, or use a different port:
```cmd
JanDocumentPlugin.bat --port 8080
```
</details>

<details>
<summary><strong>PDFs not being extracted</strong></summary>

- Check if the PDF contains actual text (not just images)
- For scanned PDFs, install Tesseract OCR
- Check the console for extraction errors
- Run with `--debug` flag for more details
</details>

<details>
<summary><strong>AI not using document context</strong></summary>

1. Verify documents uploaded: check `/documents` endpoint
2. Ensure Jan is connected via the plugin (port 1338)
3. Check `AUTO_INJECT=true` in config.env
4. Run the verification script: `python calibration/verify_extraction.py`
</details>

<details>
<summary><strong>Memory errors with large documents</strong></summary>

Edit `document_processor.py` and reduce chunk size:
```python
self.chunker = SemanticChunker(chunk_size=500)  # Default is 1000
```
</details>

For more help, run the interactive troubleshooter:
```cmd
tutorial.bat
```

---

## Building Standalone Executable (Optional)

To create a standalone `.exe` that doesn't require Python installed:

```cmd
build_exe.bat
```

This creates `dist\JanDocumentPlugin\JanDocumentPlugin.exe`

**Note:** The executable is larger (~500MB) because it bundles Python and all dependencies.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Jan Document Plugin Proxy                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   FastAPI Server (:1338)                   │ │
│  │  ┌──────────────────┐      ┌─────────────────────────────┐ │ │
│  │  │ Document Upload   │      │  Chat Completions Proxy     │ │ │
│  │  │  & Processing    │      │  (Context Injection)        │ │ │
│  │  └────────┬─────────┘      └──────────────┬──────────────┘ │ │
│  └───────────┼───────────────────────────────┼────────────────┘ │
│              │                               │                   │
│  ┌───────────▼───────────┐    ┌─────────────▼─────────────────┐ │
│  │   Document Processor   │    │     Semantic Search          │ │
│  │  ┌─────┬─────┬──────┐ │    │  ┌─────────────────────────┐ │ │
│  │  │ PDF │DOCX │ OCR  │ │    │  │ all-MiniLM-L6-v2        │ │ │
│  │  │     │     │      │ │    │  │ Sentence Transformer    │ │ │
│  │  └─────┴─────┴──────┘ │    │  └─────────────────────────┘ │ │
│  └───────────┬───────────┘    └─────────────┬─────────────────┘ │
│              │                              │                    │
│              └──────────────┬───────────────┘                    │
│                             ▼                                    │
│                   ┌─────────────────┐                           │
│                   │    ChromaDB     │                           │
│                   │  Vector Store   │                           │
│                   └─────────────────┘                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Proxied requests
                           ▼
              ┌─────────────────────────┐
              │      Jan Server (:1337) │
              │    Local LLM Inference  │
              └─────────────────────────┘
```

---

## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** - High-performance web framework
- **[ChromaDB](https://www.trychroma.com/)** - Vector database for semantic search
- **[Sentence Transformers](https://www.sbert.net/)** - Text embeddings (all-MiniLM-L6-v2)
- **[PyPDF](https://pypdf.readthedocs.io/)** - PDF text extraction
- **[python-docx](https://python-docx.readthedocs.io/)** - Word document processing
- **[openpyxl](https://openpyxl.readthedocs.io/)** - Excel file support
- **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)** - Image text extraction
- **[ReportLab](https://www.reportlab.com/)** - PDF generation (for calibration)

---

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

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
- **Discussions**: [GitHub Discussions](https://github.com/anywave/jan-document-plugin/discussions)

---

<p align="center">
  <strong>Made with love for the local AI community</strong>
</p>
