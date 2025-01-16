import configparser
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
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        taskbar_height = 95
        self.dafault_window_size = f"{int(screen_width/2)}x{screen_height - taskbar_height}+0+0"
        self.geometry(self.dafault_window_size)
        self.title("Metadata Manager for SD webui Image")
        self.configure(bg="#f0f0f0")
        self.analyzer = analyzer
        self.config_data = configparser.ConfigParser()
        self.config_data.read('config.ini')
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

        # メニューバーの設定
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        filemenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=filemenu)
        filemenu.add_command(label="開く", command=self.open_file_dialog)
        filemenu.add_separator()
        filemenu.add_command(label="終了", command=self.quit)

        # 設定メニューを追加
        settingsmenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settingsmenu)
        settingsmenu.add_command(label="設定を開く", command=self.open_settings_window)
        settingsmenu.add_command(label="ヘルプ", command=self.show_help)
        settingsmenu.add_command(label="バージョン情報", command=self.show_version_info)
        settingsmenu.add_command(label="ライセンス情報", command=self.license_info)

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
        self.current_file_frame.columnconfigure(0, weight=1)
        self.current_file_path_text = tk.Label(self.current_file_frame, text="画像が選択されていません", font=("Yu Gothic UI", 12), bg="lightgrey", wraplength=700, anchor="w")
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
        self.prompt_label = tk.Label(self.metadata_frame, text="プロンプト（編集可）", font=("Yu Gothic UI", 12), bg="#ffffff")
        self.prompt_label.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=5)
        self.prompt_text = tk.Text(self.metadata_frame, height=5, font=("Yu Gothic UI", 11), wrap=tk.WORD)
        self.prompt_text.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
        self.prompt_text_scrollbar = tk.Scrollbar(self.metadata_frame, command=self.prompt_text.yview)
        self.prompt_text_scrollbar.grid(row=1, column=2, sticky=tk.NS)
        self.prompt_text.config(yscrollcommand=self.prompt_text_scrollbar.set)

        # ネガティブプロンプトエリア
        self.negative_prompt_label = tk.Label(self.metadata_frame, text="ネガティブプロンプト（編集可）", font=("Yu Gothic UI", 12), bg="#ffffff")
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
        self.result_frame = tk.LabelFrame(main_frame, text="BLIP-2解析結果（編集可）", font=("Yu Gothic UI", 12), bg="#ffffff", relief="sunken", bd=1)
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
        self.write_button = tk.Button(self.button_frame, text="データを画像に保存", command=self.add_blip_caption_to_metadata, bg="#4CAF50", fg="white", font=("Yu Gothic UI", 11, "bold"), padx=20, pady=5)
        self.write_button.pack(side=tk.LEFT, padx=10)
        self.save_metadata_button = tk.Button(self.button_frame, text="データをCSVに保存", command=self.save_metadata_to_csv, bg="#FF9800", fg="white", font=("Yu Gothic UI", 11, "bold"), padx=20, pady=5)
        self.save_metadata_button.pack(side=tk.LEFT, padx=10)
        self.discard_button = tk.Button(self.button_frame, text="編集内容を破棄", command=self.discard, bg="#f44336", fg="white", font=("Yu Gothic UI", 11, "bold"), padx=20, pady=5)
        self.discard_button.pack(side=tk.LEFT, padx=10)
        self.remove_personal_data_button = tk.Button(self.button_frame, text="情報を削除したコピーの作成", command=self.remove_personal_data, bg="#b00020", fg="white", font=("Yu Gothic UI", 11, "bold"), padx=20, pady=5)
        self.remove_personal_data_button.pack(side=tk.LEFT, padx=10)

        # ステータスフレームの設定
        self.status_frame = tk.Frame(self, bg="#f0f0f0")
        self.status_frame.pack(fill=tk.X, padx=20, pady=5)
        self.progressbar = ttk.Progressbar(self.status_frame, orient="horizontal", mode="determinate")
        self.status_label = tk.Label(self.status_frame, text="ファイルを選択してください", bg="#f0f0f0", font=("Yu Gothic UI", 13), wraplength=self.winfo_screenwidth() / 2- 110, anchor="w")
        self.status_label.pack(side=tk.LEFT)
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
            filetypes=[("画像ファイル", "*.png *.webp"), ("すべてのファイル", "*.*")],
            initialdir="./",  # 初期ディレクトリを指定
            title="画像ファイルを選択"
        )
        if file_path:
            self.current_file_name = os.path.basename(file_path)
            self.current_file_path = file_path
            self.display_metadata(file_path)
            self.update_status("画像ファイルの情報を表示しました。Blip-2での解析やメタデータを編集することが可能です。")
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
            self.update_status("画像ファイルの情報を表示しました。Blip-2での解析やメタデータを編集することが可能です。")
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
            result = self.metadata_manager.save_metadata_to_csv(edited_prompt_text, edited_negative_prompt_text, self.current_file_name, edited_caption)
            if result:
                self.update_status(f"指定されたCSVファイルへの追記が完了しました", status_type="success")
            elif not result:
                self.update_status("書き込み先が不明です。設定を確認してください", status_type="error")
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

    def remove_personal_data(self):
        """画像から個人情報を削除したコピーを作成するメソッド"""
        if self.current_file_path:
            try:
                # MetadataManagerクラスのremove_personal_dataメソッドを呼び出す
                desktop_path, new_image_name = self.metadata_manager.remove_personal_data(self.current_file_path, self.current_file_name)

                self.update_status(f"情報を削除したコピー{new_image_name}を{desktop_path}に作成しました", status_type="success")
            except Exception as e:
                self.update_status(f"エラー: コピーの作成に失敗しました: {str(e)}", status_type="error")
        else:
            self.update_status("エラー: 画像ファイルが選択されていません", status_type="error")

    def update_status(self, message, status_type="normal"):
        """ステータス表示を更新するメソッド"""
        status_colors = {
            "normal": "black",
            "processing": "blue",
            "success": "green",
            "error": "red",
        }
        self.status_label.config(text=message, fg=status_colors.get(status_type, "black"))

    def open_settings_window(self):
        """設定画面を開く"""
        self.config_data.read("config.ini")

        self.settings_window = tk.Toplevel(self)
        self.settings_window.title("設定")

        # モーダルウィンドウに設定
        self.settings_window.grab_set()
        self.settings_window.focus_set()
        self.settings_window.geometry(self.dafault_window_size)
        self.settings_window.configure(bg="#f0f0f0")

        # キャンバスとスクロールバーを作成
        canvas = tk.Canvas(self.settings_window, bg="#f0f0f0")
        scrollbar = tk.Scrollbar(self.settings_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")

        scrollable_frame.bind("<Configure>",lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # フレームを作成
        frame = tk.Frame(scrollable_frame, bg="#f0f0f0")
        frame.pack(padx=20, pady=20)

        # 設定項目
        # csvファイルのパスの指定
        csv_label = tk.Label(frame, text="CSVの保存先:", bg="#f0f0f0", font=("Yu Gothic UI", 14))
        csv_label.grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        self.csv_file_path = tk.Label(frame, text=self.config_data.get("DEFAULT", "csv_path"), bg="#ffffff", font=("Yu Gothic UI", 14), relief="sunken", anchor="w")
        self.csv_file_path.grid(row=0, column=1, padx=5, pady=10, sticky=tk.EW)
        csv_button = tk.Button(frame, text="変更", command=self.select_csv_file, bg="#2196F3", fg="white", font=("Yu Gothic UI", 14, "bold"), width=10)
        csv_button.grid(row=0, column=2, padx=5, pady=10)

        # コピーの保存場所の設定
        image_label = tk.Label(frame, text="画像の保存場所:", bg="#f0f0f0", font=("Yu Gothic UI", 14))
        image_label.grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        self.image_save_path = tk.Label(frame, text=self.config_data.get("DEFAULT", "clone_save_path"), bg="#ffffff", font=("Yu Gothic UI", 14), relief="sunken", anchor="w")
        self.image_save_path.grid(row=1, column=1, padx=5, pady=10, sticky=tk.EW)
        image_button = tk.Button(frame, text="変更", command=self.select_image_save_path, bg="#2196F3", fg="white", font=("Yu Gothic UI", 14, "bold"), width=10)
        image_button.grid(row=1, column=2, padx=5, pady=10)

        # キャプションの追加位置の選択
        position_label = tk.Label(frame, text="解析結果の追加位置:", bg="#f0f0f0", font=("Yu Gothic UI", 14))
        position_label.grid(row=2, column=0, padx=5, pady=10, sticky=tk.W)
        self.caption_position = tk.StringVar(frame, self.config_data.get("DEFAULT", "caption_position"))
        position_option = tk.OptionMenu(frame, self.caption_position, "TOP", "BOTTOM")
        position_option.config(bg="#ffffff", font=("Yu Gothic UI", 14))
        position_option.grid(row=2, column=1, padx=5, pady=10, sticky=tk.EW)

        # csvファイル保存時にファイル名をキャプションで置き換えるかの設定
        replace_label = tk.Label(frame, text="CSV保存時にタイトルを解析結果に置き換え:", bg="#f0f0f0", font=("Yu Gothic UI", 14), wraplength=150)
        replace_label.grid(row=3, column=0, padx=5, pady=10, sticky=tk.W)
        self.replace_caption = tk.BooleanVar(frame, self.config_data.getboolean("DEFAULT", "replace_caption"))
        replace_checkbutton = tk.Checkbutton(frame, variable=self.replace_caption, bg="#ffffff", font=("Yu Gothic UI", 14))
        replace_checkbutton.grid(row=3, column=1, padx=5, pady=10)

        # csvのタイトルに付けるprefixの設定
        prefix_label = tk.Label(frame, text="CSV保存時のタイトルの接頭辞:", bg="#f0f0f0", font=("Yu Gothic UI", 14), wraplength=150)
        prefix_label.grid(row=4, column=0, padx=5, pady=10, sticky=tk.W)
        self.prefix_word = tk.StringVar(frame, self.config_data.get("DEFAULT", "csv_title_prefix"))
        self.prefix = tk.Entry(frame, width=30, font=("Yu Gothic UI", 14), textvariable=self.prefix_word)
        self.prefix.grid(row=4, column=1, padx=5, pady=10, sticky=tk.EW)

        # ボタンフレーム
        button_frame = tk.Frame(scrollable_frame, bg="#f0f0f0")
        button_frame.pack(pady=20)

        # OKボタン
        ok_button = tk.Button(button_frame, text="設定を保存", command=self.save_settings, bg="#4CAF50", fg="white", font=("Yu Gothic UI", 14, "bold"), width=15)
        ok_button.pack(side=tk.LEFT, padx=10)

        # Cancelボタン
        cancel_button = tk.Button(button_frame, text="キャンセル", command=self.settings_discard, bg="#f44336", fg="white", font=("Yu Gothic UI", 14, "bold"), width=15)
        cancel_button.pack(side=tk.LEFT, padx=10)

        # キャンバスとスクロールバーを配置
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Configure grid weights
        frame.grid_columnconfigure(1, weight=1)

    def save_settings(self):
        """設定値を保存する"""
        # 設定値を取得
        csv_path = self.csv_file_path.cget("text")
        image_save_path = self.image_save_path.cget("text")
        caption_position = self.caption_position.get()
        replace_caption = self.replace_caption.get()
        csv_title_prefix = self.prefix.get()


        # 設定値を保存（configparserを使用）
        self.config_data['DEFAULT'] = {
            'csv_path': csv_path,
            'clone_save_path': image_save_path,
            'caption_position': caption_position,
            'replace_caption': str(replace_caption).lower(),
            'csv_title_prefix': csv_title_prefix,
            
        }
        with open('config.ini', 'w') as configfile:
            self.config_data.write(configfile)

        # 設定画面を閉じる
        self.settings_window.grab_release()
        self.settings_window.destroy()
        self.update_status("設定を保存しました")

    def settings_discard(self):
        """設定変更を破棄する"""
        self.settings_window.grab_release()
        self.settings_window.destroy()
        self.update_status("設定の変更を破棄しました")

    def select_csv_file(self):
        """CSVファイルをファイラーで選択する"""
        new_file_path = filedialog.askopenfilename(
            initialdir="/",
            title="CSVファイルを選択",
            filetypes=(("CSV files", "*.csv"), ("all files", "*.*"))
        )
        if new_file_path:
            # 選択されたファイルパスを表示
            self.csv_file_path.config(text=new_file_path)
    
    def select_image_save_path(self):
        """画像保存先をフォルダパスで選択する"""
        new_folder_path = filedialog.askdirectory(
            initialdir="/",
            title="画像を保存するフォルダを選択"
        )
        if new_folder_path:
            # 選択されたフォルダパスを表示
            self.image_save_path.config(text=new_folder_path)
    
    def license_info(self):
        """ライセンス情報を表示するメソッド"""
        license_window = tk.Toplevel(self)
        license_window.title("ライセンス情報")
        license_window.geometry("600x400")

        # スクロール可能なテキストウィジェットを作成
        license_text = tk.Text(license_window, wrap=tk.WORD, padx=10, pady=10)
        license_text.pack(expand=True, fill=tk.BOTH)

        # スクロールバーを追加
        scrollbar = tk.Scrollbar(license_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        license_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=license_text.yview)

        try:
            # licenses.txtファイルからライセンス情報を読み込む
            with open('licenses.txt', 'r', encoding='utf-8') as file:
                license_content = file.read()
            
            # ライセンス情報をテキストウィジェットに挿入
            license_text.insert(tk.END, license_content)
        except FileNotFoundError:
            license_text.insert(tk.END, "ライセンス情報ファイルが見つかりません。")
        except Exception as e:
            license_text.insert(tk.END, f"ライセンス情報の読み込み中にエラーが発生しました: {str(e)}")

        # テキストウィジェットを読み取り専用に設定
        license_text.config(state=tk.DISABLED)

    def show_help(self):
        """ヘルプ情報を表示するメソッド"""
        with open('help.txt', 'r', encoding='utf-8') as file:
            help_text = file.read()
        
        help_window = tk.Toplevel(self)
        help_window.title("ヘルプ")
        help_window.geometry("600x400")
        
        text_widget = tk.Text(help_window, wrap=tk.WORD, font=("Yu Gothic UI", 10))
        text_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)  # 読み取り専用に設定
        
        scrollbar = tk.Scrollbar(text_widget)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_widget.yview)

    def show_version_info(self):
        """バージョン情報を表示するメソッド"""
        try:
            with open('version.txt', 'r', encoding="utf-8") as file:
                description = file.read().strip()
            messagebox.showinfo("バージョン情報", description)
        except FileNotFoundError:
            messagebox.showerror("エラー", "version.txt ファイルが見つかりません。")
        except Exception as e:
            messagebox.showerror("エラー", f"バージョン情報の読み込み中にエラーが発生しました: {str(e)}")