import base64
import binascii
import logging
import uuid
import os
from typing import Tuple, Union
from pathlib import Path
from services.audio_validation import AudioValidator # validates if speech is present
import subprocess

logger = logging.getLogger(__name__)

class AudioUploadService:
    SUPPORTED_MIME_TYPES = {
        'audio/wav': ('wav', 'audio/wav'),
        'audio/mp3': ('mp3', 'audio/mp3'),
        'audio/aiff': ('aiff', 'audio/aiff'),
        'audio/aac': ('aac', 'audio/aac'),
        'audio/ogg': ('ogg', 'audio/ogg'),
        'audio/flac': ('flac', 'audio/flac')
    }
    UPLOAD_DIR = Path("uploads")

    @classmethod
    async def process_upload(cls, audio_data: str) -> Tuple[str, int, bool, float]:
        """Process uploaded audio data"""
        temp_path = wav_path = None
        try:
            # Handle different input types safely
            if isinstance(audio_data, bytes):
                try:
                    # Try UTF-8 first
                    audio_data = audio_data.decode('utf-8')
                except UnicodeDecodeError:
                    # If UTF-8 fails, assume it's already binary data
                    decoded_data = audio_data
            else:
                try:
                    decoded_data = base64.b64decode(audio_data)
                except (binascii.Error, TypeError) as e:
                    logger.error(f"Base64 decode error: {e}")
                    raise ValueError("Invalid audio data format")

            size = len(decoded_data)
            
            cls.UPLOAD_DIR.mkdir(exist_ok=True)
            file_id = str(uuid.uuid4())
            
            # Save raw data first
            temp_path = cls.UPLOAD_DIR / f"{file_id}.raw"
            with open(temp_path, "wb") as f:
                f.write(decoded_data)

            # Modify ffmpeg conversion to maintain original format if supported
            mime_type = cls._detect_mime_type(decoded_data)
            if mime_type not in cls.SUPPORTED_MIME_TYPES:
                # Convert to WAV if unsupported format
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
            else:
                # Keep original format if supported
                ext, _ = cls.SUPPORTED_MIME_TYPES[mime_type]
                output_path = cls.UPLOAD_DIR / f"{file_id}.{ext}"
                with open(output_path, "wb") as f:
                    f.write(decoded_data)

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

    @classmethod
    def safe_decode(cls, data: Union[str, bytes]) -> bytes:
        """Safely decode input data to bytes"""
        if isinstance(data, bytes):
            return data
        try:
            return base64.b64decode(data)
        except (binascii.Error, TypeError):
            raise ValueError("Invalid data format")

    @classmethod
    def _detect_mime_type(cls, audio_data: bytes) -> str:
        """Detect mime type from audio data"""
        import magic
        mime = magic.Magic(mime=True)
        return mime.from_buffer(audio_data)
