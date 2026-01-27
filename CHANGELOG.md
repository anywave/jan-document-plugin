# Changelog

All notable changes to Jan Document Plugin are documented here.

## [2.0.0-beta] - 2026-01-27

### Added

- **Bundled LLM Stack**: Self-contained installer with llama-server (Vulkan GPU) and Qwen 2.5 7B Instruct (q4_k_m quantization). No separate LLM setup required.
- **Built-in Chat UI** (`GET /ui`): Full web interface served by the proxy with streaming chat, document upload, capability toggles (RAG, Soul, Consciousness), and dark theme.
- **Voice Input**: Click-to-talk microphone button using Windows offline speech recognition (`SpeechRecognition` + `PyAudio`). Audio captured client-side at 16kHz mono WAV, transcribed via `POST /v1/audio/transcriptions`.
- **Right-Click Context Menu**: Highlight assistant text and right-click for "Drill Down" (populates input with drill-down prompt) or "Save to Discovery" (stores in Research panel).
- **Research / Discovery Tab**: Left sidebar panel for saving and reviewing interesting findings. Tracks metadata (timestamp, assistant, capabilities, source document). Persists via localStorage.
- **Debug Report System**: `GET /debug/report` collects OS, GPU, Python, packages, ports, disk, memory, document store, and config. `POST /debug/report/github` auto-generates a GitHub issue URL with the report.
- **Jan Version Compatibility Checking**: Installer (Inno Setup), PowerShell installer (`install.ps1`), and runtime all detect Jan version from `package.json`. Warns on mismatch with v0.6.8. Rollback helper script (`rollback_jan.ps1`) included.
- **Consciousness Pipeline Integration**: Soul registry, seed transit, fractal analyzer, and resonance database wired into chat completions with per-request capability toggles.
- **Launcher Subprocess Management**: `launcher.py` starts bundled llama-server as a subprocess with Vulkan GPU flags (`-ngl 99`), manages lifecycle with `atexit`/`signal` handlers, auto-opens Chat UI in browser.
- **Stack Launcher Installed Mode**: `start-stack.ps1 --Installed` uses bundled `.\llm\llama-server.exe` and `.\models\*.gguf` paths.
- **Tutorial Updates**: Three new tutorial steps covering Voice Input, Right-Click Drill Down, and Research Panel.

### Changed

- Version bumped to `2.0.0-beta` across all files (jan_proxy.py, launcher.py, setup.iss, start-stack.ps1, build_exe.bat).
- `requirements.txt`: Added `SpeechRecognition>=3.10.0` and `PyAudio>=0.2.14`. Updated Python requirement note to 3.12.
- `JanDocumentPlugin.spec`: Added all consciousness pipeline `.py` files, `chat_ui.html`, `soul_registry_state.json`, `config.env.example`, `resource_monitor.py`, `ocr_processor.py`, `batch_processor.py` to `datas`. Added `speech_recognition` and `pyaudio` to `hiddenimports`.
- `build_exe.bat`: Copies `chat_ui.html` and `rollback_jan.ps1` to dist. Creates `llm/` and `models/` staging directories with README placeholders.
- `installer/setup.iss`: Bundles `chat_ui.html`, `llm\*` (llama-server + Vulkan DLLs), `models\*` (GGUF), `rollback_jan.ps1`. Added Pascal Script for Jan version detection. Updated welcome/finish messages. Added "Open Chat UI" Start Menu shortcut.
- `install.ps1`: Added Jan version detection and compatibility warning after existing Jan/llama-server detection section.
- `start-stack.ps1`: Updated output to reference Chat UI URL. Jan configuration instructions marked as optional.
- `launcher.py`: Browser now opens `/ui` instead of root. Banner shows llama-server status. Imports `app as proxy_app` to avoid name collision.
- `/health` endpoint: Now includes `jan_version` field from runtime detection.
- CLI banner: Added Jan version display line and speech recognition status.
- `README.md`: Full rewrite for v2.0.0-beta with updated architecture diagram, installer instructions, new feature documentation, and voice input troubleshooting.

## [1.2.0] - Previous Release

### Features (baseline)

- FastAPI proxy server with OpenAI-compatible chat completions
- Document upload and indexing (PDF, DOCX, XLSX, TXT, images)
- ChromaDB vector store with all-MiniLM-L6-v2 embeddings
- Auto context injection into chat requests
- OCR support via Tesseract
- Calibration PDF verification system
- Resource monitoring
- PyInstaller build support
- Inno Setup installer
