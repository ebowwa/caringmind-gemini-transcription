import logging
import os
from typing import Dict, Optional
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from pydantic import BaseModel
import mimetypes
import base64

logger = logging.getLogger(__name__)

class VoiceCharacteristics(BaseModel):
    pattern: str
    style: str
    common_phrases: list[str]

class NameAnalysis(BaseModel):
    name: str
    prosody: str
    feeling: str
    confidence_score: int
    confidence_reasoning: str
    psychoanalysis: str
    location_background: str
    voice_characteristics: VoiceCharacteristics

class NameAnalysisService:
    SUPPORTED_MIME_TYPES = {
        'audio/wav': 'audio/wav',
        'audio/mp3': 'audio/mp3',
        'audio/aiff': 'audio/aiff',
        'audio/aac': 'audio/aac',
        'audio/ogg': 'audio/ogg',
        'audio/flac': 'audio/flac',
        # Add variations
        'wav': 'audio/wav',
        'mp3': 'audio/mp3',
        'aiff': 'audio/aiff',
        'aac': 'audio/aac',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac'
    }

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=self.api_key)
        
        self.generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_schema": content.Schema(
                type=content.Type.OBJECT,
                required=[
                    "name",
                    "prosody",
                    "feeling",
                    "confidence_score",
                    "confidence_reasoning",
                    "psychoanalysis",
                    "location_background",
                    "voice_characteristics"
                ],
                properties={
                    "name": content.Schema(type=content.Type.STRING, description="The user's full name."),
                    "prosody": content.Schema(type=content.Type.STRING, description="Speech analysis."),
                    "feeling": content.Schema(type=content.Type.STRING, description="Emotional tone."),
                    "confidence_score": content.Schema(type=content.Type.INTEGER, description="Confidence score."),
                    "confidence_reasoning": content.Schema(type=content.Type.STRING, description="Reasoning."),
                    "psychoanalysis": content.Schema(type=content.Type.STRING, description="Psychological insights."),
                    "location_background": content.Schema(type=content.Type.STRING, description="Environment details."),
                    "voice_characteristics": content.Schema(
                        type=content.Type.OBJECT,
                        description="Voice profile characteristics",
                        required=["pattern", "style", "common_phrases"],
                        properties={
                            "pattern": content.Schema(type=content.Type.STRING, description="Distinctive voice pattern features"),
                            "style": content.Schema(type=content.Type.STRING, description="Speaking style characteristics"),
                            "common_phrases": content.Schema(
                                type=content.Type.ARRAY,
                                description="Detected common phrases or speech patterns",
                                items=content.Schema(type=content.Type.STRING)
                            )
                        }
                    )
                }
            ),
            "response_mime_type": "application/json",
        }

    def _validate_audio_length(self, audio_data: bytes) -> bool:
        """Check if audio length is within Gemini limits"""
        # Gemini represents each second as 25 tokens
        # Maximum length is 9.5 hours = 34,200 seconds = 855,000 tokens
        audio_size = len(audio_data)
        estimated_seconds = audio_size / (16000 * 2)  # 16kHz, 16-bit
        estimated_tokens = estimated_seconds * 25
        
        return estimated_tokens <= 855000

    async def analyze_name_recording(self, audio_data: str, mime_type: str) -> NameAnalysis:
        """Perform deep analysis of name recording"""
        try:
            # Normalize mime type
            mime_type = mime_type.lower()
            if not mime_type.startswith('audio/'):
                mime_type = f'audio/{mime_type}'

            # Validate mime type
            if mime_type not in self.SUPPORTED_MIME_TYPES:
                raise ValueError(f"Unsupported mime type: {mime_type}. Supported types: {list(set(self.SUPPORTED_MIME_TYPES.values()))}")

            # Decode base64 and validate length
            decoded_audio = base64.b64decode(audio_data)
            if not self._validate_audio_length(decoded_audio):
                raise ValueError("Audio file too long. Maximum length is 9.5 hours.")

            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config=self.generation_config
            )

            # Create parts with proper mime type
            parts = [{
                "inline_data": {
                    "mime_type": self.SUPPORTED_MIME_TYPES[mime_type],
                    "data": audio_data
                }
            }, self._get_analysis_prompt()]

            # Count tokens (for debugging)
            token_count = model.count_tokens(parts)
            logger.debug(f"Total tokens for request: {token_count}")

            chat = model.start_chat(history=[{"role": "user", "parts": parts}])
            response = chat.send_message("Please analyze this recording")

            # Parse and validate response
            if isinstance(response.text, dict):
                result = response.text
            else:
                import json
                result = json.loads(response.text)

            # Create NameAnalysis object for validation
            return NameAnalysis(**result)

        except Exception as e:
            logger.error(f"Name analysis error: {e}", exc_info=True)
            raise ValueError(f"Failed to analyze name recording: {str(e)}")

    def _get_analysis_prompt(self) -> str:
        """Get the analysis prompt"""
        return """
        # Analysis Request
        Please analyze this name recording focusing on:
        1. Exact name transcription (00:00-end)
        2. Voice characteristics and patterns
        3. Emotional state and confidence
        4. Environmental context
        5. Speaking style and mannerisms

        Format as JSON with required fields:
        - name
        - prosody
        - feeling
        - confidence_score (0-100)
        - confidence_reasoning
        - psychoanalysis
        - location_background
        - voice_characteristics:
          - pattern
          - style  
          - common_phrases
        """
