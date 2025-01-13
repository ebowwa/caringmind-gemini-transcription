import logging
from typing import Dict, Optional
from pydantic import BaseModel
import mimetypes
from .gemini_service import GeminiService, GeminiConfig
from google.ai.generativelanguage_v1beta.types import content

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
        """Initialize with custom Gemini configuration for name analysis"""
        config = GeminiConfig(
            temperature=0.8,  # Balanced between creativity and accuracy
            top_p=0.95,
            top_k=64,
            max_output_tokens=8192,
            model_name="gemini-1.5-flash"
        )
        self.gemini_service = GeminiService(config=config)

    def _create_name_analysis_schema(self) -> content.Schema:
        """Create schema for name analysis response"""
        return content.Schema(
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
        )

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

            analysis_prompt = """
            # Analysis Request
            Please analyze this name recording focusing on:
            1. Exact name transcription (00:00-end)
            2. Voice characteristics and patterns
            3. Emotional state and confidence
            4. Environmental context
            5. Speaking style and mannerisms
            """

            # Use the generic analyze_content method with audio mime type
            result = await self.gemini_service.analyze_content(
                content_data=audio_data,
                prompt=analysis_prompt,
                schema=self._create_name_analysis_schema(),
                mime_type=self.SUPPORTED_MIME_TYPES[mime_type]
            )

            # Create NameAnalysis object for validation
            return NameAnalysis(**result)

        except Exception as e:
            logger.error(f"Name analysis error: {e}", exc_info=True)
            raise ValueError(f"Failed to analyze name recording: {str(e)}")
