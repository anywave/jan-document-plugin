#!/usr/bin/env python
"""
Jan Document Plugin - Windows Launcher

This is the entry point for the compiled Windows executable.
Handles configuration loading, Tesseract detection, browser launch, and server startup.
"""

import os
import sys
import glob
import ctypes
import subprocess
import webbrowser
import threading
import time
import signal
import atexit
from pathlib import Path


def get_base_path():
    """Get the base path for resources (handles PyInstaller bundling)."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys._MEIPASS)
    else:
        # Running as script
        return Path(__file__).parent


def get_app_path():
    """Get the application directory (where exe is located)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


def load_config():
    """Load configuration from config.env file."""
    config = {
        'TESSERACT_PATH': '',
        'PROXY_PORT': '1338',
        'JAN_PORT': '11434',  # Ollama for document processing
        'JAN_AI_PORT': '1337',  # Jan AI for chat
        'DOCUMENT_PROCESSING_MODEL': 'qwen2.5:7b-instruct',
        'CHAT_MODEL': 'jan-nano:128k',
        'USE_JAN_AI_FOR_CHAT': 'true',
        'STORAGE_DIR': './jan_doc_store',
        'EMBEDDING_MODEL': 'all-MiniLM-L6-v2',
        'AUTO_INJECT': 'true',
        'MAX_CONTEXT_TOKENS': '8000',
        'AUTO_OPEN_BROWSER': 'true',
    }

    config_file = get_app_path() / 'config.env'

    if config_file.exists():
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()

    return config


def find_tesseract():
    """Find Tesseract executable."""
    # Check common locations
    locations = [
        get_app_path() / 'tesseract' / 'tesseract.exe',
        Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe'),
        Path(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'),
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Tesseract-OCR' / 'tesseract.exe',
    ]

    for loc in locations:
        if loc.exists():
            return str(loc)

    # Try PATH
    try:
        result = subprocess.run(['where', 'tesseract'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass

    return None


def set_console_title(title):
    """Set console window title on Windows."""
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    except:
        pass


def open_browser_delayed(url, delay=2):
    """Open browser after a delay to let server start."""
    def _open():
        time.sleep(delay)
        webbrowser.open(url)

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def print_banner():
    """Print startup banner."""
    print()
    print("=" * 64)
    print("         Jan Document Plugin v2.0.0-beta")
    print("     Offline Document Processing for Local LLMs")
    print("=" * 64)
    print()


# Global reference to llama-server subprocess for cleanup
_llama_process = None


def find_llama_server(app_path):
    """Locate bundled llama-server executable and model files."""
    llama_exe = app_path / "llm" / "llama-server.exe"
    if not llama_exe.exists():
        return None, None

    # Find GGUF model files
    model_files = sorted(glob.glob(str(app_path / "models" / "*.gguf")))
    if not model_files:
        return str(llama_exe), None

    # Use the first model found (single file) or primary shard
    return str(llama_exe), model_files[0]


def start_llama_server(llama_exe, model_path, port=1337):
    """Start llama-server as a subprocess with Vulkan GPU offloading."""
    global _llama_process

    cmd = [
        llama_exe,
        "-m", model_path,
        "--port", str(port),
        "--host", "0.0.0.0",
        "-ngl", "99",       # Offload all layers to GPU (Vulkan)
        "-c", "4096",        # Context length
    ]

    print(f"  Starting llama-server on port {port}...")
    print(f"  Model: {Path(model_path).name}")
    print(f"  GPU offload: all layers (Vulkan)")

    _llama_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    return _llama_process


def stop_llama_server():
    """Terminate llama-server subprocess if running."""
    global _llama_process
    if _llama_process and _llama_process.poll() is None:
        print("\n  Stopping llama-server...")
        _llama_process.terminate()
        try:
            _llama_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _llama_process.kill()
        _llama_process = None


def main():
    """Main entry point."""
    set_console_title("Jan Document Plugin v2.0.0-beta")
    print_banner()

    # Register cleanup handlers
    atexit.register(stop_llama_server)
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    # Load configuration
    config = load_config()
    app_path = get_app_path()
    port = config['PROXY_PORT']
    jan_port = int(config['JAN_PORT'])

    # Find Tesseract
    tesseract_path = config.get('TESSERACT_PATH', '')
    if not tesseract_path or not Path(tesseract_path).exists():
        tesseract_path = find_tesseract()

    print("  Configuration:")
    print("  " + "-" * 40)
    if tesseract_path:
        print(f"  OCR:         Enabled (Tesseract found)")
    else:
        print("  OCR:         Disabled (Tesseract not found)")

    print(f"  Chat UI:     http://localhost:{port}/ui")

    # Show two-tier system info if enabled
    if config['USE_JAN_AI_FOR_CHAT'].lower() == 'true':
        print(f"  Architecture: Two-Tier LLM System")
        print(f"    Chat:      {config['CHAT_MODEL']} (Jan AI port {config['JAN_AI_PORT']})")
        print(f"    Documents: {config['DOCUMENT_PROCESSING_MODEL']} (Ollama port {jan_port})")
    else:
        print(f"  LLM API:     http://localhost:{jan_port}")

    print(f"  Storage:     {config['STORAGE_DIR']}")

    # --- Start bundled llama-server if available ---
    llama_exe, model_path = find_llama_server(app_path)
    llama_started = False

    if llama_exe and model_path:
        print()
        try:
            start_llama_server(llama_exe, model_path, port=jan_port)
            llama_started = True
            # Give llama-server a moment to bind its port
            time.sleep(2)
        except Exception as e:
            print(f"  WARNING: Failed to start llama-server: {e}")
            print(f"  Continuing without bundled LLM — connect Jan or another server to port {jan_port}")
    elif llama_exe and not model_path:
        print()
        print("  WARNING: llama-server found but no .gguf model in models/ directory")
        print(f"  Place a GGUF model in: {app_path / 'models'}")
    else:
        print()
        print(f"  No bundled llama-server — expecting LLM server on port {jan_port}")

    print()

    # Ensure storage directory exists
    storage_dir = Path(config['STORAGE_DIR'])
    if not storage_dir.is_absolute():
        storage_dir = app_path / storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)

    # Add app path to Python path for imports
    sys.path.insert(0, str(get_base_path()))
    sys.path.insert(0, str(app_path))

    # Import and configure the proxy
    try:
        from jan_proxy import app as proxy_app, config as proxy_config
        import uvicorn

        # Update proxy config
        proxy_config.jan_port = jan_port
        proxy_config.jan_ai_port = int(config['JAN_AI_PORT'])
        proxy_config.use_jan_ai_for_chat = config['USE_JAN_AI_FOR_CHAT'].lower() == 'true'
        proxy_config.document_processing_model = config['DOCUMENT_PROCESSING_MODEL']
        proxy_config.chat_model = config['CHAT_MODEL']
        proxy_config.proxy_port = int(port)
        proxy_config.persist_directory = str(storage_dir)
        proxy_config.tesseract_path = tesseract_path
        proxy_config.embedding_model = config['EMBEDDING_MODEL']
        proxy_config.auto_inject = config['AUTO_INJECT'].lower() == 'true'
        proxy_config.max_context_tokens = int(config['MAX_CONTEXT_TOKENS'])

        print("=" * 64)
        print()
        print(f"  Chat UI:        http://localhost:{port}/ui")
        if llama_started:
            print(f"  LLM:            Bundled llama-server (Vulkan GPU)")
        else:
            if config['USE_JAN_AI_FOR_CHAT'].lower() == 'true':
                print(f"  Chat (Tier 2):  Jan AI on port {config['JAN_AI_PORT']} ({config['CHAT_MODEL']})")
                print(f"  Docs (Tier 1):  Ollama on port {jan_port} ({config['DOCUMENT_PROCESSING_MODEL']})")
            else:
                print(f"  LLM:            Ollama on port {jan_port}")
        print()
        print("  Press Ctrl+C to stop")
        print()
        print("=" * 64)
        print()

        # Auto-open browser to Chat UI
        if config.get('AUTO_OPEN_BROWSER', 'true').lower() == 'true':
            open_browser_delayed(f"http://localhost:{port}/ui", delay=3)

        # Start the proxy server
        uvicorn.run(
            proxy_app,
            host="0.0.0.0",
            port=int(port),
            log_level="info"
        )

    except ImportError as e:
        print(f"ERROR: Failed to import required modules: {e}")
        print()
        print("If running from source, please run: install.bat")
        input("Press Enter to exit...")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        print("Server stopped.")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
    finally:
        stop_llama_server()


if __name__ == "__main__":
    main()
