from gui import ImageAnalyzerApp

if __name__ == "__main__":
    # image_analyzer.pyが存在する場合はインポート
    try:
        from image_analyzer import ImageAnalyzer # type: ignore
        analyzer = ImageAnalyzer()

    # 存在しない場合はスキップ
    except ImportError:
        analyzer = None
    app = ImageAnalyzerApp(analyzer)
    app.mainloop()