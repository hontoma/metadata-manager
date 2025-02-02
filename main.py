from metadata_manager.gui import ImageAnalyzerApp
import traceback

def main():

    app = ImageAnalyzerApp()

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