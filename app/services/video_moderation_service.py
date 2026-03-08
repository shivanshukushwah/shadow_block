import cv2
from moviepy import VideoFileClip
import os
from app.services.image_moderation_service import ImageModerationService
from app.services.audio_moderation_service import AudioModerationService
import logging

class VideoModerationService:
    def __init__(self):
        self.image_service = ImageModerationService()
        # defer audio service creation; audio models can be heavy
        self.audio_service: AudioModerationService | None = None

    def _get_audio_service(self) -> AudioModerationService | None:
        if self.audio_service is None:
            try:
                self.audio_service = AudioModerationService()
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to initialize AudioModerationService in VideoModerationService: {e}")
                self.audio_service = None
        return self.audio_service

    def extract_frames(self, video_path: str, frame_rate: int = 1):
        vidcap = cv2.VideoCapture(video_path)
        fps = vidcap.get(cv2.CAP_PROP_FPS)
        interval = int(fps // frame_rate)
        frames = []
        count = 0
        success, image = vidcap.read()
        while success:
            if count % interval == 0:
                frame_path = f"{video_path}_frame_{count}.jpg"
                cv2.imwrite(frame_path, image)
                frames.append(frame_path)
            success, image = vidcap.read()
            count += 1
        vidcap.release()
        return frames

    def extract_audio(self, video_path: str):
        video = VideoFileClip(video_path)
        audio_path = f"{video_path}_audio.wav"
        video.audio.write_audiofile(audio_path)
        return audio_path

    def moderate_video(self, video_path: str):
        # Extract frames and audio
        frames = self.extract_frames(video_path)
        audio_path = self.extract_audio(video_path)

        # Moderate frames (images)
        frame_results = []
        for frame in frames:
            result = self.image_service.classify_image_clip(frame)
            nsfw = self.image_service.classify_image_nsfw(frame)
            ocr_text = self.image_service.extract_text(frame)
            ocr_flagged = self.image_service.moderate_text(ocr_text) if ocr_text.strip() else False
            frame_results.append({
                "frame": frame,
                "clip_classification": result,
                "nsfw_classification": nsfw,
                "ocr_text": ocr_text,
                "ocr_text_flagged": ocr_flagged
            })
            os.remove(frame)  # Clean up

        # Moderate audio, if audio service initialized successfully
        audio_result = None
        audio_srv = self._get_audio_service()
        if audio_srv:
            transcript = audio_srv.transcribe(audio_path)
            anger_score = audio_srv.detect_anger(audio_path)
            abusive_detected = audio_srv.detect_abusive_content(transcript)
            audio_result = {
                "transcript": transcript,
                "anger_score": anger_score,
                "anger_detected": anger_score > 0.5,
                "abusive_detected": abusive_detected
            }
        os.remove(audio_path)  # Clean up

        # if audio service not available, audio_result stays None

        return {
            "frames_moderation": frame_results,
            "audio_moderation": audio_result
        }