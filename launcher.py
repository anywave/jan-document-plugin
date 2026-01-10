#!/usr/bin/env python
"""
Jan Document Plugin - Windows Launcher

This is the entry point for the compiled Windows executable.
Handles configuration loading, Tesseract detection, and server startup.
"""

import os
import sys
import ctypes
import subprocess
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


def print_banner():
    """Print startup banner."""
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║            Jan Document Plugin v1.0.0                        ║")
    print("║        Offline Document Processing for Local LLMs           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()


def main():
    """Main entry point."""
    set_console_title("Jan Document Plugin")
    print_banner()
    
    # Load configuration
    config = load_config()
    app_path = get_app_path()
    
    # Find Tesseract
    tesseract_path = config.get('TESSERACT_PATH', '')
    if not tesseract_path or not Path(tesseract_path).exists():
        tesseract_path = find_tesseract()
    
    if tesseract_path:
        print(f"  Tesseract: {tesseract_path}")
    else:
        print("  Tesseract: Not found (OCR disabled)")
    
    print(f"  Proxy Port: {config['PROXY_PORT']}")
    print(f"  Jan Port: {config['JAN_PORT']}")
    print(f"  Storage: {config['STORAGE_DIR']}")
    print(f"  Auto-inject: {config['AUTO_INJECT']}")
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
        from jan_proxy import app, config as proxy_config, ProxyConfig
        import uvicorn
        
        # Update proxy config
        proxy_config.jan_port = int(config['JAN_PORT'])
        proxy_config.proxy_port = int(config['PROXY_PORT'])
        proxy_config.persist_directory = str(storage_dir)
        proxy_config.tesseract_path = tesseract_path
        proxy_config.embedding_model = config['EMBEDDING_MODEL']
        proxy_config.auto_inject = config['AUTO_INJECT'].lower() == 'true'
        proxy_config.max_context_tokens = int(config['MAX_CONTEXT_TOKENS'])
        
        print("=" * 60)
        print(f"  Server starting at: http://localhost:{config['PROXY_PORT']}")
        print(f"  Forwarding to Jan:  http://localhost:{config['JAN_PORT']}")
        print("=" * 60)
        print()
        print("Press Ctrl+C to stop the server")
        print()
        
        # Start the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(config['PROXY_PORT']),
            log_level="info"
        )
        
    except ImportError as e:
        print(f"ERROR: Failed to import required modules: {e}")
        print()
        print("Please run the installer first: install.bat")
        input("Press Enter to exit...")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        print("Server stopped.")
    except Exception as e:
        print(f"ERROR: {e}")
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
