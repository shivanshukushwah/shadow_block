# Try to import whisper, fallback if not available
try:
    import whisper
    WHISPER_AVAILABLE = True
except (ImportError, TypeError) as e:
    WHISPER_AVAILABLE = False
    whisper = None
    print(f"Whisper import failed: {e}")

import librosa
import numpy as np
import logging

logger = logging.getLogger(__name__)

class AudioModerationService:
    def __init__(self):
        # Delay loading the Whisper model until it's actually needed.
        self.model = None

    def _ensure_model(self):
        if self.model is None:
            if not WHISPER_AVAILABLE:
                raise ImportError("Whisper not available - audio transcription disabled")
            try:
                logger.info("Loading Whisper audio model...")
                self.model = whisper.load_model("base")
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load Whisper model: {e}")
                # propagate so callers can decide how to handle it
                raise

    def transcribe(self, audio_path: str) -> str:
        # model load may raise; caller should handle/convert to HTTPException
        self._ensure_model()
        result = self.model.transcribe(audio_path)
        return result["text"]

    def detect_anger(self, audio_path: str) -> float:
        y, sr = librosa.load(audio_path, sr=None)
        # Example: Use zero-crossing rate and spectral features as a proxy for anger
        zcr = np.mean(librosa.feature.zero_crossing_rate(y))
        rms = np.mean(librosa.feature.rms(y))
        # Simple heuristic: higher ZCR and RMS may indicate anger
        anger_score = (zcr + rms) * 10
        return anger_score