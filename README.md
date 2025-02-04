# Metadata Manager

Metadata Managerは、画像ファイルのメタデータを管理し、AIを使用して画像の内容を分析するPythonアプリケーションです。

## 機能

- 画像ファイルのメタデータの表示と編集
- AIを使用した画像内容の分析
- 個人情報を削除した画像コピーの作成
- ドラッグ＆ドロップによる簡単な画像ファイル選択

## インストール

1. このリポジトリをクローンします：
   git clone https://github.com/hontma/metadata-manager.git
2. プロジェクトディレクトリに移動します：
   cd metadata-manager
3. 必要な依存関係をインストールします：
   pip install -r requirements.txt
   もしくはcuda対応torchバージョン
   pip install -r requirements_cuda_version.txt

## 使用方法

1. main.pyを実行するとアプリケーションが起動します。   
2. GUIウィンドウが開きます。画像ファイルをドラッグ＆ドロップするか、「ファイルを開く」ボタンをクリックして画像を選択します。
3. メタデータの表示、編集、AIによる分析、個人情報の削除などの必要な機能を使用します。

## 依存関係

主な依存関係は以下の通りです：

- PIL (Pillow)
- OpenCV
- PyTorch
- Transformers
- Tkinter

詳細は `requirements.txt`もしくは`requirements_cuda_version.txt` を参照してください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## コントリビューション

バグ報告や機能リクエストは、GitHubの[Issues](https://github.com/hontoma/metadata-manager/issues)ページにて受け付けています。

プルリクエストも歓迎します。大きな変更を加える場合は、まずissueを開いて議論してください。

## 作者

- hontoma

## 謝辞

このプロジェクトは以下のオープンソースプロジェクトを使用しています：

- [Hugging Face Transformers](https://github.com/huggingface/transformers)
- [PyTorch](https://pytorch.org/)
- [OpenCV](https://opencv.org/)

これらのプロジェクトの開発者の皆様に感謝いたします。