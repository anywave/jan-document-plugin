# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Jan Document Plugin

Build with:
    pyinstaller JanDocumentPlugin.spec

This creates a single-folder distribution with all dependencies.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all sentence-transformers data
sentence_transformers_datas = collect_data_files('sentence_transformers')
chromadb_datas = collect_data_files('chromadb')

# Hidden imports for dynamic modules
hidden_imports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'sentence_transformers',
    'chromadb',
    'chromadb.config',
    'httpx',
    'httpx._transports',
    'httpx._transports.default',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
    'fitz',
    'docx',
    'openpyxl',
    'PIL',
    'pytesseract',
    'pydantic',
    'pydantic_core',
    'starlette',
    'fastapi',
    'speech_recognition',
    'pyaudio',
]

# Add all chromadb submodules
hidden_imports.extend(collect_submodules('chromadb'))
hidden_imports.extend(collect_submodules('sentence_transformers'))

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('document_processor.py', '.'),
        ('jan_proxy.py', '.'),
        ('chat_ui.html', '.'),
        ('config.env.example', '.'),
        ('README.md', '.'),
        # Consciousness pipeline
        ('consciousness_pipeline.py', '.'),
        ('soul_registry.py', '.'),
        ('soul_registry_state.json', '.'),
        ('seed_transit.py', '.'),
        ('fractal_analyzer.py', '.'),
        ('resonance_db.py', '.'),
        # Supporting modules
        ('resource_monitor.py', '.'),
        ('ocr_processor.py', '.'),
        ('batch_processor.py', '.'),
    ] + sentence_transformers_datas + chromadb_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JanDocumentPlugin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Show console for logging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JanDocumentPlugin',
)
