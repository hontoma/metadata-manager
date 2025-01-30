from metadata_manager.gui import ImageAnalyzerApp
from metadata_manager.config import get_config
import matplotlib.pyplot as plt
import traceback

def main():
    config = get_config()

    # Matplotlibのフォント設定
    ui_font_name = config.get('DEFAULT', 'ui_font_name', fallback='Yu Gothic, Meiryo, MS Gothic')
    plt.rcParams['font.family'] = ui_font_name

    # image_analyzer.pyが存在する場合はインポート
    try:
        from image_analyzer import ImageAnalyzer # type: ignore
        analyzer = ImageAnalyzer(config)

    # 存在しない場合はスキップ
    except ImportError:
        analyzer = None
        
    app = ImageAnalyzerApp(analyzer)

    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("KeyboardInterrupt: アプリケーションを終了します。")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        traceback.print_exc()
    finally:
        if not app.is_closing:
            app.on_closing()  # 明示的に終了処理を呼び出す

if __name__ == "__main__":
    main()