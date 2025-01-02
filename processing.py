import torch
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from PIL import Image
import cv2
import numpy as np
import piexif
import piexif.helper
from PIL.PngImagePlugin import PngInfo

#画像を解析し、キャプションを生成するクラス。
class ImageAnalyzer:
    def __init__(self):
        self.processor = None
        self.model = None
    #BLIP-2モデルをロードするメソッド
    def load_model(self):
        if self.model is None:
            self.processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
            self.model = Blip2ForConditionalGeneration.from_pretrained(
                "Salesforce/blip2-opt-2.7b",
                device_map="auto",
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True
            )
    #画像を前処理するメソッド
    def preprocess_image(self, image_path):
        image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (224, 224))
        return Image.fromarray(image)

    #画像を解析し、キャプションを生成するメソッド
    def analyze_image(self, image_path):
        try:
            image = self.preprocess_image(image_path)
            inputs = self.processor(image, return_tensors="pt").to(self.model.device)
            with torch.inference_mode():
                outputs = self.model.generate(**inputs, min_length=50, max_new_tokens=200, num_beams=3, do_sample=True, temperature=0.8)
            caption_text = self.processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()
            return f"画像の説明: {caption_text}"
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"
        
#画像のメタデータを管理するクラス
class MetadataManager:
    @staticmethod
    def write_metadata(file_path, caption):
        ext = file_path.lower().split('.')[-1]
        img = Image.open(file_path)

        if ext in ['jpg', 'jpeg']:
            exif_dict = piexif.load(img.info.get("exif", piexif.dump({"0th":{}, "Exif":{}, "GPS":{}, "1st":{}, "thumbnail":None})))
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = caption.encode()
            img.save(file_path, exif=piexif.dump(exif_dict))
        elif ext == 'png':
            metadata = PngInfo()
            for key, value in img.info.items():
                if isinstance(value, str):
                    metadata.add_text(key, value)
            metadata.add_text("Description", caption)
            img.save(file_path, pnginfo=metadata)
        elif ext == 'webp':
            metadata = img.info.copy()
            metadata['Description'] = caption
            img.save(file_path, **metadata)
        else:
            raise ValueError("Unsupported file format")

    #webpファイルのバイト列からExif UserCommentを取得するメソッド
    def get_corrupted_user_comment(file_content):
        # UserCommentタグのID
        user_comment_tag_id = b'\x92\x86'

        # タグIDの位置を探す
        tag_start = file_content.find(user_comment_tag_id, 0x20)  # 0x20以降で検索

        if tag_start == -1:
            return "UserComment tag not found."

        # データタイプの特定
        data_type_start = tag_start + 2
        data_type = file_content[data_type_start:data_type_start + 2]

        # コンポーネント数の特定
        component_count_start = data_type_start + 2
        component_count = int.from_bytes(file_content[component_count_start:component_count_start + 4], byteorder='big')

        # オフセットの特定
        offset_start = component_count_start + 4
        offset = int.from_bytes(file_content[offset_start:offset_start + 4], byteorder='big')

        # UserCommentのバイナリデータを取得
        user_comment_data = file_content[offset : offset+component_count]

        # データのデコード (UNICODEかつUTF-16BEを想定)
        try:
            if user_comment_data.startswith(b'UNICODE\x00'):
                decoded_value = user_comment_data[8:].decode('utf-16be', errors='ignore')
            else:
                decoded_value = user_comment_data.decode('utf-8', errors='ignore')
            return decoded_value
        except UnicodeDecodeError:
            return "Could not decode UserComment data."

    #画像ファイルからメタデータを読み込むメソッド
    @staticmethod
    def read_metadata(file_path):
        with Image.open(file_path) as img:
            metadata = {}
            if img.format == "PNG" and "parameters" in img.info:
                metadata['parameters'] = img.info["parameters"]
            elif img.format == "WEBP" and "exif" in img.info:
                exif_dict = piexif.load(img.info["exif"])
                user_comment = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
                if user_comment:
                    metadata['Exif UserComment'] = piexif.helper.UserComment.load(user_comment)
            return metadata

    #Exif UserCommentをデコードするメソッド
    @staticmethod
    def decode_user_comment(user_comment):
        if user_comment.startswith(b'UNICODE\x00'):
            return user_comment[8:].decode('utf-16be', errors='ignore')
        return user_comment.decode('utf-8', errors='ignore')

    #メタデータからプロンプトを抽出するメソッド
    @staticmethod
    def extract_prompts(text):
        lines = text.split('\n')
        positive_prompt, negative_prompt = [], []
        is_negative = False
        for line in lines:
            if line.startswith("Negative prompt: "):
                is_negative = True
                line = line.replace("Negative prompt: ", "")
            elif line.startswith("Steps:"):
                break
            (negative_prompt if is_negative else positive_prompt).append(line.strip())
        return " ".join(positive_prompt).strip(), " ".join(negative_prompt).strip()