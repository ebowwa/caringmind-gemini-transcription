import logging
import tempfile
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from services.speaker_profile import SpeakerProfile, SpeakerCharacteristics, SpeakerProfileService
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
import os
import json
import base64
import uuid
from services.gemini_service import GeminiService
from enum import Enum

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/speaker-profiles",  # Remove api/v1 prefix
    tags=["speaker-profiles"],
)

speaker_service = SpeakerProfileService()
gemini_service = GeminiService()

# Keep existing model definitions but add voice analysis fields
class SpeakerProfileResponse(BaseModel):
    user_id: str
    name: str
    prosody: str
    feeling: str
    confidence_score: int
    confidence_reasoning: str
    psychoanalysis: str
    location_background: str
    voice_characteristics: dict
    profile_created: bool = False

# Add request model to match iOS client
class SpeakerProfileRequest(BaseModel):
    audio_base64: str
    timestamp: str
    metadata: dict[str, str]

class TranscriptionResponse(BaseModel):
    transcript: str
    summary: str
    key_points: List[str]
    sentiment: str
    speaker_count: int
    speaker_characteristics: dict

class AnalysisType(str, Enum):
    NAME = "name"
    TRANSCRIPTION = "transcription"

ANALYSIS_SCHEMAS = {
    AnalysisType.NAME: content.Schema(
        type=content.Type.OBJECT,
        required=["name", "prosody", "feeling", "confidence_score", 
                 "confidence_reasoning", "psychoanalysis", 
                 "location_background", "voice_characteristics"],
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
    AnalysisType.TRANSCRIPTION: content.Schema(
        type=content.Type.OBJECT,
        required=["transcript", "summary", "key_points", 
                 "sentiment", "speaker_count", "speaker_characteristics"],
        properties={
            "transcript": content.Schema(type=content.Type.STRING, description="Complete transcription of the audio."),
            "summary": content.Schema(type=content.Type.STRING, description="Concise summary of the content."),
            "key_points": content.Schema(type=content.Type.ARRAY, items=content.Schema(type=content.Type.STRING)),
            "sentiment": content.Schema(type=content.Type.STRING, description="Overall emotional tone."),
            "speaker_count": content.Schema(type=content.Type.INTEGER, description="Number of distinct speakers."),
            "speaker_characteristics": content.Schema(
                type=content.Type.OBJECT,
                properties={
                    "speaking_styles": content.Schema(type=content.Type.ARRAY, items=content.Schema(type=content.Type.STRING)),
                    "interaction_patterns": content.Schema(type=content.Type.STRING)
                }
            )
        }
    )
}

ANALYSIS_PROMPTS = {
    AnalysisType.NAME: """
    # Context Setting
    Imagine onboarding as an exploratory field where speech prosody and name 
    pronunciation reveal aspects of personal identity, emotions, and cultural dynamics.
    
    # Analysis Steps
    1. Transcribe the complete name with high attention to nuance
    2. Analyze speech prosody and personality indicators
    3. Evaluate emotional state and comfort level
    4. Assess confidence and authenticity
    5. Perform psychological analysis
    6. Analyze environmental context
    7. Extract voice characteristics for future identification
    
    # Important Notes
    - Focus on accuracy over assumptions
    - Respect cultural and individual nuances
    - Do not hallucinate details
    - Maintain professional analytical tone
    """,
    
    AnalysisType.TRANSCRIPTION: """
    # Context Setting
    You are analyzing a conversation or speech recording for detailed transcription
    and comprehensive understanding of the content and dynamics.
    
    # Analysis Steps
    1. Provide accurate transcription of all speech
    2. Create a concise summary of key content
    3. Extract main discussion points
    4. Analyze overall sentiment and tone
    5. Count and characterize distinct speakers
    6. Note speaking patterns and interaction dynamics
    
    # Important Notes
    - Maintain verbatim accuracy in transcription
    - Capture speaker transitions and overlaps
    - Note significant non-verbal audio cues
    - Preserve speaker-specific language patterns
    """
}

def normalize_mime_type(format_str: str) -> str:
    """Convert format string to proper mime type"""
    mime_map = {
        'wav': 'audio/wav',
        'mp3': 'audio/mp3',
        'aiff': 'audio/aiff',
        'aac': 'audio/aac',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac'
    }
    # Strip 'audio/' prefix if present
    format_str = format_str.lower().replace('audio/', '')
    return mime_map.get(format_str, 'audio/wav')  # Default to wav

# Update endpoint path
@router.post("", response_model=SpeakerProfileResponse)  # Empty string for root path
async def record_name(
    request: SpeakerProfileRequest,  # Changed to handle JSON request
):
    """Record user's name and create speaker profile"""
    logger.debug("Received speaker profile request")
    logger.debug(f"Timestamp: {request.timestamp}")
    logger.debug(f"Metadata: {request.metadata}")
    
    try:
        # Normalize mime type
        mime_type = normalize_mime_type(request.metadata.get("format", "wav"))
        logger.debug(f"Normalized mime type: {mime_type}")

        # Validate base64 data
        try:
            audio_data = base64.b64decode(request.audio_base64)
            logger.debug(f"Decoded audio length: {len(audio_data)}")
        except Exception as e:
            logger.error(f"Base64 decode error: {e}")
            raise HTTPException(status_code=400, detail="Invalid audio data encoding")

        # Process with name analyzer service
        user_id = str(uuid.uuid4())  # Generate ID for new profile
        profile, analysis = await speaker_service.create_from_name_recording(
            user_id=user_id,
            audio_data=request.audio_base64,  # Pass encoded data directly
            mime_type=mime_type,  # Use normalized mime type
            relationship="self"
        )

        response_data = {
            **analysis.dict(),
            "user_id": profile.user_id,
            "profile_created": True
        }
        logger.debug(f"Returning response: {response_data}")
        return response_data

    except Exception as e:
        logger.error(f"Error processing name recording: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Alternative endpoint for JSON/base64 input
@router.post("/record-name/base64", response_model=SpeakerProfileResponse)
async def record_name_base64(
    audio_base64: str,
    user_id: Optional[str] = None,
    relationship: str = "self"
):
    """Record user's name using base64 encoded audio"""
    try:
        profile, analysis = await speaker_service.create_from_name_recording(
            user_id=user_id or str(uuid.uuid4()),
            audio_data=audio_base64,
            mime_type="audio/wav",
            relationship=relationship
        )

        return {
            **analysis.dict(),
            "user_id": profile.user_id,
            "profile_created": True
        }

    except Exception as e:
        logger.error(f"Error processing name recording: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}", response_model=SpeakerProfile)
async def get_speaker_profile(user_id: str):
    """Get a speaker profile by user ID"""
    profile = await speaker_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Speaker profile not found")
    return profile

async def process_audio(file_path: str, analysis_type: AnalysisType) -> dict:
    """Process audio using Gemini with specified analysis type"""
    try:
        with open(file_path, "rb") as f:
            audio_data = f.read()

        return await gemini_service.analyze_audio(
            audio_data,
            ANALYSIS_PROMPTS[analysis_type],
            ANALYSIS_SCHEMAS[analysis_type]
        )

    except Exception as e:
        logger.error(f"Audio analysis error: {e}", exc_info=True)
        raise ValueError(f"Failed to analyze audio: {str(e)}")

# Update existing process_name_recording to use the new unified function
async def process_name_recording(file_path: str) -> dict:
    return await process_audio(file_path, AnalysisType.NAME)

# Add new transcription processing function
async def process_transcription(file_path: str) -> dict:
    return await process_audio(file_path, AnalysisType.TRANSCRIPTION)