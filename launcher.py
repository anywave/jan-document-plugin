#!/usr/bin/env python
"""
Jan Document Plugin - Windows Launcher

This is the entry point for the compiled Windows executable.
Handles configuration loading, Tesseract detection, browser launch, and server startup.
"""

import os
import sys
import ctypes
import subprocess
import webbrowser
import threading
import time
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
        'JAN_PORT': '1337',
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
    print("         Jan Document Plugin v1.2.0")
    print("     Offline Document Processing for Local LLMs")
    print("=" * 64)
    print()


def main():
    """Main entry point."""
    set_console_title("Jan Document Plugin")
    print_banner()

    # Load configuration
    config = load_config()
    app_path = get_app_path()
    port = config['PROXY_PORT']

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

    print(f"  Web UI:      http://localhost:{port}")
    print(f"  Jan API:     http://localhost:{config['JAN_PORT']}")
    print(f"  Storage:     {config['STORAGE_DIR']}")
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
        from jan_proxy import app, config as proxy_config
        import uvicorn

        # Update proxy config
        proxy_config.jan_port = int(config['JAN_PORT'])
        proxy_config.proxy_port = int(port)
        proxy_config.persist_directory = str(storage_dir)
        proxy_config.tesseract_path = tesseract_path
        proxy_config.embedding_model = config['EMBEDDING_MODEL']
        proxy_config.auto_inject = config['AUTO_INJECT'].lower() == 'true'
        proxy_config.max_context_tokens = int(config['MAX_CONTEXT_TOKENS'])

        print("=" * 64)
        print()
        print(f"  Server running at: http://localhost:{port}")
        print()
        print("  Upload documents via the web interface, then chat in Jan!")
        print()
        print("  Press Ctrl+C to stop the server")
        print()
        print("=" * 64)
        print()

        # Auto-open browser if configured
        if config.get('AUTO_OPEN_BROWSER', 'true').lower() == 'true':
            open_browser_delayed(f"http://localhost:{port}", delay=2)

        # Start the server
        uvicorn.run(
            app,
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


if __name__ == "__main__":
    main()
