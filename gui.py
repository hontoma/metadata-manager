import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import os
from processing import MetadataManager
from tkinter import messagebox, filedialog
from tkinter import ttk

class ImageAnalyzerApp(TkinterDnD.Tk):
    """画像解析アプリケーションのGUIを作成するクラス"""
    def __init__(self, analyzer):
        super().__init__()
        self.state("zoomed")
        self.title("Metadata Manager for SD webui Image")
        self.configure(bg="#f0f0f0")
        self.analyzer = analyzer
        self.create_widgets()
        self.metadata_manager = MetadataManager()
        # 画像のファイルパス及びファイル名
        self.current_file_name = None
        self.current_file_path = None
        #解析中の確認用変数
        self.is_analyzing = False
        # blip-2での分析結果
        self.original_caption = None

    def create_widgets(self):
        """ウィジェットを定義し作成するメソッド"""

        # メインフレーム
        main_frame = tk.Frame(self, bg="#f0f0f0")
        main_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        # ドロップエリアの設定
        self.drop_area = tk.Frame(main_frame, bg="#e0e0e0", width=700, height=100, relief="groove", bd=2)
        self.drop_area.pack(pady=10, padx=20, fill=tk.X)
        self.drop_area.pack_propagate(False)
        self.drop_label = tk.Label(self.drop_area, text="画像ファイルをここにドロップするかクリックして選択してください", bg="#e0e0e0", font=("Yu Gothic UI", 14))
        self.drop_label.pack(expand=True)
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind('<<Drop>>', self.drop)
        self.drop_area.bind("<Enter>", self.on_enter)
        self.drop_area.bind("<Leave>", self.on_leave)
        self.drop_area.bind("<Button-1>", self.open_file_dialog)

        # 処理中の画像のファイルパスの表示
        self.current_file_frame = tk.LabelFrame(main_frame, text="現在の画像", font=("Yu Gothic UI", 12), bg="#ffffff", relief="sunken", bd=1)
        self.current_file_frame.pack(pady=10, padx=20, fill=tk.X)
        self.current_file_path_text = tk.Label(self.current_file_frame, text="画像が選択されていません", font=("Yu Gothic UI", 12), bg="lightgrey", wraplength=800)
        self.current_file_path_text.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=5)
        
        # ファイルを開くボタン
        self.open_file_path_button = tk.Button(self.current_file_frame, text="画像を表示", command=self.open_file_path, font=("Yu Gothic UI", 12), padx=10, pady=5, state=tk.DISABLED)
        self.open_file_path_button.grid(row=0, column=1, sticky=tk.E, padx=5, pady=5)

        # メタデータ表示エリア
        self.metadata_frame = tk.LabelFrame(main_frame, text="メタデータ", font=("Yu Gothic UI", 12), bg="#ffffff", relief="sunken", bd=1)
        self.metadata_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        self.metadata_frame.columnconfigure(1, weight=1)
        for i in range(6):
            self.metadata_frame.rowconfigure(i, weight=1)

        # プロンプトエリア
        self.prompt_label = tk.Label(self.metadata_frame, text="プロンプト", font=("Yu Gothic UI", 12), bg="#ffffff")
        self.prompt_label.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=5)
        self.prompt_text = tk.Text(self.metadata_frame, height=5, font=("Yu Gothic UI", 11), wrap=tk.WORD)
        self.prompt_text.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
        self.prompt_text_scrollbar = tk.Scrollbar(self.metadata_frame, command=self.prompt_text.yview)
        self.prompt_text_scrollbar.grid(row=1, column=2, sticky=tk.NS)
        self.prompt_text.config(yscrollcommand=self.prompt_text_scrollbar.set)

        # ネガティブプロンプトエリア
        self.negative_prompt_label = tk.Label(self.metadata_frame, text="ネガティブプロンプト", font=("Yu Gothic UI", 12), bg="#ffffff")
        self.negative_prompt_label.grid(row=2, column=0, sticky=tk.EW, padx=5, pady=5)
        self.negative_prompt_text = tk.Text(self.metadata_frame, height=5, font=("Yu Gothic UI", 11), wrap=tk.WORD)
        self.negative_prompt_text.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
        self.negative_prompt_text_scrollbar = tk.Scrollbar(self.metadata_frame, command=self.negative_prompt_text.yview)
        self.negative_prompt_text_scrollbar.grid(row=3, column=2, sticky=tk.NS)
        self.negative_prompt_text.config(yscrollcommand=self.negative_prompt_text_scrollbar.set)

        # その他の情報エリア
        self.others_text_label = tk.Label(self.metadata_frame, text="その他の情報", font=("Yu Gothic UI", 12), bg="#ffffff")
        self.others_text_label.grid(row=4, column=0, sticky=tk.EW, padx=5, pady=5)
        self.others_text = tk.Text(self.metadata_frame, state=tk.DISABLED, height=5, font=("Yu Gothic UI", 10), wrap=tk.WORD, bg="lightgrey")
        self.others_text.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
        self.others_text_scrollbar = tk.Scrollbar(self.metadata_frame, command=self.others_text.yview)
        self.others_text_scrollbar.grid(row=5, column=2, sticky=tk.NS)
        self.others_text.config(yscrollcommand=self.others_text_scrollbar.set)

        # BLIP-2解析データ表示エリア
        self.result_frame = tk.LabelFrame(main_frame, text="BLIP-2解析結果", font=("Yu Gothic UI", 12), bg="#ffffff", relief="sunken", bd=1)
        self.result_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        self.blip2_result = tk.Text(self.result_frame, height=2, width=80, font=("Yu Gothic UI", 11), wrap=tk.WORD)
        self.blip2_result.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.scrollbar = tk.Scrollbar(self.result_frame, command=self.blip2_result.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.blip2_result.config(yscrollcommand=self.scrollbar.set)

        # ボタンフレームの設定
        self.button_frame = tk.Frame(main_frame, bg="#f0f0f0")
        self.button_frame.pack(pady=10)
        self.analyze_button = tk.Button(self.button_frame, text="BLIP-2で解析", command=self.analyze_with_blip, bg="#2196F3", fg="white", font=("Yu Gothic UI", 12, "bold"), padx=20, pady=5)
        self.analyze_button.pack(side=tk.LEFT, padx=10)
        self.write_button = tk.Button(self.button_frame, text="解析データを画像に保存", command=self.add_blip_caption_to_metadata, bg="#4CAF50", fg="white", font=("Yu Gothic UI", 12, "bold"), padx=20, pady=5)
        self.write_button.pack(side=tk.LEFT, padx=10)
        self.save_metadata_button = tk.Button(self.button_frame, text="メタデータをCSVファイルに保存", command=self.save_metadata_to_csv, bg="#FF9800", fg="white", font=("Yu Gothic UI", 12, "bold"), padx=20, pady=5)
        self.save_metadata_button.pack(side=tk.LEFT, padx=10)
        self.discard_button = tk.Button(self.button_frame, text="編集内容を破棄", command=self.discard, bg="#f44336", fg="white", font=("Yu Gothic UI", 12, "bold"), padx=20, pady=5)
        self.discard_button.pack(side=tk.LEFT, padx=10)

        # ステータスフレームの設定
        self.status_frame = tk.Frame(self, bg="#f0f0f0")
        self.status_frame.pack(fill=tk.X, padx=20, pady=5)
        self.status_label = tk.Label(self.status_frame, text="", bg="#f0f0f0", font=("Yu Gothic UI", 12))
        self.status_label.pack(side=tk.LEFT)
        self.progressbar = ttk.Progressbar(self.status_frame, orient="horizontal", mode="determinate")
        self.progressbar.pack(side=tk.RIGHT, fill=tk.X)

    def open_file_path(self):
        """画像を既定のプログラムで開くメソッド"""
        if self.current_file_path:
            try:
                os.startfile(self.current_file_path)
            except Exception as e:
                self.update_status(f"エラー: {str(e)}", status_type="error")
                messagebox.showerror("エラー", f"画像を開く際にエラーが発生しました: {str(e)}")

    def open_file_dialog(self, event=None):
        """ファイル選択ダイアログを開くメソッド"""

        # 処理中の場合の無効化
        if self.is_analyzing:
            messagebox.showwarning("警告", "現在、画像の解析中のため実行できません。")
            return

        file_path = filedialog.askopenfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("WEBP files", "*.webp")],
            initialdir="./",  # 初期ディレクトリを指定
            title="画像ファイルを選択"
        )
        if file_path:
            self.current_file_name = os.path.basename(file_path)
            self.current_file_path = file_path
            self.display_metadata(file_path)
            self.update_status("画像ファイルを選択しました。BLIP-2で解析ボタンを押して分析を開始してください。")
            self.current_file_path_text.config(text=self.current_file_path)
            self.open_file_path_button.config(state=tk.NORMAL)

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
        # 処理中の場合の無効化
        if self.is_analyzing:
            messagebox.showwarning("警告", "現在、画像の解析中のため実行できません。")
            return
        
        file_path = event.data.strip("{}")
        self.current_file_name = os.path.basename(file_path)
        self.current_file_path = file_path
        if file_path.lower().endswith(('.png', '.webp')):
            self.display_metadata(file_path)
            self.update_status("画像をドロップしました。BLIP-2で解析ボタンを押して分析を開始してください。")
            self.current_file_path_text.config(text=self.current_file_path)
            self.open_file_path_button.config(state=tk.NORMAL)
        else:
            self.update_status("サポートされていないファイル形式です。png及びwebp拡張子のみ対応しています。",status_type="error")
            self.current_file_path = None
            self.original_caption = None

    def analyze_with_blip(self):
        """BLIP-2で画像を解析するメソッド"""
        if self.is_analyzing:
            messagebox.showwarning("警告", "現在、画像の解析中のため実行できません。")
            return

        # 解析前にresult textを初期化
        self.blip2_result.delete(1.0, tk.END)

        if self.current_file_path:
            # 解析中フラグを設定し、ボタンをDISABLEDにする
            self.is_analyzing = True 
            self.analyze_button.config(state=tk.DISABLED)
            self.write_button.config(state=tk.DISABLED)
            self.save_metadata_button.config(state=tk.DISABLED)
            self.discard_button.config(state=tk.DISABLED)

            self.update_status("BLIP-2モデルをロード中...",status_type="processing")
            self.progressbar.start() 
            
            # threading.Threadを使用して、ロードと解析を別スレッドで実行
            thread = threading.Thread(target=self.run_blip_analysis)
            thread.start()
        else:
            self.update_status("分析する画像がありません",status_type="error")

    def run_blip_analysis(self):
        """BLIP-2のロードと解析を行うメソッド"""
        self.analyzer.load_model()  # メインスレッドをブロックしないように、別スレッドでロード
        self.update_status("画像を分析中...", status_type="processing")

        result = self.analyzer.analyze_image(self.current_file_path)
        self.blip2_result.insert(tk.END, result)
        self.original_caption = result
        self.update_status("BLIP-2による画像分析が完了しました", status_type="success")
        self.progressbar.stop()

        # 解析完了後のフラグ処理とボタンの有効化
        self.is_analyzing = False  # 解析中フラグをFalseに設定
        self.analyze_button.config(state=tk.NORMAL)
        self.write_button.config(state=tk.NORMAL)
        self.save_metadata_button.config(state=tk.NORMAL)
        self.discard_button.config(state=tk.NORMAL)

    def display_metadata(self, file_path):
        """read_metadataメソッドからの戻り値であるメタデータを表示するメソッド"""
        try:
            metadata = self.metadata_manager.read_metadata(file_path)
            # extract_promptsメソッドを使ってプロンプトを分割
            positive_prompt, negative_prompt, others = self.metadata_manager.extract_prompts(metadata.get("parameters", ""))

            self.prompt_text.delete(1.0, tk.END)
            self.prompt_text.insert(tk.END, positive_prompt)

            self.negative_prompt_text.delete(1.0, tk.END)
            self.negative_prompt_text.insert(tk.END, negative_prompt)

            self.others_text.config(state=tk.NORMAL)
            self.others_text.delete(1.0, tk.END)
            self.others_text.insert(tk.END, others)
            self.others_text.config(state=tk.DISABLED)

            self.blip2_result.delete(1.0, tk.END)

            self.original_prompt = positive_prompt
            self.original_negative_prompt = negative_prompt
            self.update_status("メタデータを読み込みに成功しました",status_type="success")
        except Exception as e:
            self.prompt_text.insert(tk.END, f"\n\nメタデータの読み込みに失敗しました: {str(e)}")
            self.original_prompt,self.original_negative_prompt, self.others_text = None
            self.update_status("エラー: メタデータの読み込みに失敗しました", status_type="error")

    def add_blip_caption_to_metadata(self):
        """解析データを画像のメタデータに追加する"""
        if self.current_file_path and self.original_caption:
            try:
                # 編集したメタデータの取得
                edited_prompt_text = self.prompt_text.get("1.0","end-1c")
                edited_negative_prompt_text = self.negative_prompt_text.get("1.0","end-1c")
                others_text= self.others_text.get("1.0","end-1c")
                edited_caption = self.blip2_result.get("1.0","end-1c")

                # MetadataManagerクラスのadd_blip_captionメソッドを呼び出す
                metadata = self.metadata_manager.add_blip_caption(edited_prompt_text, edited_negative_prompt_text, others_text, edited_caption)
                self.metadata_manager.update_image_metadata(self.current_file_path, metadata)

                self.update_status("メタデータへの書き込みが完了しました", status_type="success")
            except Exception as e:
                self.update_status(f"エラー: メタデータへの書き込みに失敗しました: {str(e)}", status_type="error")
        else:
            self.update_status("エラー: 画像またはキャプションがありません", status_type="error")

    def save_metadata_to_csv(self):
        """メタデータをCSVファイルに保存するメソッド"""
        if self.current_file_path:

            # 編集したメタデータの取得
            edited_prompt_text = self.prompt_text.get("1.0","end-1c")
            edited_negative_prompt_text = self.negative_prompt_text.get("1.0","end-1c")
            edited_caption = self.blip2_result.get("1.0","end-1c")

            # MetadataManagerクラスのsave_metadata_to_csvメソッドを呼び出す
            self.metadata_manager.save_metadata_to_csv(edited_prompt_text, edited_negative_prompt_text, self.current_file_name, edited_caption)
            self.update_status(f"指定されたCSVファイルへの追記が完了しました", status_type="success")
        else:
            self.update_status("エラー: 保存するメタデータがありません", status_type="error")

    def discard(self):
        """編集状況を破棄するメソッド"""
        self.prompt_text.delete(1.0, tk.END)
        if self.original_prompt:
            self.prompt_text.insert(tk.END, self.original_prompt)

        self.negative_prompt_text.delete(1.0, tk.END)
        if self.original_negative_prompt:
            self.negative_prompt_text.insert(tk.END, self.original_negative_prompt)

        self.blip2_result.delete(1.0, tk.END)
        if self.original_caption:
            self.blip2_result.insert(tk.END, self.original_caption)

        self.update_status("編集中のデータを破棄しました")

    def update_status(self, message, status_type="normal"):
        """ステータス表示を更新するメソッド"""
        status_colors = {
            "normal": "black",
            "processing": "blue",
            "success": "green",
            "error": "red",
        }
        self.status_label.config(text=message, fg=status_colors.get(status_type, "black"))