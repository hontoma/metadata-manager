import os

# プロジェクトのルートディレクトリを取得
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# resourcesフォルダのパスを設定
RESOURCES_DIR = os.path.join(ROOT_DIR, 'resources')

# config.iniファイルのパスを設定
CONFIG_FILE = os.path.join(RESOURCES_DIR, 'config.ini')