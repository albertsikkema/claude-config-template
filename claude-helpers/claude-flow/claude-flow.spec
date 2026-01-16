# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Claude Flow desktop app."""

import tomllib
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

block_cipher = None

# Project paths
spec_root = Path(SPECPATH)
frontend_dist = spec_root / "claude-flow-board" / "dist"

# Read version from pyproject.toml
pyproject_path = spec_root / "pyproject.toml"
with open(pyproject_path, "rb") as f:
    pyproject_data = tomllib.load(f)
VERSION = pyproject_data["project"]["version"]

# Collect all FastAPI/Uvicorn/Pydantic dependencies
hiddenimports = [
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
    'pydantic',
    'pydantic.deprecated',
    'pydantic_core',
    'sqlalchemy.sql.default_comparator',
    # PyWebView dependencies for macOS
    'webview',
    'webview.platforms.cocoa',
    'AppKit',
    'Foundation',
    'WebKit',
    'objc',
    # PydanticAI for AI-powered task improvement
    'pydantic_ai',
    'pydantic_ai.agent',
    'pydantic_ai.models',
    'pydantic_ai.models.openai',
    'httpx',
    'openai',
    'openai._client',
    'openai.resources',
]

# Collect SQLAlchemy submodules
hiddenimports += collect_submodules('sqlalchemy')

# Collect PyWebView submodules (exclude Android)
hiddenimports += [m for m in collect_submodules('webview') if 'android' not in m]

# Collect AI-related submodules (exclude optional/problematic ones)
hiddenimports += [m for m in collect_submodules('pydantic_ai') if 'prefect' not in m and 'durable' not in m]
hiddenimports += collect_submodules('httpx')
hiddenimports += [m for m in collect_submodules('openai') if 'helpers' not in m]  # Exclude voice_helpers (needs numpy)

# Collect data files from packages
datas = []
datas += collect_data_files('uvicorn', include_py_files=True)

# Package metadata required by pydantic_ai (it checks versions at import time)
datas += copy_metadata('pydantic_ai')
datas += copy_metadata('pydantic_ai_slim')  # Core pydantic_ai package
datas += copy_metadata('genai_prices')       # Pricing info for AI models
datas += copy_metadata('httpx')
datas += copy_metadata('openai')

# Include frontend build files
if frontend_dist.exists():
    datas.append((str(frontend_dist), 'claude-flow-board/dist'))
else:
    print("WARNING: Frontend not built! Run 'npm run build' in claude-flow-board/")

a = Analysis(
    ['desktop_app.py'],
    pathex=[str(spec_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],  # Don't include binaries/zipfiles/datas here for onedir mode
    exclude_binaries=True,  # Use onedir mode (recommended for macOS)
    name='claude-flow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(spec_root / 'icon.icns'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='claude-flow',
)

# macOS app bundle
app = BUNDLE(
    coll,  # Use collected files for onedir mode
    name='Claude Flow.app',
    icon=str(spec_root / 'icon.icns'),
    bundle_identifier='com.albertsikkema.claude-flow',
    info_plist={
        'NSPrincipalClass': 'NSApplication',  # Required for Finder launches
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'CFBundleShortVersionString': VERSION,
    },
)
