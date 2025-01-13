import os
import logging
import json
import google.generativeai as genai
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import List
from google.ai.generativelanguage_v1beta.types import content
import binascii
from fastapi.encoders import jsonable_encoder
import base64

logger = logging.getLogger(__name__)

class ToneAnalysis(BaseModel):
    tone: str
    indicators: List[str]

class ConversationTurn(BaseModel):
    diarization_html: str
    transcription_html: str
    timestamps_html: str
    tone_analysis: ToneAnalysis
    confidence: float
    summary: str

class TranscriptionResponse(BaseModel):
    full_audio_transcribed: bool
    conversation_analysis: List[ConversationTurn]

class GeminiService:
    def __init__(self, model_name="gemini-1.5-flash"):
        self.model_name = model_name

    def _create_generation_config(self, schema):
        return {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_schema": schema,
            "response_mime_type": "application/json",
        }

    def _ensure_base64(self, data) -> str:
        """Convert input to base64 string if needed"""
        if isinstance(data, str):
            try:
                # Verify it's valid base64
                base64.b64decode(data)
                return data
            except:
                raise ValueError("Invalid base64 string provided")
        elif isinstance(data, bytes):
            return base64.b64encode(data).decode('utf-8')
        else:
            raise ValueError("Input must be base64 string or bytes")

    async def analyze_audio(self, audio_data, prompt: str, schema: content.Schema) -> dict:
        """Generic method to analyze audio using Gemini
        
        Args:
            audio_data: Either base64 string or raw bytes
            prompt: Analysis prompt
            schema: Response schema
        """
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=self._create_generation_config(schema)
            )

            # Convert input to base64 if needed
            encoded_audio = self._ensure_base64(audio_data)

            chat = model.start_chat(history=[{
                "role": "user",
                "parts": [{
                    "inline_data": {
                        "mime_type": "audio/wav",
                        "data": encoded_audio
                    }
                }, prompt]
            }])

            response = chat.send_message("Analyze this audio comprehensively")
            
            if isinstance(response.text, dict):
                result = response.text
            else:
                result = json.loads(response.text)

            return result

        except ValueError as e:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Gemini analysis error: {e}", exc_info=True)
            raise ValueError(f"Failed to analyze audio: {str(e)}")

class GeminiServiceWrapper:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=self.api_key)
        
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
