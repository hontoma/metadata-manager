import torch
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from PIL import Image
import cv2
import csv
import numpy as np
import piexif
import piexif.helper
from PIL.PngImagePlugin import PngInfo
from PIL import Image
import os
import configparser

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
        
class MetadataManager:
    """画像のメタデータを管理するクラス"""

    def __init__(self):
        self.config_data = configparser.ConfigParser()
        self.config_data.read('config.ini')
    
    @staticmethod
    def update_image_metadata(file_path, metadata):
        """メタデータを実際に画像に書き込むメソッド"""
        ext = file_path.lower().split(".")[-1]
        img = Image.open(file_path)

        if ext == "png":
            png_info = PngInfo()
            for key, value in img.info.items():
                if isinstance(value, str):
                    png_info.add_text(key, value)
            # parametersに追記する
            png_info.add_text("parameters", metadata)
            img.save(file_path, pnginfo=png_info)
        elif ext == "webp":
            # UserCommentに書き込む
            exif_dict = piexif.load(img.info.get("exif", b""))
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(
                metadata,
                encoding="unicode"
            )
            exif_bytes = piexif.dump(exif_dict)
            img.save(file_path, exif=exif_bytes)
        else:
            raise ValueError("Unsupported file format")

    @staticmethod
    def read_metadata(file_path):
        """画像ファイルからメタデータを読み込むメソッド"""
        with Image.open(file_path) as img:
            metadata = {}
            if img.format == "PNG" and "parameters" in img.info:
                metadata['parameters'] = img.info["parameters"]
            elif img.format == "WEBP" and "exif" in img.info:
                exif_dict = piexif.load(img.info["exif"])
                user_comment = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
                if user_comment:
                    metadata['parameters'] = piexif.helper.UserComment.load(user_comment)
            return metadata

    @staticmethod
    def extract_prompts(text):
        """メタデータからポジティブプロンプト、ネガティブプロンプトを抽出するメソッド"""
        lines = text.split('\n')
        positive_prompt, negative_prompt, others = [], [], []

        #ポジティブプロンプト、ネガティブプロンプト、それ以外の判別用
        is_positive = True
        is_negative = False

        for line in lines:
            if line.startswith("Negative prompt: "):
                is_positive = False
                is_negative = True
                line = line.replace("Negative prompt: ", "")
            elif line.startswith("Steps:"):
                is_negative = False
                is_positive = False
            
            if is_negative:
                negative_prompt.append(line.strip())
            elif is_positive:
                positive_prompt.append(line.strip())
            else:
                others.append(line.strip())

        #ポジティブプロンプトのみでネガティブ、その他も空の場合にはプロンプトを空と見なし、その他に集約する。
        if not negative_prompt and not others:
            others = positive_prompt.copy()
            positive_prompt.clear()

        return " ".join(positive_prompt).strip(), " ".join(negative_prompt).strip(), " ".join(others).strip()
    
    def add_blip_caption(self, positive_prompt, negative_prompt, others, caption):
        """BLIP-2のキャプションをプロンプトに追加するメソッド"""
        # Config.iniからcaption_positionを読み込む
        self.config_data.read('config.ini')
        caption_position = self.config_data.get("DEFAULT", "caption_position", fallback="bottom")

        # positive_promptにcaptionを追加
        if len(positive_prompt) == 0 and len(caption) == 0:
            positive_prompt = ""
        elif len(positive_prompt) == 0 and len(caption) > 0:
            positive_prompt = caption.strip()
        elif len(positive_prompt) > 0 and len(caption) == 0:
            pass
        else:  # len(positive_prompt) > 0 and len(caption) > 0
            if caption_position == "TOP":
                positive_prompt = f"{caption}, {positive_prompt}"
            else:  # "bottom"の場合やその他の値の場合
                positive_prompt += f", {caption}"

        # metadataの形を整形
        updated_prompt = f"{positive_prompt}\nNegative prompt: {negative_prompt}\n{others}"

        return updated_prompt

    def save_metadata_to_csv(self, positive_prompt, negative_prompt, file_name, current_caption):
        """メタデータをCSVファイルに保存するメソッド"""
        self.config_data.read('config.ini')
        output_file = self.config_data.get("DEFAULT", "csv_path")
        if not os.path.exists(output_file):
            return False
        
        with open(output_file, "a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            caption_position = self.config_data.get("DEFAULT", "caption_position")
            is_replace_title = self.config_data.getboolean("DEFAULT", "replace_caption")
            title_prefix = self.config_data.get("DEFAULT", "csv_title_prefix", fallback="")
            
            if len(current_caption) == 0:
                writer.writerow([f"{title_prefix}{file_name}", positive_prompt, negative_prompt])
            else:
                if caption_position == "TOP":
                    if is_replace_title:
                        writer.writerow([f"{title_prefix}{current_caption}", f"{current_caption}, {positive_prompt}", negative_prompt])
                    else:
                        writer.writerow([f"{title_prefix}{file_name}", f"{current_caption}, {positive_prompt}", negative_prompt])              
                elif caption_position == "BOTTOM":
                    if is_replace_title:
                        writer.writerow([f"{title_prefix}{current_caption}", f"{positive_prompt}, {current_caption}", negative_prompt])
                    else:
                        writer.writerow([f"{title_prefix}{file_name}", f"{positive_prompt}, {current_caption}", negative_prompt])
        
        return True

    def remove_personal_data(self, file_path, original_file_name):
        """画像からメタデータを削除しデスクトップに保存するメソッド"""
        try:
            # ファイルパスから波括弧を取り除く
            file_path = file_path.strip('{}')

            img = Image.open(file_path)
            file_name, file_extension = os.path.splitext(original_file_name)

            # 保存場所のパスを取得
            self.config_data.read('config.ini')
            save_path = self.config_data.get("DEFAULT", "clone_save_path", fallback=None)
            # 保存場所が存在しない場合はデスクトップに設定し設定ファイルに書き込む
            if not save_path:
                save_path = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
                # 既存の設定を読み込み、保存用のパスをデスクトップに指定
                self.config_data.read('config.ini')
                self.config_data.set("DEFAULT", "clone_save_path", save_path)
                # 設定を書き込む
                with open('config.ini', 'w') as configfile:
                    self.config_data.write(configfile)
            
            new_image_name = f"{file_name}_cleaned{file_extension}"
            output_path = os.path.join(save_path, new_image_name)

            if img.format == "PNG":
                # PNGのテキストチャンクを削除
                img_without_text = Image.new(img.mode, img.size)
                img_without_text.putdata(list(img.getdata()))
                img_without_text.save(output_path, "PNG")

                return save_path, new_image_name

            elif img.format == "WEBP":
                # WEBPのEXIFデータを削除
                img_without_exif = Image.new(img.mode, img.size)
                img_without_exif.putdata(list(img.getdata()))
                img_without_exif.save(output_path, "WEBP")

                return save_path, new_image_name

            else:
                raise ValueError(f"このファイルの形式（{img.format}）はサポートされていません。")

        except Exception as e:
            raise Exception(f"処理中にエラーが発生しました: {e}")