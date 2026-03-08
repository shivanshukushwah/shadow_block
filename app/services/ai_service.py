import logging
# from transformers import BertTokenizer, BertForSequenceClassification, pipeline
import socketio
# from app.services.image_moderation_service import ImageModerationService

# Configure logging
logger = logging.getLogger(__name__)

# Try to load ML models, fallback to simple logic if not available
try:
    from transformers import pipeline
    moderation_pipeline = pipeline("text-classification", model="unitary/toxic-bert")
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    moderation_pipeline = None

def moderate_text_simple(text: str):
    result = moderation_pipeline(text)
    # result[0]['label'] can be 'TOXIC' or 'NON_TOXIC'
    is_abusive = result[0]['label'] == 'TOXIC'
    return {"is_abusive": is_abusive, "score": result[0]['score']}

class AIService:
    def __init__(self):
        self.load_models()
        self.sio = socketio.Client()
        self.sio.on('model_retrained', self.on_model_retrained)
        # self.image_service = ImageModerationService()  # Initialize image service

    def connect_socket(self):
        self.sio.connect("http://localhost:8000")

    def load_models(self):
        # For text: Only load if transformers is available
        try:
            from transformers import BertForSequenceClassification, BertTokenizer
            self.text_model = BertForSequenceClassification.from_pretrained("bert-base-uncased")
            self.text_tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
        except ImportError:
            self.text_model = None
            self.text_tokenizer = None
        # For image/audio/video, load respective models

    def on_model_retrained(self, data):
        print("Model retrained event received, reloading models...")
        self.load_models()

    def predict_text(self, text):
        inputs = self.text_tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        outputs = self.text_model(**inputs)
        pred = outputs.logits.argmax(dim=1).item()
        return pred

    async def initialize_models(self):
        # ...your model loading logic...
        self.load_models()
    
    async def moderate_text(self, text: str):
        """Moderate text using the toxic-bert pipeline"""
        if not ML_AVAILABLE or moderation_pipeline is None:
            # Fallback to simple keyword-based moderation
            toxic_keywords = ['fuck', 'shit', 'damn', 'bitch', 'asshole', 'bastard', 'crap', 'piss']
            is_toxic = any(keyword in text.lower() for keyword in toxic_keywords)
            confidence = 0.8 if is_toxic else 0.2
            
            return {
                "is_toxic": is_toxic,
                "action": "block" if is_toxic else "approve",
                "confidence": confidence,
                "violations": ["toxic"] if is_toxic else [],
                "explanation": f"Simple keyword-based moderation: {'toxic' if is_toxic else 'safe'}"
            }
        
        try:
            result = moderation_pipeline(text)
            logger.info(f"Pipeline result: {result}")  # Debug log
            
            # result[0] contains {'label': 'toxic'/'not_toxic', 'score': float}
            label = result[0]['label'].lower()
            score = result[0]['score']
            
            # If score >= 0.5, the model is confident it's toxic
            # If score < 0.5, the model is confident it's safe
            is_toxic = score >= 0.5
            
            logger.info(f"Text: {text[:50]}... | Label: {label} | Score: {score:.4f} | Is Toxic: {is_toxic}")
            
            return {
                "is_toxic": is_toxic,
                "action": "block" if is_toxic else "approve",
                "confidence": score,
                "violations": ["toxic"] if is_toxic else [],
                "explanation": f"Content classified as {label} with confidence {score:.2f}"
            }
        except Exception as e:
            logger.error(f"Error in text moderation: {e}", exc_info=True)
            return {
                "is_toxic": False,
                "action": "approve",
                "confidence": 0.5,
                "violations": [],
                "explanation": f"Moderation error: {str(e)}"
            }

    async def moderate_image(self, image_path: str):
        """Moderate image using CLIP and NSFW models"""
        # Check if image service is available
        if not hasattr(self, 'image_service') or self.image_service is None:
            return {
                "is_toxic": False,
                "action": "approve",
                "confidence": 0.5,
                "violations": [],
                "explanation": "Image moderation service not available - ML dependencies missing",
                "details": {}
            }
        
        try:
            # Extract text from image (if OCR available)
            ocr_text = self.image_service.extract_text(image_path)
            
            # Classify with CLIP
            clip_result = self.image_service.classify_image_clip(image_path)
            
            # Classify with NSFW model
            nsfw_result = self.image_service.classify_image_nsfw(image_path)
            
            # Check OCR text for toxicity
            ocr_toxic = False
            if ocr_text.strip():
                ocr_moderation = await self.moderate_text(ocr_text)
                ocr_toxic = ocr_moderation["is_toxic"]
            
            # Determine if image is inappropriate
            # Check NSFW scores
            nsfw_scores = nsfw_result["scores"]
            is_nsfw = any(score > 0.5 for label, score in nsfw_scores.items() 
                         if label.lower() in ['nsfw', 'porn', 'hentai', 'sexy'])
            
            # Check CLIP scores for inappropriate content
            clip_scores = clip_result["scores"]
            inappropriate_clip = any(score > 0.5 for prompt, score in clip_scores.items()
                                   if any(word in prompt.lower() for word in 
                                         ['nudity', 'pornography', 'violence', 'drugs', 'guns', 'blood', 'hate']))
            
            # Overall decision
            is_inappropriate = is_nsfw or inappropriate_clip or ocr_toxic
            
            violations = []
            if is_nsfw:
                violations.append("nsfw")
            if inappropriate_clip:
                violations.append("inappropriate_content")
            if ocr_toxic:
                violations.append("toxic_text")
            
            confidence = max(
                max(nsfw_scores.values()) if nsfw_scores else 0,
                max(clip_scores.values()) if clip_scores else 0,
                0.5 if ocr_toxic else 0
            )
            
            return {
                "is_toxic": is_inappropriate,
                "action": "block" if is_inappropriate else "approve",
                "confidence": confidence,
                "violations": violations,
                "explanation": f"Image moderation: NSFW={is_nsfw}, Inappropriate={inappropriate_clip}, OCR Toxic={ocr_toxic}",
                "details": {
                    "ocr_text": ocr_text,
                    "clip_classification": clip_result,
                    "nsfw_classification": nsfw_result
                }
            }
        except Exception as e:
            logger.error(f"Error in image moderation: {e}", exc_info=True)
            return {
                "is_toxic": False,
                "action": "approve",
                "confidence": 0.5,
                "violations": [],
                "explanation": f"Image moderation error: {str(e)}",
                "details": {}
            }

    async def moderate_audio(self, audio_path: str):
        """Placeholder for audio moderation"""
        return {
            "is_toxic": False,
            "action": "approve",
            "confidence": 0.5,
            "violations": [],
            "explanation": "Audio moderation not yet implemented",
            "details": {}
        }

    async def moderate_video(self, video_path: str):
        """Placeholder for video moderation"""
        return {
            "is_toxic": False,
            "action": "approve",
            "confidence": 0.5,
            "violations": [],
            "explanation": "Video moderation not yet implemented",
            "details": {}
        }
        """Moderate text using the toxic-bert pipeline"""
        try:
            result = moderation_pipeline(text)
            logger.info(f"Pipeline result: {result}")  # Debug log
            
            # result[0] contains {'label': 'toxic'/'not_toxic', 'score': float}
            label = result[0]['label'].lower()
            score = result[0]['score']
            
            # If score >= 0.5, the model is confident it's toxic
            # If score < 0.5, the model is confident it's safe
            is_toxic = score >= 0.5
            
            logger.info(f"Text: {text[:50]}... | Label: {label} | Score: {score:.4f} | Is Toxic: {is_toxic}")
            
            return {
                "is_toxic": is_toxic,
                "action": "block" if is_toxic else "approve",
                "confidence": score,
                "violations": ["toxic"] if is_toxic else [],
                "explanation": f"Content classified as {label} with confidence {score:.2f}"
            }
        except Exception as e:
            logger.error(f"Error in text moderation: {e}", exc_info=True)
            return {
                "is_toxic": False,
                "action": "approve",
                "confidence": 0.5,
                "violations": [],
                "explanation": f"Moderation error: {str(e)}"
            }


