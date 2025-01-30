from PIL import Image
import cv2
from PIL import Image
from metadata_manager.config import get_config

class ImageAnalyzer:
    """画像を解析し、キャプションを生成するクラス"""
    def __init__(self, config):
        self.blip_processor = None
        self.blip_model = None
        self.clip_processor = None
        self.clip_model = None
        self.config = config
        self.mobilenet = None
        self.mobilenet_preprocess = None
        self.class_labels = None

    def load_torch(self):
        """torchをロードするメソッド"""
        try:
            import torch
            self.torch_loaded = True
            return True
        except ImportError:
            print("Torchのインポートに失敗しました。")
            return False
        except Exception as e:
            print(f"Torchのロード中に予期せぬエラーが発生しました: {str(e)}")
            return False
    
    def load_model(self, model_name):
        """画像解析用の選択されたモデルのロードを処理分けするためのメソッド"""
        try:
            if model_name == "CLIP":
                self.load_clip_model()
            elif model_name == "BLIP-2":
                self.load_blip_model()
            elif model_name == "MobileNet_v3_Small":
                self.load_mobilenet("small")
            elif model_name == "MobileNet_v3_Large":
                self.load_mobilenet("large")
            
            return True
        except Exception as e:
            return False

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
        if self.blip_model is None:
            self.blip_processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
            self.blip_model = Blip2ForConditionalGeneration.from_pretrained(
                "Salesforce/blip2-opt-2.7b",
                device_map="auto",
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True
            )

    def analyze_image_with_blip(self, image_path):
        """画像を解析し、キャプションを生成するメソッド"""
        import torch
        try:
            image = self.preprocess_image(image_path)
            inputs = self.blip_processor(image, return_tensors="pt").to(self.blip_model.device)
            with torch.inference_mode():
                outputs = self.blip_model.generate(**inputs, min_length=50, max_new_tokens=200, num_beams=3, do_sample=True, temperature=0.8)
            caption_text = self.blip_processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()
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

    def load_mobilenet(self, version):
        """MobileNetV3をロードするメソッド"""
        if version == "small":
            from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
        elif version == "large":
            from torchvision.models import mobilenet_v3_large, MobileNet_V3_Large_Weights
        if self.mobilenet is None:
            weights = MobileNet_V3_Small_Weights.DEFAULT if version == "small" else MobileNet_V3_Large_Weights.DEFAULT
            self.mobilenet = mobilenet_v3_small(weights=weights) if version == "small" else mobilenet_v3_large(weights=weights)
            self.mobilenet.eval()
            self.mobilenet_preprocess = weights.transforms()
            
            # クラスラベルを取得
            self.class_labels = weights.meta["categories"]

    def analyze_image_with_mobilenet(self, image_path):
        """MobileNetV3を使用して画像を解析するメソッド"""
        import torch
        try:
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.mobilenet_preprocess(image).unsqueeze(0)
            
            with torch.no_grad():
                output = self.mobilenet(input_tensor)

            # 最新の設定を取得
            latest_config = self.get_latest_config()
            word_count = int(latest_config.getint('DEFAULT', 'word_count', fallback=5))
            
            # 上位5クラスの予測結果を取得
            probabilities = torch.nn.functional.softmax(output[0], dim=0)
            top_prob, top_catid = torch.topk(probabilities, word_count)
            
            results = []
            for i in range(top_prob.size(0)):
                results.append(f"{self.class_labels[top_catid[i]]}: {top_prob[i].item():.2%}")

            return "\n".join(results)
        except Exception as e:
            return f"MobileNetV3による解析中にエラーが発生しました: {str(e)}"

    def close(self):
        """リソースを解放するメソッド"""
        # モデルやその他のリソースを解放する処理
        if hasattr(self, 'blip_model'):
            del self.blip_model
        if hasattr(self, 'clip_model'):
            del self.clip_model
        if hasattr(self, 'mobilenet'):
            del self.mobilenet