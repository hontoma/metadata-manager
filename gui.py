import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import csv
import os
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from processing import MetadataManager

#画像解析アプリケーションのGUIを作成するクラス
class ImageAnalyzerApp(TkinterDnD.Tk):
    def __init__(self, analyzer):
        super().__init__()
        self.title("Image Analyzer")
        self.geometry("800x600")
        self.configure(bg="#f0f0f0")
        self.analyzer = analyzer
        self.create_widgets()
        self.metadata_manager = MetadataManager()

    #ウィジェットを定義し作成するメソッド
    def create_widgets(self):
        # ドロップエリアの設定
        self.drop_area = tk.Frame(self, bg="#e0e0e0", width=700, height=100, relief="groove", bd=2)
        self.drop_area.pack(pady=20, padx=20, fill=tk.X)
        self.drop_area.pack_propagate(False)
        self.drop_label = tk.Label(self.drop_area, text="画像ファイルをここにドロップしてください", bg="#e0e0e0", font=("Arial", 12))
        self.drop_label.pack(expand=True)
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind('<<Drop>>', self.drop)
        self.drop_area.bind("<Enter>", self.on_enter)
        self.drop_area.bind("<Leave>", self.on_leave)

        # メタデータ表示エリア
        self.metadata_frame = tk.Frame(self, bg="#ffffff", relief="sunken", bd=1)
        self.metadata_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        self.metadata_text = tk.Text(self.metadata_frame, height=9, width=80, font=("Arial", 10), wrap=tk.WORD)
        self.metadata_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.metadata_scrollbar = tk.Scrollbar(self.metadata_frame, command=self.metadata_text.yview)
        self.metadata_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.metadata_text.config(yscrollcommand=self.metadata_scrollbar.set)

        # BLIP-2解析データ表示エリア
        self.result_frame = tk.Frame(self, bg="#ffffff", relief="sunken", bd=1)
        self.result_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        self.result_text = tk.Text(self.result_frame, height=9, width=80, font=("Arial", 10), wrap=tk.WORD)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.scrollbar = tk.Scrollbar(self.result_frame, command=self.result_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=self.scrollbar.set)

        # ステータスフレームの設定
        self.status_frame = tk.Frame(self, bg="#f0f0f0")
        self.status_frame.pack(fill=tk.X, padx=20, pady=5)
        self.status_label = tk.Label(self.status_frame, text="", bg="#f0f0f0", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT)

        # ボタンフレームの設定
        self.button_frame = tk.Frame(self, bg="#f0f0f0")
        self.button_frame.pack(pady=10)
        self.analyze_button = tk.Button(self.button_frame, text="BLIP-2で解析", command=self.analyze_with_blip, bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5)
        self.analyze_button.pack(side=tk.LEFT, padx=10)
        self.write_button = tk.Button(self.button_frame, text="解析データを画像に保存", command=self.write_analysis_data_to_image, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5)
        self.write_button.pack(side=tk.LEFT, padx=10)
        self.save_metadata_button = tk.Button(self.button_frame, text="メタデータをCSVファイルに保存", command=self.save_metadata_to_csv, bg="#FF9800", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5)
        self.save_metadata_button.pack(side=tk.LEFT, padx=10)
        self.discard_button = tk.Button(self.button_frame, text="破棄", command=self.discard, bg="#f44336", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5)
        self.discard_button.pack(side=tk.LEFT, padx=10)

    #ドロップエリアのマウスオーバー時のイベント
    def on_enter(self, event):
        self.drop_area.config(bg="#d0d0d0")
        self.drop_label.config(bg="#d0d0d0")

    #ドロップエリアからマウスが離れた時のイベント
    def on_leave(self, event):
        self.drop_area.config(bg="#e0e0e0")
        self.drop_label.config(bg="#e0e0e0")

    #画像ファイルをドロップした時のイベント
    def drop(self, event):
        file_path = event.data.strip("{}")
        self.current_file_name = os.path.basename(file_path)
        self.current_file_path = file_path
        if file_path.lower().endswith(('.png', '.webp')):
            self.read_and_display_metadata(file_path)
            self.update_status("画像をドロップしました。BLIP-2で解析ボタンを押して分析を開始してください。")
        else:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "サポートされていないファイル形式です。画像ファイルをドロップしてください。")
            self.current_file_path = None
            self.current_caption = None
            self.update_status("エラー: サポートされていないファイル形式")

    #BLIP-2で画像を解析するメソッド
    def analyze_with_blip(self):
        if self.current_file_path:
            self.update_status("BLIP-2モデルをロード中...")
            
            # threading.Threadを使用して、ロードと解析を別スレッドで実行
            thread = threading.Thread(target=self.run_blip_analysis)
            thread.start()
        else:
            self.update_status("分析する画像がありません")

    #BLIP-2のロードと解析を行うメソッド
    def run_blip_analysis(self):
        self.analyzer.load_model()  # メインスレッドをブロックしないように、別スレッドでロード
        self.result_text.insert(tk.END, "\n画像を分析中...\n")
        result = self.analyzer.analyze_image(self.current_file_path)
        self.result_text.insert(tk.END, result + "\n")
        self.current_caption = result.split(": ", 1)[1]
        self.update_status("BLIP-2による画像分析が完了しました")

    #メタデータを読み込み、表示するメソッド
    def read_and_display_metadata(self, file_path):
        try:
            metadata = self.metadata_manager.read_metadata(file_path)
            self.metadata_text.delete(1.0, tk.END)
            self.metadata_text.insert(tk.END, "既存のメタデータ:\n")
            for key, value in metadata.items():
                self.metadata_text.insert(tk.END, f"{key}:\n{value}\n\n")
            self.current_metadata = metadata
            self.update_status("メタデータを読み込みました")
        except Exception as e:
            self.metadata_text.insert(tk.END, f"\n\nメタデータの読み込みに失敗しました: {str(e)}")
            self.current_metadata = None
            self.update_status("エラー: メタデータの読み込みに失敗")

    #解析データを画像のメタデータに書き込むメソッド
    def write_analysis_data_to_image(self):
        if self.current_file_path and self.current_caption:
            try:
                # 既存のメタデータを読み込む
                metadata = self.metadata_manager.read_metadata(self.current_file_path)

                # 解析データを既存のプロンプトの最後に追加
                if "parameters" in metadata:
                    metadata["parameters"] += f"\n\nBLIP-2 description: {self.current_caption}"
                if "Exif UserComment" in metadata:
                    metadata["Exif UserComment"] += f"\n\nBLIP-2 description: {self.current_caption}"
                if "ImageDescription" in metadata:
                    metadata["ImageDescription"] += f"\n\nBLIP-2 description: {self.current_caption}"

                # 更新されたメタデータを書き込む
                self.write_metadata(self.current_file_path, metadata)

                self.result_text.insert(tk.END, "\n\n解析データをメタデータに書き込みました。")
                self.update_status("解析データをメタデータに書き込みました")
            except Exception as e:
                self.result_text.insert(tk.END, f"\n\nメタデータの書き込みに失敗しました: {str(e)}")
                self.update_status("エラー: メタデータの書き込みに失敗")
        else:
            self.result_text.insert(tk.END, "\n\n画像が選択されていないか、キャプションが生成されていません。")
            self.update_status("エラー: 画像またはキャプションがありません")

    #メタデータを画像に書き込むメソッド
    def write_metadata(self, file_path, metadata):
        ext = file_path.lower().split(".")[-1]
        img = Image.open(file_path)

        if ext == "png":
            png_info = PngInfo()
            for key, value in img.info.items():
                if isinstance(value, str):
                    png_info.add_text(key, value)
            # parametersに追記する
            if "parameters" in metadata:
                png_info.add_text("parameters", metadata["parameters"])
            img.save(file_path, pnginfo=png_info)
        elif ext == "webp":
            # Exif UserCommentの値をdescriptionに書き込む
            img.save(
                file_path, description=metadata.get("Exif UserComment", "")
            )
        else:
            raise ValueError("Unsupported file format")

    #メタデータをCSVファイルに保存するメソッド
    def save_metadata_to_csv(self):
        if self.current_metadata and self.current_file_name:
            output_file = "G:/マイドライブ/sd関連データ/styles.csv"
            metadata_text = self.current_metadata.get('parameters', '') or self.current_metadata.get('Exif UserComment', '')
            positive_prompt, negative_prompt = self.metadata_manager.extract_prompts(metadata_text)
            with open(output_file, "a", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([f"<過去作>{self.current_file_name}", positive_prompt, negative_prompt, self.current_caption])
            self.update_status(f"テキスト情報を {output_file} に追記しました")
        else:
            self.update_status("保存するメタデータがありません")

    #分析結果を破棄するメソッド
    def discard(self):
        self.current_file_path = None
        self.current_caption = None
        self.current_metadata = None
        self.current_file_name = None
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "分析結果を破棄しました。新しい画像をドロップしてください。")
        self.update_status("分析結果を破棄しました")

    #ステータスラベルを更新するメソッド
    def update_status(self, message):
        self.status_label.config(text=message)