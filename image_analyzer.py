import torch
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from PIL import Image
import cv2
import numpy as np
from PIL import Image

class ImageAnalyzer:
    """画像を解析し、キャプションを生成するクラス"""
    def __init__(self):
        self.processor = None
        self.model = None
    
    def load_model(self):
        """BLIP-2モデルをロードするメソッド"""
        if self.model is None:
            self.processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
            self.model = Blip2ForConditionalGeneration.from_pretrained(
                "Salesforce/blip2-opt-2.7b",
                device_map="auto",
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True
            )

    
    def preprocess_image(self, image_path):
        """画像を前処理するメソッド"""
        image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (192, 192))
        return Image.fromarray(image)

    def analyze_image(self, image_path):
        """画像を解析し、キャプションを生成するメソッド"""
        try:
            image = self.preprocess_image(image_path)
            inputs = self.processor(image, return_tensors="pt").to(self.model.device)
            with torch.inference_mode():
                outputs = self.model.generate(**inputs, min_length=50, max_new_tokens=200, num_beams=3, do_sample=True, temperature=0.8)
            caption_text = self.processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()
            return caption_text
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"