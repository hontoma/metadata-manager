# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# tkinterdnd2のデータファイルを収集
tkdnd_data = collect_data_files('tkinterdnd2')

# プロジェクトのルートディレクトリを取得
root_dir = SPECPATH

# 追加のデータファイルを指定
resources_dir = os.path.join(root_dir, 'resources')
additional_data = []
for file_name in ['version.txt', 'licenses.txt', 'help.txt']:
    file_path = os.path.join(resources_dir, file_name)
    if os.path.exists(file_path):
        additional_data.append((file_path, 'resources'))
    else:
        print(f"Warning: {file_name} not found in the resources directory.")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=tkdnd_data + additional_data,
    hiddenimports=['tkinterdnd2', 'metadata_manager'],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # コンソールウィンドウを非表示にする
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)