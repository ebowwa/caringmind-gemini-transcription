import base64
import logging
import uuid
import os
from typing import Tuple
from pathlib import Path
from services.audio_validation import AudioValidator
import subprocess

logger = logging.getLogger(__name__)

class AudioUploadService:
    UPLOAD_DIR = Path("uploads")

    @classmethod
    async def process_upload(cls, audio_base64: str) -> Tuple[str, float, bool, float]:
        """Process uploaded audio data"""
        temp_path = wav_path = None
        try:
            audio_data = base64.b64decode(audio_base64)
            size = len(audio_data)
            
            cls.UPLOAD_DIR.mkdir(exist_ok=True)
            file_id = str(uuid.uuid4())
            
            # Save raw data first
            temp_path = cls.UPLOAD_DIR / f"{file_id}.raw"
            with open(temp_path, "wb") as f:
                f.write(audio_data)

            # Convert to properly formatted WAV
            wav_path = cls.UPLOAD_DIR / f"{file_id}.wav"
            try:
                result = subprocess.run([
                    'ffmpeg',
                    '-i', str(temp_path),
                    '-acodec', 'pcm_s16le',
                    '-ac', '1',
                    '-ar', '16000',
                    '-filter:a', 'volume=2.0',  # Normalize audio
                    '-y',
                    str(wav_path)
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg error: {result.stderr}")
                    raise ValueError("Audio conversion failed")
                    
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg process error: {e.stderr}")
                raise ValueError("Audio conversion failed")

            # Optional: Debug playback
            if os.getenv("DEBUG_AUDIO") == "1":
                subprocess.run(['aplay', str(wav_path)])

            # Single validation pass
            validator = AudioValidator()
            has_speech, speech_ratio = validator.validate_wav(wav_path)
            logger.info(f"Audio validation for {file_id}: has_speech={has_speech}, speech_ratio={speech_ratio:.2f}")

            # Keep files for now, just log
            if not has_speech:
                logger.warning(f"Low speech content in {file_id}: {speech_ratio:.1%}")
                
            return file_id, size, has_speech, speech_ratio

        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            # Cleanup on error
            for path in [temp_path, wav_path]:
                if path and path.exists():
                    path.unlink()
            raise ValueError(str(e))

    @classmethod
    def get_audio_path(cls, file_id: str) -> Path:
        """Get path to WAV file"""
        path = cls.UPLOAD_DIR / f"{file_id}.wav"
        if not path.exists():
            logger.error(f"WAV file not found: {path}")
            raise FileNotFoundError(f"No audio file found for ID: {file_id}")
        return path
