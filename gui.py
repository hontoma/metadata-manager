import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import os
from processing import MetadataManager

class ImageAnalyzerApp(TkinterDnD.Tk):
    """画像解析アプリケーションのGUIを作成するクラス"""
    def __init__(self, analyzer):
        super().__init__()
        self.title("Image Analyzer")
        self.geometry("800x600")
        self.configure(bg="#f0f0f0")
        self.analyzer = analyzer
        self.create_widgets()
        self.metadata_manager = MetadataManager()

    def create_widgets(self):
        """ウィジェットを定義し作成するメソッド"""
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
        self.write_button = tk.Button(self.button_frame, text="解析データを画像に保存", command=self.add_blip_caption_to_metadata, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5)
        self.write_button.pack(side=tk.LEFT, padx=10)
        self.save_metadata_button = tk.Button(self.button_frame, text="メタデータをCSVファイルに保存", command=self.save_metadata_to_csv, bg="#FF9800", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5)
        self.save_metadata_button.pack(side=tk.LEFT, padx=10)
        self.discard_button = tk.Button(self.button_frame, text="破棄", command=self.discard, bg="#f44336", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5)
        self.discard_button.pack(side=tk.LEFT, padx=10)

    def on_enter(self, event):
        """ドロップエリアのマウスオーバー時のイベント"""
        self.drop_area.config(bg="#d0d0d0")
        self.drop_label.config(bg="#d0d0d0")
    
    def on_leave(self, event):
        """ドロップエリアからマウスが離れた時のイベント"""
        self.drop_area.config(bg="#e0e0e0")
        self.drop_label.config(bg="#e0e0e0")

    def drop(self, event):
        """画像ファイルをドロップした時のイベント"""
        file_path = event.data.strip("{}")
        self.current_file_name = os.path.basename(file_path)
        self.current_file_path = file_path
        if file_path.lower().endswith(('.png', '.webp')):
            self.display_metadata(file_path)
            self.update_status("画像をドロップしました。BLIP-2で解析ボタンを押して分析を開始してください。")
        else:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "サポートされていないファイル形式です。画像ファイルをドロップしてください。")
            self.current_file_path = None
            self.current_caption = None
            self.update_status("エラー: サポートされていないファイル形式")

    def analyze_with_blip(self):
        """BLIP-2で画像を解析するメソッド"""
        if self.current_file_path:
            self.update_status("BLIP-2モデルをロード中...")
            
            # threading.Threadを使用して、ロードと解析を別スレッドで実行
            thread = threading.Thread(target=self.run_blip_analysis)
            thread.start()
        else:
            self.update_status("分析する画像がありません")

    def run_blip_analysis(self):
        """BLIP-2のロードと解析を行うメソッド"""
        self.analyzer.load_model()  # メインスレッドをブロックしないように、別スレッドでロード
        self.result_text.insert(tk.END, "\n画像を分析中...\n")
        result = self.analyzer.analyze_image(self.current_file_path)
        self.result_text.insert(tk.END, result + "\n")
        self.current_caption = result.split(": ", 1)[1]
        self.update_status("BLIP-2による画像分析が完了しました")

    def display_metadata(self, file_path):
        """read_metadataメソッドからの戻り値であるメタデータを表示するメソッド"""
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

    def add_blip_caption_to_metadata(self):
        """解析データを画像のメタデータに追加する"""
        if self.current_file_path and self.current_caption:
            try:
                metadata = self.metadata_manager.read_metadata(self.current_file_path)
                # MetadataManagerクラスのadd_blip_captionメソッドを呼び出す
                metadata = self.metadata_manager.add_blip_caption(metadata, self.current_caption)
                self.metadata_manager.update_image_metadata(self.current_file_path, metadata)

                self.result_text.insert(tk.END, "\n\n解析データをメタデータに書き込みました。")
                self.update_status("解析データをメタデータに書き込みました")
            except Exception as e:
                self.result_text.insert(tk.END, f"\n\nメタデータの書き込みに失敗しました: {str(e)}")
                self.update_status("エラー: メタデータの書き込みに失敗")
        else:
            self.result_text.insert(tk.END, "\n\n画像が選択されていないか、キャプションが生成されていません。")
            self.update_status("エラー: 画像またはキャプションがありません")

    def save_metadata_to_csv(self):
        """メタデータをCSVファイルに保存するメソッド"""
        if self.current_metadata and self.current_file_name:
            # MetadataManagerクラスのsave_metadata_to_csvメソッドを呼び出す
            self.metadata_manager.save_metadata_to_csv(self.current_metadata, self.current_file_name, self.current_caption)
            self.update_status(f"テキスト情報を styles.csv に追記しました")
        else:
            self.update_status("保存するメタデータがありません")

    def discard(self):
        """分析結果を破棄するメソッド"""
        self.current_file_path = None
        self.current_caption = None
        self.current_metadata = None
        self.current_file_name = None
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "分析結果を破棄しました。新しい画像をドロップしてください。")
        self.update_status("分析結果を破棄しました")

    def update_status(self, message):
        """ステータスラベルを更新するメソッド"""
        self.status_label.config(text=message)