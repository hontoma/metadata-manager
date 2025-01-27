from PIL import Image
import cv2
from PIL import Image
from metadata_manager.config import get_config

class ImageAnalyzer:
    """画像を解析し、キャプションを生成するクラス"""
    def __init__(self, config):
        self.processor = None
        self.model = None
        self.clip_processor = None
        self.clip_model = None
        self.config = config

    def get_latest_config(self):
        """最新の設定を取得するメソッド"""
        return get_config()
  
    def preprocess_image(self, image_path):
        """画像を前処理するメソッド"""
        import numpy as np
        image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (192, 192))
        return Image.fromarray(image)
    
    def load_blip_model(self):
        """BLIP-2モデルをロードするメソッド"""
        import torch
        from transformers import Blip2Processor, Blip2ForConditionalGeneration
        if self.model is None:
            self.processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
            self.model = Blip2ForConditionalGeneration.from_pretrained(
                "Salesforce/blip2-opt-2.7b",
                device_map="auto",
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True
            )

    def analyze_image_with_blip(self, image_path):
        """画像を解析し、キャプションを生成するメソッド"""
        import torch
        try:
            self.load_blip_model()
            image = self.preprocess_image(image_path)
            inputs = self.processor(image, return_tensors="pt").to(self.model.device)
            with torch.inference_mode():
                outputs = self.model.generate(**inputs, min_length=50, max_new_tokens=200, num_beams=3, do_sample=True, temperature=0.8)
            caption_text = self.processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()
            return caption_text
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"
        
    def load_clip_model(self):
        """CLIPモデルをロードするメソッド"""
        from transformers import CLIPProcessor, CLIPModel
        if self.clip_model is None:
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")

    def analyze_image_with_clip(self, image_path):
        """CLIPを使用して画像を解析し、カテゴリを予測するメソッド"""
        import torch
        try:
            self.load_clip_model()
            image = Image.open(image_path).convert("RGB")

            # 最新の設定を取得
            latest_config = self.get_latest_config()
            
            # カテゴリーの初期値
            default_categories = "a photo of a person, a photo of a landscape, a photo of an animal, a photo of food, a photo of a building"

            # カテゴリー設定の読み込み
            categories = latest_config.get('DEFAULT', 'clip_categories', fallback=default_categories).split(',')
            word_count = int(latest_config.getint('DEFAULT', 'word_count', fallback=5))
            
            categories = [cat.strip() for cat in categories]
            inputs = self.clip_processor(text=categories, images=image, return_tensors="pt", padding=True)
            
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)

            # probs[0]をNumPy配列に変換
            probs_np = probs[0].cpu().numpy()

            # 設定された数の結果を取得する
            top_words = sorted(zip(categories, probs_np), key=lambda x: x[1], reverse=True)[:word_count]

            results = []
            for category, prob in top_words:
                results.append(f"{category}: {prob.item():.2%}")

            return "\n".join(results)
        except Exception as e:
            return f"CLIPによる解析中にエラーが発生しました: {str(e)}"

    def close(self):
        """リソースを解放するメソッド"""
        # モデルやその他のリソースを解放する処理
        if hasattr(self, 'blip_model'):
            del self.blip_model
        if hasattr(self, 'clip_model'):
            del self.clip_model