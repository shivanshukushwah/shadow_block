import pytesseract
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel, AutoModelForImageClassification, AutoImageProcessor
import openai
import os
from app.core.config import settings

class ImageModerationService:
    def __init__(self):
        # Set HF token for authenticated downloads
        if settings.HF_TOKEN:
            os.environ['HF_TOKEN'] = settings.HF_TOKEN

        # CLIP for general image understanding
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch16")
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch16")
        # Specialized NSFW model
        self.nsfw_model = AutoModelForImageClassification.from_pretrained("Falconsai/nsfw_image_detection")
        self.processor = AutoImageProcessor.from_pretrained("Falconsai/nsfw_image_detection")
        # Expanded prompt list
        self.prompts = [
            "a photo of nudity",
            "a photo of pornography",
            "a photo of hate gesture",
            "a photo of violence",
            "a photo of drugs",
            "a photo of guns",
            "a photo of blood",
            "a photo of hate symbol",
            "a photo of racism",
            "a photo of safe content",
            "a meme with offensive text",
            "a meme with hate speech",
            "a safe photo"
        ]
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def extract_text(self, image_path: str) -> str:
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            print(f"OCR failed: {e}. Make sure tesseract is installed.")
            return ""

    def classify_image_clip(self, image_path: str) -> dict:
        img = Image.open(image_path).convert("RGB")
        inputs = self.clip_processor(text=self.prompts, images=img, return_tensors="pt", padding=True)
        outputs = self.clip_model(**inputs)
        logits_per_image = outputs.logits_per_image.softmax(dim=1)
        scores = logits_per_image[0].tolist()
        result = dict(zip(self.prompts, scores))
        label = self.prompts[scores.index(max(scores))]
        return {"scores": result, "label": label}

    def classify_image_nsfw(self, image_path: str) -> dict:
        img = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=img, return_tensors="pt")
        outputs = self.nsfw_model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=1)[0]
        labels = self.nsfw_model.config.id2label
        result = {labels[i]: float(probs[i]) for i in range(len(labels))}
        label = labels[int(torch.argmax(probs))]
        return {"scores": result, "label": label}

    def moderate_text(self, text: str) -> bool:
        try:
            response = openai.Moderation.create(input=text)
            flagged = response["results"][0]["flagged"]
            return flagged
        except Exception:
            return False