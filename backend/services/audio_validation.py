import webrtcvad
import wave
import logging
from pathlib import Path
from typing import Tuple
import numpy as np

logger = logging.getLogger(__name__)

class AudioValidator:
    def __init__(self, aggressiveness: int = 3):  # Maximum aggressiveness for clearest speech
        self.vad = webrtcvad.Vad(aggressiveness)
        logger.info(f"Initialized VAD with aggressiveness {aggressiveness}")
    
    def validate_wav(self, audio_path: Path) -> Tuple[bool, float]:
        logger.info(f"Starting validation of {audio_path}")
        try:
            with wave.open(str(audio_path), 'rb') as wf:
                # Log wave file properties
                logger.debug(f"Wave properties: channels={wf.getnchannels()}, "
                           f"width={wf.getsampwidth()}, "
                           f"rate={wf.getframerate()}, "
                           f"frames={wf.getnframes()}")
                
                # Validate wave format
                if wf.getnchannels() != 1:
                    logger.error("Audio must be mono")
                    return False, 0.0
                if wf.getsampwidth() != 2:
                    logger.error("Audio must be 16-bit")
                    return False, 0.0
                if wf.getframerate() != 16000:
                    logger.error("Sample rate must be 16kHz")
                    return False, 0.0

                # Read all frames at once
                frames = wf.readframes(wf.getnframes())
                audio_data = np.frombuffer(frames, dtype=np.int16)
                
                # More strict volume threshold
                if np.max(np.abs(audio_data)) < 1000:
                    logger.warning("Audio too quiet")
                    return False, 0.0

                frame_duration = 10  # Shorter frames for more precise detection
                samples_per_frame = int(16000 * frame_duration / 1000)
                frame_size = samples_per_frame * 2

                windows = []  # Use sliding windows for better detection
                window_size = 5  # Check 5 frames at a time
                
                total_frames = 0
                speech_frames = 0
                window = []

                for start in range(0, len(frames), frame_size):
                    chunk = frames[start:start + frame_size]
                    if len(chunk) == frame_size:
                        total_frames += 1
                        try:
                            is_speech = self.vad.is_speech(chunk, 16000)
                            window.append(is_speech)
                            if len(window) > window_size:
                                window.pop(0)
                            # Count as speech if majority of window is speech
                            if len(window) == window_size and sum(window) >= 3:
                                speech_frames += 1
                        except Exception as e:
                            logger.debug(f"Frame error: {e}")
                            continue

                speech_ratio = speech_frames / total_frames if total_frames > 0 else 0
                has_speech = speech_ratio > 0.08  # More permissive ratio but stricter detection
                
                logger.info(f"Speech detection: {speech_frames}/{total_frames} frames "
                          f"({speech_ratio:.1%}) {'VALID' if has_speech else 'INVALID'}")
                return has_speech, speech_ratio

        except Exception as e:
            logger.error(f"VAD error: {str(e)}", exc_info=True)
            return False, 0.0
