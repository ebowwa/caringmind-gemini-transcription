import os
import logging
from typing import Any, Dict, Optional, Union, List, Type
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import base64

logger = logging.getLogger(__name__)

# Base Response Models
class BaseResponse(BaseModel):
    """Base class for all Gemini responses"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToneAnalysis(BaseResponse):
    """Analysis of tone and emotional content"""
    tone: str
    indicators: List[str]
    confidence_score: Optional[float] = None
    additional_metrics: Optional[Dict[str, Any]] = None

class ConversationTurn(BaseResponse):
    """Individual turn in a conversation"""
    diarization_html: Optional[str] = None
    transcription_html: Optional[str] = None
    timestamps_html: Optional[str] = None
    tone_analysis: Optional[ToneAnalysis] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    segments: Optional[List[Dict[str, Any]]] = None

class TranscriptionResponse(BaseModel):
    """Complete transcription analysis response"""
    full_audio_transcribed: bool
    conversation_analysis: List[ConversationTurn]
    metadata: Optional[Dict[str, Any]] = None
    processing_stats: Optional[Dict[str, Any]] = None

class GeminiConfig(BaseModel):
    """Base configuration for Gemini API calls"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 64
    max_output_tokens: int = 8192
    model_name: str = "gemini-1.5-flash"
    response_mime_type: str = "application/json"
    response_schema: Optional[content.Schema] = None

class TranscriptionConfig(GeminiConfig):
    """Specific configuration for transcription use case"""
    temperature: float = 0.7  # Lower temperature for more focused responses
    model_name: str = "gemini-1.5-flash"
    
    def __init__(self, **data):
        data['response_schema'] = self._create_schema()
        super().__init__(**data)
        
    def _create_schema(self) -> content.Schema:
        """Generate the transcription schema"""
        return content.Schema(
            type=content.Type.OBJECT,
            required=["full_audio_transcribed", "conversation_analysis"],
            properties={
                "full_audio_transcribed": content.Schema(
                    type=content.Type.BOOLEAN,
                    description="Indicates if the entire audio file has been transcribed."
                ),
                "conversation_analysis": content.Schema(
                    type=content.Type.ARRAY,
                    description="List of analyzed turns in the conversation.",
                    items=content.Schema(
                        type=content.Type.OBJECT,
                        required=["diarization_html", "transcription_html", "timestamps_html", 
                                 "tone_analysis", "confidence", "summary"],
                        properties={
                            "diarization_html": content.Schema(
                                type=content.Type.STRING,
                                description="HTML structure indicating the speaker label."
                            ),
                            "transcription_html": content.Schema(
                                type=content.Type.STRING,
                                description="HTML structure for the verbatim transcription."
                            ),
                            "timestamps_html": content.Schema(
                                type=content.Type.STRING,
                                description="HTML structure indicating approximate time range."
                            ),
                            "tone_analysis": content.Schema(
                                type=content.Type.OBJECT,
                                description="Analysis of the speaker's tone.",
                                required=["tone", "indicators"],
                                properties={
                                    "tone": content.Schema(
                                        type=content.Type.STRING,
                                        description="The dominant tone identified."
                                    ),
                                    "indicators": content.Schema(
                                        type=content.Type.ARRAY,
                                        description="Supporting details for the identified tone.",
                                        items=content.Schema(type=content.Type.STRING)
                                    )
                                }
                            ),
                            "confidence": content.Schema(
                                type=content.Type.NUMBER,
                                description="Confidence score for the tone detection."
                            ),
                            "summary": content.Schema(
                                type=content.Type.STRING,
                                description="Concise summary of the speaker's contribution."
                            )
                        }
                    )
                )
            }
        )

class GeminiService:
    """
    Abstract interface for Gemini API interactions.
    Handles configuration, authentication, and provides a clean API for various Gemini operations.
    """
    
    def __init__(self, config: Optional[GeminiConfig] = None):
        """Initialize service with optional custom configuration"""
        self.config = config or GeminiConfig()
        self._setup_api()
        
    def _setup_api(self) -> None:
        """Configure Gemini API with authentication"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        
    def _create_generation_config(self) -> Dict[str, Any]:
        """Create generation configuration using service config"""
        config = {
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "max_output_tokens": self.config.max_output_tokens,
            "response_mime_type": self.config.response_mime_type,
        }
        
        # Get the actual schema object if it's a property
        if hasattr(self.config, 'response_schema'):
            schema = self.config.response_schema
            if isinstance(schema, property):
                schema = schema.fget(self.config)
            config["response_schema"] = schema
            
        return config

    def _ensure_base64(self, data: Union[str, bytes]) -> str:
        """Ensure data is properly base64 encoded"""
        if isinstance(data, str):
            try:
                base64.b64decode(data)
                return data
            except:
                raise ValueError("Invalid base64 string provided")
        elif isinstance(data, bytes):
            return base64.b64encode(data).decode('utf-8')
        raise ValueError("Input must be base64 string or bytes")

    async def analyze_content(self, 
                            content_data: Union[str, bytes],
                            prompt: str,
                            response_model: Optional[Type[BaseModel]] = None,
                            mime_type: str = "audio/wav") -> Union[Dict[str, Any], BaseModel]:
        """
        Generic content analysis method supporting various content types
        
        Args:
            content_data: Raw content as base64 string or bytes
            prompt: Analysis prompt
            response_model: Optional Pydantic model for response validation
            mime_type: Content MIME type
            
        Returns:
            Analysis results as dict or specified response model
        """
        try:
            model = genai.GenerativeModel(
                model_name=self.config.model_name,
                generation_config=self._create_generation_config()
            )

            encoded_content = self._ensure_base64(content_data)
            
            chat = model.start_chat(history=[{
                "role": "user",
                "parts": [{
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": encoded_content
                    }
                }, prompt]
            }])

            response = chat.send_message("Analyze this content")
            result = response.text if isinstance(response.text, dict) else response.json()
            
            return response_model(**result) if response_model else result

        except Exception as e:
            logger.error(f"Content analysis error: {e}", exc_info=True)
            raise ValueError(f"Analysis failed: {str(e)}")

    @classmethod
    def create_transcription_service(cls) -> 'GeminiService':
        """Factory method for creating a transcription-specific service"""
        return cls(config=TranscriptionConfig())

    async def analyze_audio(self, 
                          audio_data: Union[str, bytes],
                          prompt: str) -> TranscriptionResponse:
        """
        Specialized method for audio analysis using transcription configuration
        
        Returns:
            TranscriptionResponse object containing the analysis
        """
        return await self.analyze_content(
            content_data=audio_data,
            prompt=prompt,
            response_model=TranscriptionResponse,
            mime_type="audio/wav"
        )

    async def analyze_text(self,
                         text: str,
                         prompt: str) -> Dict[str, Any]:
        """Specialized method for text analysis"""
        try:
            model = genai.GenerativeModel(
                model_name=self.config.model_name,
                generation_config=self._create_generation_config()
            )
            
            chat = model.start_chat(history=[{
                "role": "user",
                "parts": [text, prompt]
            }])
            
            response = chat.send_message("Analyze this text")
            return response.text if isinstance(response.text, dict) else response.json()
            
        except Exception as e:
            logger.error(f"Text analysis error: {e}", exc_info=True)
            raise ValueError(f"Analysis failed: {str(e)}")

class GeminiServiceWrapper:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=self.api_key)
        # this config is specific to the transcription use case not all gemini requests.. we also have _create_name_analysis_schema and will be expanding
        self.generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_schema": content.Schema(
                type=content.Type.OBJECT,
                enum=[],
                required=["full_audio_transcribed", "conversation_analysis"],
                properties={
                    "full_audio_transcribed": content.Schema(
                        type=content.Type.BOOLEAN,
                        description="Indicates if the entire audio file has been transcribed.",
                    ),
                    "conversation_analysis": content.Schema(
                        type=content.Type.ARRAY,
                        description="List of analyzed turns in the conversation.",
                        items=content.Schema(
                            type=content.Type.OBJECT,
                            enum=[],
                            required=["diarization_html", "transcription_html", "timestamps_html", "tone_analysis", "confidence", "summary"],
                            properties={
                                "diarization_html": content.Schema(
                                    type=content.Type.STRING,
                                    description="HTML structure indicating the speaker label.",
                                ),
                                "transcription_html": content.Schema(
                                    type=content.Type.STRING,
                                    description="HTML structure for the verbatim transcription.",
                                ),
                                "timestamps_html": content.Schema(
                                    type=content.Type.STRING,
                                    description="HTML structure indicating approximate time range.",
                                ),
                                "tone_analysis": content.Schema(
                                    type=content.Type.OBJECT,
                                    description="Analysis of the speaker's tone.",
                                    enum=[],
                                    required=["tone", "indicators"],
                                    properties={
                                        "tone": content.Schema(
                                            type=content.Type.STRING,
                                            description="The dominant tone identified.",
                                        ),
                                        "indicators": content.Schema(
                                            type=content.Type.ARRAY,
                                            description="Supporting details for the identified tone.",
                                            items=content.Schema(
                                                type=content.Type.STRING,
                                                description="A specific indicator of the tone.",
                                            ),
                                        ),
                                    },
                                ),
                                "confidence": content.Schema(
                                    type=content.Type.NUMBER,
                                    description="Confidence score for the tone detection.",
                                ),
                                "summary": content.Schema(
                                    type=content.Type.STRING,
                                    description="Concise summary of the speaker's contribution.",
                                ),
                            },
                        ),
                    ),
                },
            ),
            "response_mime_type": "application/json",
        }

    async def analyze_audio(self, audio_data, prompt: str = None, schema: content.Schema = None) -> dict:
        """Process audio through Gemini model and return analysis
        
        Args:
            audio_data: Either base64 string, bytes, or file-like object
            prompt: Custom analysis prompt (optional)
            schema: Custom response schema (optional)
        """
        try:
            # Use internal gemini service with standardized interface
            gemini_service = GeminiService(model_name="gemini-2.0-flash-exp")
            
            # Use default schema if none provided
            schema = schema or self.generation_config["response_schema"]
            
            # Use default prompt if none provided
            prompt = prompt or """Please transcribe only what is actually spoken..."""
            
            return await gemini_service.analyze_audio(
                audio_data=audio_data,
                prompt=prompt,
                schema=schema
            )

        except Exception as e:
            logger.error(f"Gemini analysis error: {e}", exc_info=True)
            return self.get_empty_response()

    def get_empty_response(self) -> dict:
        """Return a valid empty response"""
        return {
            "full_audio_transcribed": False,
            "conversation_analysis": []
        }
