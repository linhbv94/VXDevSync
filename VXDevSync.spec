# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
project_root = Path.cwd()

datas = [
    (str(project_root / "frontend"), "frontend"),
    (str(project_root / "public"), "public"),
    (str(project_root / "icon.png"), "."),
    (str(project_root / "icon.icns"), "."),
]

hiddenimports = [
    "webview",
    "webview.platforms.cocoa",
    "objc",
    "AppKit",
    "WebKit",
    "Foundation",
    "src",
    "src.bridge_api",
    "src.config_manager",
    "src.git_engine",
    "src.skills_engine",
    "src.adapter_engine",
    "src.window_chrome",
]

a = Analysis(
    ["src/main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "scipy", "PIL"],
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
    name="VXDevSync",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "icon.icns"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VXDevSync",
)

app = BUNDLE(
    coll,
    name="VXDevSync.app",
    icon=str(project_root / "icon.icns"),
    bundle_identifier="com.ztools.vxdevsync",
    info_plist={
        "CFBundleName": "VXDevSync",
        "CFBundleDisplayName": "VXDevSync",
        "CFBundleIdentifier": "com.ztools.vxdevsync",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "NSRequiresAquaSystemAppearance": False,
        "CFBundlePackageType": "APPL",
    },
)
