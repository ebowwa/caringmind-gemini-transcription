import os
import logging
import json
import base64
import binascii
from typing import Optional
from fastapi import APIRouter, HTTPException
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from pydantic import BaseModel, Field
from datetime import datetime
from services.audio_upload import AudioUploadService
from services.audio_validation import AudioValidator  # Add this import
from services.gemini_service import GeminiService
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["audio-processing"],
    responses={404: {"description": "Not found"}},
)

# Base models for extensibility
class BaseAnalysis(BaseModel):
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = Field(default_factory=dict)

class BaseRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_metadata: Optional[dict] = Field(default_factory=dict)

class ToneAnalysis(BaseAnalysis):
    tone: str
    indicators: list[str]
    confidence_score: Optional[float] = None
    additional_metrics: Optional[dict] = None

class ConversationTurn(BaseAnalysis):
    diarization_html: Optional[str] = None
    transcription_html: Optional[str] = None
    timestamps_html: Optional[str] = None
    tone_analysis: Optional[ToneAnalysis] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    raw_data: Optional[dict] = None
    segments: Optional[list[dict]] = None

class TranscriptionResponse(BaseModel):
    full_audio_transcribed: bool
    conversation_analysis: list[ConversationTurn]
    metadata: Optional[dict] = None
    processing_stats: Optional[dict] = None

class AudioRequest(BaseRequest):
    audio_base64: str
    audio_format: Optional[str] = None
    processing_options: Optional[dict] = None

class UploadResponse(BaseModel):
    file_id: Optional[str] = None
    size: int
    is_valid: bool
    analysis: Optional[TranscriptionResponse] = None
    upload_metadata: Optional[dict] = None

class AnalysisRequest(BaseRequest):
    file_id: str
    analysis_options: Optional[dict] = None

def create_transcription_schema():
    """Create schema for transcription response"""
    return content.Schema(
        type=content.Type.OBJECT,
        required=["full_audio_transcribed", "conversation_analysis"],
        properties={
            "full_audio_transcribed": content.Schema(
                type=content.Type.BOOLEAN,
                description="Indicates if the entire audio was successfully transcribed"
            ),
            "conversation_analysis": content.Schema(
                type=content.Type.ARRAY,
                description="List of analyzed conversation turns",
                items=content.Schema(
                    type=content.Type.OBJECT,
                    required=[
                        "diarization_html",
                        "transcription_html",
                        "timestamps_html",
                        "tone_analysis",
                        "confidence",
                        "summary"
                    ],
                    properties={
                        "diarization_html": content.Schema(
                            type=content.Type.STRING,
                            description="Speaker identification in HTML format"
                        ),
                        "transcription_html": content.Schema(
                            type=content.Type.STRING,
                            description="Transcribed text in HTML format"
                        ),
                        "timestamps_html": content.Schema(
                            type=content.Type.STRING,
                            description="Timestamp markers in HTML format"
                        ),
                        "tone_analysis": content.Schema(
                            type=content.Type.OBJECT,
                            required=["tone", "indicators"],
                            properties={
                                "tone": content.Schema(
                                    type=content.Type.STRING,
                                    description="Identified emotional tone"
                                ),
                                "indicators": content.Schema(
                                    type=content.Type.ARRAY,
                                    items=content.Schema(type=content.Type.STRING),
                                    description="Evidence supporting tone analysis"
                                )
                            }
                        ),
                        "confidence": content.Schema(
                            type=content.Type.NUMBER,
                            description="Confidence score for the analysis"
                        ),
                        "summary": content.Schema(
                            type=content.Type.STRING,
                            description="Brief summary of the conversation turn"
                        )
                    }
                )
            )
        }
    )

@router.post("/upload")
async def upload_audio(request: AudioRequest):
    """Handle file upload and analysis with context"""
    try:
        # Handle potential binary data
        if isinstance(request.audio_base64, bytes):
            try:
                request.audio_base64 = request.audio_base64.decode('utf-8')
            except UnicodeDecodeError:
                request.audio_base64 = base64.b64encode(request.audio_base64).decode('utf-8')

        # Process upload
        file_id, size, is_valid, speech_ratio = await AudioUploadService.process_upload(request.audio_base64)
        
        if not is_valid:
            return TranscriptionResponse(
                full_audio_transcribed=False,
                conversation_analysis=[]
            )

        file_path = AudioUploadService.get_audio_path(file_id)
        with open(file_path, "rb") as f:
            audio_data = f.read()

        gemini_service = GeminiService()
        transcription_prompt = """
        Please transcribe and analyze this audio clip. For each speaker turn:
        1. Identify the speaker
        2. Transcribe their exact words
        3. Note the approximate timestamp
        4. Analyze their tone
        5. Provide a brief summary
        
        Format using HTML tags as specified in the schema.
        Focus on accuracy and clarity.
        """

        return await gemini_service.analyze_audio(
            audio_data=audio_data,
            prompt=transcription_prompt,
            schema=create_transcription_schema()
        )

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
