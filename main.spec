# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.building.api import PYZ, EXE, COLLECT

block_cipher = None

# プロジェクトのルートディレクトリを取得
root_dir = SPECPATH

# 仮想環境のパスを指定
home_dir = os.path.expanduser("~")

# cuda対応なしバージョン作成の場合
venv_site_packages = os.path.join(home_dir, '.python_virtualenvs', 'torch_no_cuda', 'Lib', 'site-packages')
# cuda12.4バージョン作成の場合
# venv_site_packages = os.path.join(home_dir, '.python_virtualenvs', 'torch_cuda_124', 'Lib', 'site-packages')

# デスクトップのパスを取得
desktop_path = os.path.expanduser("~/Desktop")

# ビルドとディストリビューションのパスを設定
build_path = os.path.join(desktop_path, 'MetadataManager_build')
dist_path = os.path.join(desktop_path, 'MetadataManager_dist')

# ディレクトリが存在しない場合は作成
os.makedirs(build_path, exist_ok=True)
os.makedirs(dist_path, exist_ok=True)

# tkinterdnd2のデータファイルを収集
tkdnd_data = collect_data_files('tkinterdnd2')

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
    pathex=[venv_site_packages],
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
    workpath=build_path,  # カスタムビルドパスを指定
    distpath=dist_path,   # カスタムディストリビューションパスを指定
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Metadata Manager for SD webui Image',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    distpath=dist_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Metadata Manager for SD webui Image',
    distpath=dist_path,
)