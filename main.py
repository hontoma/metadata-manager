from gui import ImageAnalyzerApp
from processing import ImageAnalyzer

if __name__ == "__main__":
    analyzer = ImageAnalyzer()
    app = ImageAnalyzerApp(analyzer)
    app.mainloop()