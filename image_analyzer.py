from PIL import Image
import cv2
import os
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
        self.mobilenet_v3_small_model = None
        self.mobilenet_v3_large_model = None
        self.mobilenet_v3_small_model_preprocess = None
        self.mobilenet_v3_large_model_preprocess = None
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
                self.load_mobilenet_model("small")
            elif model_name == "MobileNet_v3_Large":
                self.load_mobilenet_model("large")
            
            return True
        except Exception as e:
            return False

    def get_latest_config(self):
        """最新の設定を取得するメソッド"""
        return get_config()
    
    def get_model_path(self, model_name):
        """モデルのパスを取得するメソッド"""
        app_dir = os.path.join(os.path.expanduser('~'), '.metadata_manager')
        return os.path.join(app_dir, 'models', model_name)
  
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
        from transformers import Blip2Processor, Blip2ForConditionalGeneration, BitsAndBytesConfig
        import traceback
        try:
            model_path = self.get_model_path("blip2-opt-2.7b")
            is_use_4bit_model: bool = self.get_latest_config().getboolean("DEFAULT", "use_4bit_model", fallback=False)
            self.is_torch_with_cuda_version: bool = torch.cuda.is_available()

            torch_dtype = torch.float16 if self.is_torch_with_cuda_version else torch.float32

            from_pretrained_kwargs = {
                "cache_dir": model_path,
                "torch_dtype": torch_dtype,
                "low_cpu_mem_usage": True,
            }

            if self.is_torch_with_cuda_version:
                from_pretrained_kwargs["device_map"] = 'auto'


            if is_use_4bit_model and self.is_torch_with_cuda_version:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                from_pretrained_kwargs["quantization_config"] = quantization_config

            if self.blip_model is None:
                print("Loading BLIP-2 model...")
                self.blip_processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b", cache_dir=model_path)
                self.blip_model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-opt-2.7b", **from_pretrained_kwargs)

            if is_use_4bit_model and self.is_torch_with_cuda_version:
                # 4ビット量子化を適用
                print("BLIP-2 model loaded with 4-bit quantization")
            else:
                print("BLIP-2 model loaded without 4-bit quantization")
            
            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def analyze_image_with_blip(self, image_path):
        """画像を解析し、キャプションを生成するメソッド"""
        import torch
        try:
            image = self.preprocess_image(image_path)
            inputs = self.blip_processor(image, return_tensors="pt").to(self.blip_model.device)

            # 4bit量子化の場合の追加処理（入力テンソルをfloat16に変換）
            if self.get_latest_config().getboolean("DEFAULT", "use_4bit_model", fallback=False):
                inputs = {k: v.to(torch.float16) for k, v in inputs.items()}
            
            with torch.inference_mode():
                outputs = self.blip_model.generate(**inputs, min_length=50, max_new_tokens=200, num_beams=5, do_sample=True, temperature=0.8)
            caption_text = self.blip_processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()
            return caption_text
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"
        
    def load_clip_model(self):
        """CLIPモデルをロードするメソッド"""
        from transformers import CLIPProcessor, CLIPModel

        model_path = self.get_model_path("clip-vit-base-patch32")

        if self.clip_model is None:
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", cache_dir=model_path)
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", cache_dir=model_path)

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

    def load_mobilenet_model(self, version):
        """MobileNetV3モデルをロードするメソッド"""
        import torch

        model_path = self.get_model_path(f"mobilenet_v3_{version}")
        model_file = os.path.join(model_path, f"mobilenet_v3_{version}.pth")

        if version == "small":
            from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
            if self.mobilenet_v3_small_model is None:
                if os.path.exists(model_file):
                # 既に保存されているモデルを読み込む
                    self.mobilenet_v3_small_model = mobilenet_v3_small()
                    self.mobilenet_v3_small_model.load_state_dict(torch.load(model_file, map_location=torch.device('cpu'), weights_only=True))
                else:
                # モデルをダウンロードして保存
                    weights = MobileNet_V3_Small_Weights.DEFAULT
                    self.mobilenet_v3_small_model = mobilenet_v3_small(weights=weights)
                    
                    # ディレクトリが存在しない場合は作成
                    os.makedirs(model_path, exist_ok=True)
                    torch.save(self.mobilenet_v3_small_model.state_dict(), model_file)
                    print(f"Downloaded and saved model to {model_file}")
                
                self.mobilenet_v3_small_model.eval()
                self.mobilenet_v3_small_model_preprocess = MobileNet_V3_Small_Weights.DEFAULT.transforms()
            
                # クラスラベルを取得
                self.class_labels = MobileNet_V3_Small_Weights.DEFAULT.meta["categories"]

        elif version == "large":
            from torchvision.models import mobilenet_v3_large, MobileNet_V3_Large_Weights
            if self.mobilenet_v3_large_model is None:
                if os.path.exists(model_file):
                    self.mobilenet_v3_large_model = mobilenet_v3_large()
                    self.mobilenet_v3_large_model.load_state_dict(torch.load(model_file, map_location=torch.device('cpu'), weights_only=True))
                    print(f"Loaded existing model from {model_file}")
                else:
                    # モデルをダウンロードして保存
                    weights = MobileNet_V3_Large_Weights.DEFAULT
                    self.mobilenet_v3_large_model = mobilenet_v3_large(weights=weights)
                    print(f"Loaded existing model from {model_file}")
                    
                    # ディレクトリが存在しない場合は作成
                    os.makedirs(model_path, exist_ok=True)
                    torch.save(self.mobilenet_v3_large_model.state_dict(), model_file)
                    print(f"Downloaded and saved model to {model_file}")
                
                self.mobilenet_v3_large_model.eval()
                self.mobilenet_v3_large_model_preprocess = MobileNet_V3_Large_Weights.DEFAULT.transforms()
                
                # クラスラベルを取得
                self.class_labels = MobileNet_V3_Large_Weights.DEFAULT.meta["categories"]

    def analyze_image_with_mobilenet(self, image_path, version):
        """MobileNetV3を使用して画像を解析するメソッド"""
        import torch
        try:
            image = Image.open(image_path).convert('RGB')
            
            with torch.no_grad():
                if version == "small":
                    input_tensor = self.mobilenet_v3_small_model_preprocess(image).unsqueeze(0)
                    output = self.mobilenet_v3_small_model(input_tensor)
                elif version == "large":
                    input_tensor = self.mobilenet_v3_large_model_preprocess(image).unsqueeze(0)
                    output = self.mobilenet_v3_large_model(input_tensor)

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
        if hasattr(self, 'mobilenet_v3_small_model'):
            del self.mobilenet_v3_small_model
        if hasattr(self, 'mobilenet_v3_large_model'):
            del self.mobilenet_v3_large_model