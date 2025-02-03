import configparser
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import os
import win32api
import datetime
from tkinter import font
from tkinter import messagebox, filedialog
from tkinter import ttk
import matplotlib.pyplot as plt

# リソースファイルの読み込み
from .processing import MetadataManager
from resources import get_resource_content
from metadata_manager.config import CONFIG_FILE

class ImageAnalyzerApp(TkinterDnD.Tk):
    """画像解析アプリケーションのGUIを作成するクラス"""
    def __init__(self):
        super().__init__()

        # configファイルの読み込み
        self.config_data = configparser.ConfigParser()
        self.config_data.read(CONFIG_FILE)

        # Matplotlibのフォント設定
        ui_font_name = self.config_data.get('DEFAULT', 'ui_font_name', fallback='Yu Gothic, Meiryo, MS Gothic')
        plt.rcParams['font.family'] = f"{ui_font_name}, sans-serif"
        
        # ImageAnalyzerのインポートと初期化
        try:
            from image_analyzer import ImageAnalyzer
            self.analyzer = ImageAnalyzer(self.config_data)
        except ImportError:
            self.analyzer = None
        
        # windowの初期サイズの決定
        screen_width: int = self.winfo_screenwidth()
        screen_height: int = self.winfo_screenheight()
        taskbar_height: int = self.get_taskbar_height() + 55
        self.dafault_window_size = f"{int(screen_width/2)}x{screen_height - taskbar_height}+0+0"
        self.geometry(self.dafault_window_size)

        # バージョンの確認とタイトル表示
        version_name = "Light version" if self.analyzer is None else "Full version"
        self.title(f"Metadata Manager for SD webui Image {version_name}")

        # フォントの設定
        ui_font = self.config_data.get('DEFAULT', 'ui_font_name', fallback='Yu Gothic UI')
        ui_font_size = self.config_data.get('DEFAULT', 'ui_font_size', fallback=12)
        text_font = self.config_data.get('DEFAULT', 'text_font_name', fallback='Yu Gothic UI')
        text_font_size = self.config_data.get('DEFAULT', 'text_font_size', fallback=14)
        self.text_font = (text_font, int(text_font_size))
        self.ui_font = (ui_font, int(ui_font_size))
        self.configure(bg="#f0f0f0")

        # フォント更新の際に使用するウィジェットの辞書
        self.ui_font_widgets = []
        self.text_font_widgets = []

        # 実体（インスタンス）の作成処理
        self.create_widgets()
        self.metadata_manager = MetadataManager()

        # 終了処理
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 終了処理中の確認フラグ
        self.is_closing: bool = False

        # グラフウィンドウの初期化
        self.graph_window = None

        # 画像のファイルパス及びファイル名
        self.current_file_name = None
        self.current_file_path = None

        # torchロード中の確認フラグ
        self.is_torch_loaded: bool = False
        
        #解析中の確認用変数
        self.is_analyzing: bool = False
        
        # 解析モデルと解析結果テキスト
        self.analysis_model = self.config_data.get('DEFAULT', 'analysis_model', fallback='CLIP')
        self.original_caption = None

    def get_taskbar_height(self):
        """タスクバーの高さを取得するメソッド"""
        monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))
        monitor_area = monitor_info.get("Monitor")
        work_area = monitor_info.get("Work")
        return monitor_area[3] - work_area[3]

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
        self.main_frame = tk.Frame(self, bg="#f0f0f0")
        self.main_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # ドロップエリアの設定
        self.drop_area = tk.Frame(self.main_frame, bg="#e0e0e0", width=700, height=100, relief="groove", bd=2)
        self.drop_area.pack(pady=5, padx=10, fill=tk.X)
        self.drop_area.pack_propagate(False)

        self.drop_label = tk.Label(self.drop_area, text="画像ファイルをここにドロップするかクリックして選択してください", bg="#e0e0e0", font=self.ui_font)
        self.drop_label.pack(expand=True)

        self.register_widget("ui", self.drop_label)
        self.drop_area.drop_target_register(DND_FILES)

        self.drop_area.dnd_bind('<<Drop>>', self.drop)
        self.drop_area.bind("<Enter>", self.on_enter)
        self.drop_area.bind("<Leave>", self.on_leave)
        self.drop_area.bind("<Button-1>", self.open_file_dialog)

        # 処理中の画像のファイルパスの表示
        self.current_file_frame = tk.LabelFrame(self.main_frame, text="現在の画像", font=self.ui_font, bg="#ffffff", relief="sunken", bd=1)
        self.current_file_frame.pack(pady=5, padx=10, fill=tk.X)
        self.register_widget("ui", self.current_file_frame)
        self.current_file_frame.columnconfigure(0, weight=1)
        self.current_file_path_text = tk.Label(self.current_file_frame, text="画像が選択されていません", font=self.ui_font, bg="lightgrey", wraplength=700, anchor="w")
        self.current_file_path_text.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=5)
        self.register_widget("ui", self.current_file_path_text)

        # ファイルを開くボタン
        self.open_file_path_button = tk.Button(self.current_file_frame, text="画像を表示", command=self.open_file_path, font=(self.ui_font[0], self.ui_font[1], "bold"), padx=10, pady=5, state=tk.DISABLED)
        self.open_file_path_button.grid(row=0, column=1, sticky=tk.E, padx=5, pady=5)
        self.register_widget("ui", self.open_file_path_button)


        # メタデータ表示エリア
        self.metadata_frame = tk.LabelFrame(self.main_frame, text="メタデータ", font=self.ui_font, bg="#ffffff", relief="sunken", bd=1)
        self.metadata_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        self.register_widget("ui", self.metadata_frame)
        self.metadata_frame.columnconfigure(1, weight=1)
        for i in range(6):
            self.metadata_frame.rowconfigure(i, weight=1)

        # プロンプトエリア
        self.prompt_label = tk.Label(self.metadata_frame, text="プロンプト", font=self.ui_font, bg="#ffffff")
        self.prompt_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.register_widget("ui", self.prompt_label)

        self.prompt_text = tk.Text(self.metadata_frame, height=4, font=self.text_font, wrap=tk.WORD)
        self.prompt_text.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
        self.register_widget("text", self.prompt_text)

        self.prompt_text_scrollbar = tk.Scrollbar(self.metadata_frame, command=self.prompt_text.yview)
        self.prompt_text_scrollbar.grid(row=1, column=2, sticky=tk.NS)
        self.prompt_text.config(yscrollcommand=self.prompt_text_scrollbar.set)

        # ネガティブプロンプトエリア
        self.negative_prompt_label = tk.Label(self.metadata_frame, text="ネガティブプロンプト", font=self.ui_font, bg="#ffffff")
        self.negative_prompt_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.register_widget("ui", self.negative_prompt_label)

        self.negative_prompt_text = tk.Text(self.metadata_frame, height=4, font=self.text_font, wrap=tk.WORD)
        self.negative_prompt_text.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
        self.register_widget("text", self.negative_prompt_text)

        self.negative_prompt_text_scrollbar = tk.Scrollbar(self.metadata_frame, command=self.negative_prompt_text.yview)
        self.negative_prompt_text_scrollbar.grid(row=3, column=2, sticky=tk.NS)
        self.negative_prompt_text.config(yscrollcommand=self.negative_prompt_text_scrollbar.set)

        # その他の情報エリア
        self.extra_info_label = tk.Label(self.metadata_frame, text="その他の情報", font=self.ui_font, bg="#ffffff")
        self.extra_info_label.grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.register_widget("ui", self.extra_info_label)
        self.extra_info = tk.Text(self.metadata_frame, state=tk.DISABLED, height=3, font=self.text_font, wrap=tk.WORD, bg="lightgrey")
        self.extra_info.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
        self.register_widget("text", self.extra_info)
        self.extra_info_scrollbar = tk.Scrollbar(self.metadata_frame, command=self.extra_info.yview)
        self.extra_info_scrollbar.grid(row=5, column=2, sticky=tk.NS)
        self.extra_info.config(yscrollcommand=self.extra_info_scrollbar.set)

        # 解析データ・もしくは追加テキストの表示及び編集エリア
        # self.analyzerがNoneの場合には「追加テキスト」とラベル名を変更
        label_name = "追加テキスト" if self.analyzer is None else "解析データ"
        self.result_frame = tk.LabelFrame(self.main_frame, text=label_name, font=self.ui_font, bg="#ffffff", relief="sunken", bd=1)
        self.result_frame.pack(pady=5, padx=10, fill=tk.X)
        self.register_widget("ui", self.result_frame)

        self.additional_text = tk.Text(self.result_frame, height=2, font=self.text_font, wrap=tk.WORD)
        self.additional_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.register_widget("text", self.additional_text)

        self.scrollbar = tk.Scrollbar(self.result_frame, command=self.additional_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.additional_text.config(yscrollcommand=self.scrollbar.set)

        # ボタンフレームの設定
        self.button_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.button_frame.pack(pady=5, padx=10, fill=tk.X, expand=True)

        # ボタンを格納するリスト
        buttons = []

        if self.analyzer is not None:
            self.analyze_button = tk.Button(self.button_frame, text="AIで解析", command=self.analyze_with_AI, bg="#2196F3", fg="white", font=(self.ui_font[0], self.ui_font[1], "bold"), padx=20, pady=5)
            buttons.append(self.analyze_button)
            self.register_widget("ui", self.analyze_button)

        self.write_button = tk.Button(self.button_frame, text="データを画像に保存", command=self.add_blip_caption_to_metadata, bg="#4CAF50", fg="white", font=(self.ui_font[0], self.ui_font[1], "bold"), padx=15, pady=5)
        buttons.append(self.write_button)
        self.register_widget("ui", self.write_button)

        self.save_metadata_button = tk.Button(self.button_frame, text="データをCSVに保存", command=self.save_metadata_to_csv, bg="#FF9800", fg="white", font=(self.ui_font[0], self.ui_font[1], "bold"), padx=15, pady=5)
        buttons.append(self.save_metadata_button)
        self.register_widget("ui", self.save_metadata_button)

        self.discard_button = tk.Button(self.button_frame, text="編集内容を破棄", command=self.discard, bg="#f44336", fg="white", font=(self.ui_font[0], self.ui_font[1], "bold"), padx=15, pady=5)
        buttons.append(self.discard_button)
        self.register_widget("ui", self.discard_button)

        self.remove_personal_data_button = tk.Button(self.button_frame, text="データを削除し複製", command=self.remove_personal_data, bg="#b00020", fg="white", font=(self.ui_font[0], self.ui_font[1], "bold"), padx=15, pady=5)
        buttons.append(self.remove_personal_data_button)
        self.register_widget("ui", self.remove_personal_data_button)

        # ボタンを均等に配置
        for i, button in enumerate(buttons):
            self.button_frame.columnconfigure(i, weight=1)
            button.grid(row=0, column=i, padx=5, pady=5, sticky="ew")

        # ステータスフレームの設定
        self.status_frame = tk.Frame(self, bg="#f0f0f0")
        self.status_frame.pack(fill=tk.BOTH, padx=10, pady=5)

        self.progressbar = ttk.Progressbar(self.status_frame, orient="horizontal", mode="determinate")
        self.status_label = tk.Label(self.status_frame, text="ファイルを選択してください", bg="#f0f0f0", font=self.ui_font, wraplength=self.winfo_screenwidth() / 2- 110, anchor="w")
        self.status_label.pack(side=tk.LEFT)
        self.register_widget("ui", self.status_label)
        self.progressbar.pack(side=tk.RIGHT, fill=tk.X)

    def register_widget(self, part, widget):
        """フォント更新のためにウィジェットをリスト登録するメソッド"""
        if part == "ui":
            self.ui_font_widgets.append(widget)
        elif part == "text":
            self.text_font_widgets.append(widget)

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
            self.update_status("画像ファイルの情報を表示しました。AIでのタグ解析やメタデータの編集が可能です。")
            self.current_file_path_text.config(text=self.current_file_path)
            self.open_file_path_button.config(state=tk.NORMAL)
        else:
            self.update_status("現在サポートされていないファイル形式です。png及びwebp拡張子のみ対応しています。",status_type="error")
            self.current_file_path = None
            self.original_caption = None

    def analyze_with_AI(self):
        """AIで画像を解析するメソッド"""

        # self.analyzerがNoneの場合のエラー表示（無い場合はメソッド自体を使用しないが念の為）
        if self.analyzer is None:
            self.update_status("ライト版のためAI解析は利用できません", status_type="error")

        if self.is_analyzing:
            messagebox.showwarning("警告", "現在、画像の解析中のため実行できません。")
            return

        # 解析前にresult textを初期化
        self.additional_text.delete(1.0, tk.END)

        if self.current_file_path:
            # 解析中フラグを設定し、ボタンをDISABLEDにする
            self.is_analyzing = True 
            self.analyze_button.config(state=tk.DISABLED)
            self.write_button.config(state=tk.DISABLED)
            self.save_metadata_button.config(state=tk.DISABLED)
            self.discard_button.config(state=tk.DISABLED)
            self.remove_personal_data_button.config(state=tk.DISABLED)

            self.progressbar.start() 
            
            # threading.Threadを使用して、ロードと解析を別スレッドで実行
            thread = threading.Thread(target=self.run_analysis)
            thread.start()
        else:
            self.update_status("解析する画像がありません",status_type="error")

    def run_analysis(self):
        """AIモデルのロードと解析を行うメソッド"""

        # ライト版の場合の処理の無効化（念の為）
        if self.analyzer is None:
            return
        
        # analyzeに使用するモデルについての設定を読み込む
        self.metadata_manager.reload_config()  # config.iniを再読み込み
        self.analysis_model = self.metadata_manager.config_data.get('DEFAULT', 'analysis_model', fallback='CLIP')
        self.is_show_result_graph = self.metadata_manager.config_data.getboolean('DEFAULT', 'is_show_result_graph', fallback=True)

        self.update_status("torchライブラリのロード中...", status_type="processing")
        if self.is_torch_loaded is False:
            torch_load_result = self.analyzer.load_torch()
            if torch_load_result:
                self.is_torch_loaded = True
            else:
                self.update_status("Torchのロードに失敗しました。処理を続行できません", status_type="error")
                return
        
        self.update_status(f"画像解析用のモデル({self.analysis_model})をロード中...",status_type="processing")
        model_load_result = self.analyzer.load_model(self.analysis_model)
        if model_load_result is False:
            self.update_status("解析用のモデルをロードできませんでした。処理を続行できません", status_type="error")
            return
        
        self.update_status("画像を解析中...", status_type="processing")

        if self.analysis_model == 'CLIP':
            # CLIPでの解析
            result = self.analyzer.analyze_image_with_clip(self.current_file_path)
            analysis_type = "CLIP"
            
            categories, probabilities = self.separate_categories_from_result(result)

            # グラフ表示
            if self.is_show_result_graph:
                self.after(0, lambda: self.show_graph(categories, probabilities))
        elif self.analysis_model == 'BLIP-2':
            # BLIP-2での解析
            result = self.analyzer.analyze_image_with_blip(self.current_file_path)
            analysis_type = "BLIP-2"
        
        elif self.analysis_model == 'MobileNet_v3_Small':
            # MobileNet_v3_Smallでの解析
            result = self.analyzer.analyze_image_with_mobilenet(self.current_file_path, "small")
            analysis_type = "MobileNet_v3_Small"

            categories, probabilities = self.separate_categories_from_result(result)

            # グラフ表示
            if self.is_show_result_graph:
                self.after(0, lambda: self.show_graph(categories, probabilities))
        
        elif self.analysis_model == 'MobileNet_v3_Large':
            # MobileNet_v3_Largeでの解析
            result = self.analyzer.analyze_image_with_mobilenet(self.current_file_path, "large")
            analysis_type = "MobileNet_v3_Large"

            categories, probabilities = self.separate_categories_from_result(result)

            # グラフ表示
            if self.is_show_result_graph:
                self.after(0, lambda: self.show_graph(categories, probabilities))

        # 解析結果をログに記録
        self.log_analysis(self.current_file_name, analysis_type, result)

        # メインスレッドでGUIを更新
        if self.analysis_model == 'BLIP-2':
            self.after(0, lambda: self.update_gui_after_analysis(result))
        else:
            self.after(0, lambda: self.update_gui_after_analysis(", ".join(categories)))
        
    def update_gui_after_analysis(self, result):
        self.additional_text.insert(tk.END, result)
        self.original_caption = result
        self.update_status("画像解析が完了しました", status_type="success")
        self.progressbar.stop()

        # 解析完了後のフラグ処理とボタンの有効化
        self.is_analyzing = False  # 解析中フラグをFalseに設定
        self.analyze_button.config(state=tk.NORMAL)
        self.write_button.config(state=tk.NORMAL)
        self.save_metadata_button.config(state=tk.NORMAL)
        self.discard_button.config(state=tk.NORMAL)
        self.remove_personal_data_button.config(state=tk.NORMAL)

    def separate_categories_from_result(self, result):
        """解析結果からカテゴリと確信度を分割するメソッド"""
        categories = []
        probabilities = []
        for line in result.split("\n"):
            category, prob = line.split(":")
            categories.append(category)
            probabilities.append(float(prob.strip("%"))/100)
        
        return categories, probabilities

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

            self.extra_info.config(state=tk.NORMAL)
            self.extra_info.delete(1.0, tk.END)
            self.extra_info.insert(tk.END, others)
            self.extra_info.config(state=tk.DISABLED)

            self.additional_text.delete(1.0, tk.END)

            self.original_prompt = positive_prompt
            self.original_negative_prompt = negative_prompt
            self.update_status("メタデータを読み込みに成功しました",status_type="success")
        except Exception as e:
            self.prompt_text.insert(tk.END, f"\n\nメタデータの読み込みに失敗しました: {str(e)}")
            self.original_prompt,self.original_negative_prompt, self.extra_info = None
            self.update_status("エラー: メタデータの読み込みに失敗しました", status_type="error")

    def add_blip_caption_to_metadata(self):
        """解析データを画像のメタデータに追加する"""
        if self.current_file_path and self.original_caption:
            try:
                # 編集したメタデータの取得
                edited_prompt_text = self.prompt_text.get("1.0","end-1c")
                edited_negative_prompt_text = self.negative_prompt_text.get("1.0","end-1c")
                others_text= self.extra_info.get("1.0","end-1c")
                edited_caption = self.additional_text.get("1.0","end-1c")

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
            edited_caption = self.additional_text.get("1.0","end-1c")

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

        self.additional_text.delete(1.0, tk.END)
        if self.original_caption:
            self.additional_text.insert(tk.END, self.original_caption)

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
        self.config_data.read(CONFIG_FILE)

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
        # フォントファミリーとフォントサイズの設定
        # フォント設定
        font_frame = tk.Frame(frame, bg="#f0f0f0")
        font_frame.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=5, pady=10)
        font_frame.grid_columnconfigure(1, weight=6)
        font_frame.grid_columnconfigure(2, weight=0)  # スペーサー列
        font_frame.grid_columnconfigure(3, weight=4)

        # UIフォント設定
        ui_font_label = tk.Label(font_frame, text="UIフォント:", bg="#f0f0f0", font=self.ui_font, width=20, anchor="w")
        ui_font_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.register_widget("ui", ui_font_label)

        self.ui_font_name_var = tk.StringVar(value=self.config_data.get('DEFAULT', 'ui_font_name', fallback='Yu Gothic UI'))
        self.ui_font_name_combobox = ttk.Combobox(font_frame, textvariable=self.ui_font_name_var, values=font.families(), state="readonly", font=self.text_font)
        self.ui_font_name_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.register_widget("text", self.ui_font_name_combobox)

        self.ui_font_size_var = tk.StringVar(value=self.config_data.get('DEFAULT', 'ui_font_size', fallback='14'))
        self.ui_font_size_combobox = ttk.Combobox(font_frame, textvariable=self.ui_font_size_var, values=[str(i) for i in range(8, 25)], state="readonly", font=self.text_font, width=5)
        self.ui_font_size_combobox.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.register_widget("text", self.ui_font_size_combobox)

        # スペーサー
        tk.Label(font_frame, bg="#f0f0f0").grid(row=1, column=0, pady=10)

        # テキストフォント設定
        text_font_label = tk.Label(font_frame, text="テキストフォント:", bg="#f0f0f0", font=self.ui_font, width=20, anchor="w")
        text_font_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.register_widget("ui", text_font_label)

        self.text_font_name_var = tk.StringVar(value=self.config_data.get('DEFAULT', 'text_font_name', fallback='Yu Gothic UI'))
        self.text_font_name_combobox = ttk.Combobox(font_frame, textvariable=self.text_font_name_var, values=font.families(), state="readonly", font=self.text_font)
        self.text_font_name_combobox.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        self.register_widget("text", self.text_font_name_combobox)

        self.text_font_size_var = tk.StringVar(value=self.config_data.get('DEFAULT', 'text_font_size', fallback='12'))
        self.text_font_size_combobox = ttk.Combobox(font_frame, textvariable=self.text_font_size_var, values=[str(i) for i in range(8, 25)], state="readonly", font=self.text_font, width=5)
        self.text_font_size_combobox.grid(row=2, column=3, sticky="w", padx=5, pady=5)
        self.register_widget("text", self.text_font_size_combobox)

        # csvファイルのパスの指定
        csv_label = tk.Label(frame, text="CSVの保存先:", bg="#f0f0f0", font=self.ui_font, width=20, anchor="w")
        csv_label.grid(row=2, column=0, padx=5, pady=10, sticky=tk.W)
        self.register_widget("ui", csv_label)

        self.csv_file_path = tk.Label(frame, text=self.config_data.get("DEFAULT", "csv_path"), bg="#ffffff", font=self.text_font, relief="sunken", anchor="w")
        self.csv_file_path.grid(row=2, column=1, padx=5, pady=10, sticky=tk.EW)
        self.register_widget("text", self.csv_file_path)

        csv_button = tk.Button(frame, text="変更", command=self.select_csv_file, bg="#2196F3", fg="white", font=(self.ui_font[0], self.ui_font[1], "bold"), width=10)
        csv_button.grid(row=2, column=2, padx=5, pady=10)
        self.register_widget("ui", csv_button)

        # コピーの保存場所の設定
        image_label = tk.Label(frame, text="画像の保存場所:", bg="#f0f0f0", font=self.ui_font)
        image_label.grid(row=3, column=0, padx=5, pady=10, sticky=tk.W)
        self.register_widget("ui", image_label)

        self.image_save_path = tk.Label(frame, text=self.config_data.get("DEFAULT", "clone_save_path"), bg="#ffffff", font=self.text_font, relief="sunken", anchor="w")
        self.image_save_path.grid(row=3, column=1, padx=5, pady=10, sticky=tk.EW)
        self.register_widget("text", self.image_save_path)

        image_button = tk.Button(frame, text="変更", command=self.select_image_save_path, bg="#2196F3", fg="white", font=(self.ui_font[0], self.ui_font[1], "bold"), width=10)
        image_button.grid(row=3, column=2, padx=5, pady=10)
        self.register_widget("ui", image_button)

        # キャプションの追加位置の選択
        position_label = tk.Label(frame, text="解析結果の追加位置:", bg="#f0f0f0", font=self.ui_font)
        position_label.grid(row=4, column=0, padx=5, pady=10, sticky=tk.W)
        self.register_widget("ui", position_label)

        self.caption_position = tk.StringVar(frame, self.config_data.get("DEFAULT", "caption_position"))
        position_option = tk.OptionMenu(frame, self.caption_position, "TOP", "BOTTOM")
        position_option.config(bg="#ffffff", font=self.text_font)
        position_option.grid(row=4, column=1, padx=5, pady=10, sticky=tk.EW)
        self.register_widget("text", position_option)

        # csvファイル保存時にファイル名をキャプションで置き換えるかの設定
        replace_label = tk.Label(frame, text="CSV保存時にタイトルを解析結果に置き換え:", bg="#f0f0f0", font=self.ui_font, wraplength=150)
        replace_label.grid(row=5, column=0, padx=5, pady=10, sticky=tk.W)
        self.register_widget("ui", replace_label)

        self.replace_caption = tk.BooleanVar(frame, self.config_data.getboolean("DEFAULT", "replace_caption", fallback=False))
        replace_checkbutton = tk.Checkbutton(frame, variable=self.replace_caption, bg="#ffffff", font=self.text_font)
        replace_checkbutton.grid(row=5, column=1, padx=5, pady=10)
        self.register_widget("text", replace_checkbutton)

        # csvのタイトルに付けるprefixの設定
        prefix_label = tk.Label(frame, text="CSV保存時のタイトルの接頭辞:", bg="#f0f0f0", font=self.ui_font, wraplength=150)
        prefix_label.grid(row=6, column=0, padx=5, pady=10, sticky=tk.W)
        self.register_widget("ui", prefix_label)

        self.prefix_word = tk.StringVar(frame, self.config_data.get("DEFAULT", "csv_title_prefix"))
        self.prefix = tk.Entry(frame, width=30, font=self.text_font, textvariable=self.prefix_word)
        self.prefix.grid(row=6, column=1, padx=5, pady=10, sticky=tk.EW)
        self.register_widget("text", self.prefix)

        # 解析モデルの選択
        model_label = tk.Label(frame, text="解析モデル:", bg="#f0f0f0", font=self.ui_font)
        model_label.grid(row=7, column=0, padx=5, pady=10, sticky=tk.W)
        self.register_widget("ui", model_label)

        self.model_var = tk.StringVar(value=self.config_data.get('DEFAULT', 'analysis_model', fallback='blip2'))
        model_combo = ttk.Combobox(frame, textvariable=self.model_var, values=['BLIP-2', 'CLIP', 'MobileNet_v3_Small','MobileNet_v3_Large'], state="readonly", font=self.text_font)
        model_combo.grid(row=7, column=1, padx=5, pady=10, sticky=tk.EW)
        self.register_widget("text", model_combo)

        # CLIPで解析するワードの設定
        tk.Label(frame, text="CLIPのカテゴリー設定:").grid(row=8, column=0, sticky="w")
        self.clip_categories = tk.Text(frame, height=5, width=50, font=self.text_font)
        self.clip_categories.grid(row=8, column=1, sticky="we")
        self.register_widget("text", self.clip_categories)
        self.clip_categories.insert(tk.END, self.config_data.get('DEFAULT', 'clip_categories', fallback=''))

        # CLIPの解析結果で表示するワードの数を指定するスライダー
        self.word_count_var = tk.IntVar(value=int(self.config_data.get('DEFAULT', 'word_count', fallback=5)))
        word_count_label = tk.Label(frame, text="CLIPで表示するワード数:", bg="#f0f0f0", font=self.ui_font)
        word_count_label.grid(row=9, column=0, sticky="w")
        self.register_widget("ui", word_count_label)

        word_count_scale = tk.Scale(frame,from_=1,to=20,orient=tk.HORIZONTAL,variable=self.word_count_var,length=200)
        word_count_scale.grid(row=9, column=1, sticky="w")
        word_count_value_label = tk.Label(frame, textvariable=self.word_count_var, bg="#f0f0f0", font=self.ui_font) # 現在の値を表示するラベル
        word_count_value_label.grid(row=9, column=1, sticky="e")
        self.register_widget("ui", word_count_value_label)
        
        def update_word_count(*args):# スライダーの値が変更されたときに呼び出される関数
            self.word_count_var.set(int(self.word_count_var.get()))
        
        self.word_count_var.trace_add("write", update_word_count)# スライダーの値が変更されたときにupdate_word_count関数を呼び出す

        # CLIP解析でグラフ表示を行うかの選択        
        graph_label = tk.Label(frame, text="解析結果のグラフを表示:", bg="#f0f0f0", font=self.ui_font)
        graph_label.grid(row=10, column=0, sticky="w")
        self.register_widget("ui", graph_label)

        self.graph_var = tk.BooleanVar(frame, self.config_data.getboolean("DEFAULT", "is_show_result_graph", fallback=True))
        graph_checkbutton = tk.Checkbutton(frame, variable=self.graph_var, bg="#ffffff", font=self.ui_font)
        graph_checkbutton.grid(row=10, column=1, padx=5, pady=10)
        self.register_widget("ui", graph_checkbutton)

        # blip-2で4bit量子化モデルを使用するかの選択
        use_4bit_model_label = tk.Label(frame, text="blip-2で4bit量子化モデルを使用（cuda対応バージョンのみ）:", bg="#f0f0f0", font=self.ui_font)
        use_4bit_model_label.grid(row=11, column=0, sticky="w")
        self.register_widget("ui", use_4bit_model_label)

        self.use_4bit_model_var = tk.BooleanVar(frame, self.config_data.getboolean("DEFAULT", "use_4bit_model", fallback=False))
        use_4bit_checkbutton = tk.Checkbutton(frame, variable=self.use_4bit_model_var, bg="#ffffff", font=self.ui_font)
        use_4bit_checkbutton.grid(row=11, column=1, padx=5, pady=10)
        self.register_widget("ui", use_4bit_checkbutton)

        # ボタンフレーム
        button_frame = tk.Frame(scrollable_frame, bg="#f0f0f0")
        button_frame.pack(pady=20)

        # OKボタン
        ok_button = tk.Button(button_frame, text="設定を保存", command=self.save_settings, bg="#4CAF50", fg="white", font=(self.ui_font[0], self.ui_font[1], "bold"), width=15)
        ok_button.pack(side=tk.LEFT, padx=10)
        self.register_widget("ui", ok_button)

        # Cancelボタン
        cancel_button = tk.Button(button_frame, text="キャンセル", command=self.settings_discard, bg="#f44336", fg="white", font=(self.ui_font[0], self.ui_font[1], "bold"), width=15)
        cancel_button.pack(side=tk.LEFT, padx=10)
        self.register_widget("ui", cancel_button)

        # キャンバスとスクロールバーを配置
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Configure grid weights
        frame.grid_columnconfigure(1, weight=1)

        # ウィンドウが閉じられたときの処理を追加
        self.settings_window.protocol("WM_DELETE_WINDOW", self.close_settings_window)

    def show_graph(self, categories, probabilities):
        """別ウィンドウでグラフを表示するメソッド"""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        try:
            if self.graph_window is None or not self.graph_window.winfo_exists():
                self.graph_window = tk.Toplevel(self)
                self.graph_window.title("解析結果グラフ")
                self.graph_window.geometry("800x600")
                self.fig, self.ax = plt.subplots(figsize=(8, 6))
                self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_window)
                self.canvas_widget = self.canvas.get_tk_widget()
                self.canvas_widget.pack(fill=tk.BOTH, expand=True)
                
                # ウィンドウが閉じられたときの処理
                self.graph_window.protocol("WM_DELETE_WINDOW", self.on_graph_window_close)
            else:
                self.graph_window.lift()  # ウィンドウを前面に
            
            self.ax.clear()
            self.ax.bar(categories, probabilities)
            self.ax.set_ylabel('確率')
            self.ax.set_title('カテゴリ別確率')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            self.canvas.draw()

        except Exception as e:
            self.update_status(f"グラフの表示中にエラーが発生しました: {str(e)}", status_type="error")
            messagebox.showerror("エラー", f"グラフの表示中にエラーが発生しました: {str(e)}")

    def on_graph_window_close(self):
        """グラフウィンドウが閉じられたときの処理"""
        plt.close(self.fig)
        self.graph_window.destroy()
        self.graph_window = None

    def save_settings(self):
        """設定値を保存する"""
        # 設定値を取得
        csv_path = self.csv_file_path.cget("text")
        image_save_path = self.image_save_path.cget("text")
        caption_position = self.caption_position.get()
        replace_caption = self.replace_caption.get()
        csv_title_prefix = self.prefix.get()
        selected_model = self.model_var.get()
        clip_categories = self.clip_categories.get("1.0", tk.END).strip()
        word_count = self.word_count_var.get()
        is_show_result_graph = self.graph_var.get()
        ui_font_name = self.ui_font_name_var.get()
        ui_font_size = self.ui_font_size_var.get()
        text_font_name = self.text_font_name_var.get()
        text_font_size = self.text_font_size_var.get()
        use_4bit_model = self.use_4bit_model_var.get()
        
        # 設定値を保存（configparserを使用）
        self.config_data['DEFAULT'] = {
            'csv_path': csv_path,
            'clone_save_path': image_save_path,
            'caption_position': caption_position,
            'replace_caption': str(replace_caption).lower(),
            'csv_title_prefix': csv_title_prefix,
            'analysis_model': selected_model,
            'clip_categories': clip_categories,
            'word_count': str(word_count),
            'is_show_result_graph': str(is_show_result_graph).lower(),
            'ui_font_name': ui_font_name,
            'ui_font_size': str(ui_font_size),
            'text_font_name': text_font_name,
            'text_font_size': str(text_font_size),
            'use_4bit_model': str(use_4bit_model).lower()
        }
        with open(CONFIG_FILE, 'w') as configfile:
            self.config_data.write(configfile)

        # フォント設定が変更されている場合は変更する
        new_ui_font = (ui_font_name, int(ui_font_size))
        new_text_font = (text_font_name, int(text_font_size))
        if new_ui_font != self.ui_font:
            self.ui_font = new_ui_font
            self.update_fonts("ui")

        if new_text_font!= self.text_font:
            self.text_font = new_text_font
            self.update_fonts("text")

        # 設定画面を閉じる
        self.close_settings_window()
        self.update_status("設定を保存しました")

    def update_fonts(self, part):
        # UIフォントの更新処理
        if part == "ui":
            for widget in self.ui_font_widgets:
                try:
                    if widget.winfo_exists():
                        if hasattr(widget, 'config'):
                            if isinstance(widget, tk.Button):
                                # ボタンの場合はboldを追加
                                widget.config(font=(self.ui_font[0], self.ui_font[1], "bold"))
                            else:
                                # ボタン以外の場合は通常のフォントを適用
                                widget.config(font=self.ui_font)
                except Exception as e:
                    print(f"Error updating UI font: {str(e)}")

        # テキストフォントの更新
        if part == "text":    
            for widget in self.text_font_widgets:
                try:
                    if widget.winfo_exists():
                        if hasattr(widget, 'config'):
                            widget.config(font=self.text_font)
                except Exception as e:
                    print(f"Error updating text font: {str(e)}")
    
        #self.main_frame.update()
        for widget in self.main_frame.winfo_children():
            widget.update()

    def settings_discard(self):
        """設定変更を破棄する"""
        self.close_settings_window()
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
            license_content = get_resource_content('licenses.txt')
            
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
        help_text = get_resource_content('help.txt')
        
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
            description = get_resource_content('version.txt')
            messagebox.showinfo("バージョン情報", description)
        except FileNotFoundError:
            messagebox.showerror("エラー", "version.txt ファイルが見つかりません。")
        except Exception as e:
            messagebox.showerror("エラー", f"バージョン情報の読み込み中にエラーが発生しました: {str(e)}")
    
    def log_analysis(self, image_name, analysis_type, result):
        """解析結果をログファイルに記録するメソッド"""
        # ユーザーのホームディレクトリを取得
        config_dir = os.path.join(os.path.expanduser('~'), '.metadata_manager')
        log_dir = os.path.join(config_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, "analysis_log.txt")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] Image: {image_name}\n")
            f.write(f"Analysis Type: {analysis_type}\n")
            f.write(f"Result: {result}\n\n")

    def on_closing(self):
        """アプリケーションの終了処理"""
        # すでに終了処理中の場合は処理を開始しない
        if self.is_closing:
            return
        # 処理中のフラグを立てる
        self.is_closing = True

        # 実行中のスレッドがあれば終了を待つ
        if hasattr(self, 'analysis_thread') and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=1)  # 1秒待つ

        # リソースの解放
        if hasattr(self, 'analyzer') and self.analyzer:
            self.analyzer.close()

        # アプリケーションを終了
        #グラフを表示させるウィンドウが開いているときは終了させる
        if self.graph_window:
            self.on_graph_window_close()
        self.quit()
        self.destroy()

    def close_settings_window(self):
        """設定画面を閉じるメソッド"""
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            try:
                self.settings_window.grab_release()
            except Exception as e:
                print(f"Error releasing settings window: {str(e)}")
            # Tkinter変数を解放
            tk_vars = [
                'ui_font_name_var', 'ui_font_size_var', 
                'text_font_name_var', 'text_font_size_var', 
                'caption_position', 'replace_caption', 
                'prefix_word', 'model_var', 'word_count_var', 
                'graph_var'
            ]
            
            for var_name in tk_vars:
                if hasattr(self, var_name):
                    delattr(self, var_name)
            
            # ウィンドウを破棄
            self.settings_window.destroy()
            self.settings_window = None
