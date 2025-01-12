import os
import logging
import json
import base64
from typing import Optional
from fastapi import APIRouter, HTTPException
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from pydantic import BaseModel
from services.audio_upload import AudioUploadService
from services.audio_validation import AudioValidator  # Add this import

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["audio-processing"],
    responses={404: {"description": "Not found"}},
)

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set")
genai.configure(api_key=api_key)

# Schema definitions
class ToneAnalysis(BaseModel):
    tone: str
    indicators: list[str]

class ConversationTurn(BaseModel):
    diarization_html: str
    transcription_html: str
    timestamps_html: str
    tone_analysis: ToneAnalysis
    confidence: float
    summary: str

class TranscriptionResponse(BaseModel):
    full_audio_transcribed: bool
    conversation_analysis: list[ConversationTurn]

class AudioRequest(BaseModel):
    audio_base64: str

class UploadResponse(BaseModel):
    file_id: Optional[str] = None
    size: int
    is_valid: bool
    analysis: Optional[TranscriptionResponse] = None

class AnalysisRequest(BaseModel):
    file_id: str

# Create the model configuration
generation_config = {
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

@router.post("/upload", response_model=UploadResponse)
async def upload_audio(request: AudioRequest):
    """Handle file upload and optional analysis"""
    try:
        # Single validation during upload
        file_id, size, is_valid, speech_ratio = await AudioUploadService.process_upload(request.audio_base64)
        logger.info(f"Upload processed - valid: {is_valid}, speech: {speech_ratio:.2f}")

        # Return early if audio is invalid
        if not is_valid:
            return UploadResponse(file_id=None, size=size, is_valid=False)

        # Only analyze valid audio
        file_path = AudioUploadService.get_audio_path(file_id)
        with open(file_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode()

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config
        )

        logger.info("Starting chat session...")
        try:
            chat = model.start_chat(history=[
                {
                    "role": "user",
                    "parts": [{
                        "inline_data": {
                            "mime_type": "audio/wav",  # Changed from ogg to wav
                            "data": audio_base64
                        }
                    },
                    """Please transcribe only what is actually spoken in this audio clip. 
                    Do not invent or assume additional dialogue.
                    If you hear a single speaker, return just one analysis.
                    Format the output as follows:
                    - Diarization: Use <h1> for actual speaker detection
                    - Transcription: Use <p> for exact words spoken
                    - Timestamps: Use <h2> for time ranges detected
                    - Tone: Only analyze the actual tone present
                    
                    Return a JSON object with full_audio_transcribed boolean and conversation_analysis array.
                    If unsure about any part, indicate lower confidence scores."""
                    ]
                }
            ])
            logger.info("Chat session started successfully")
        except Exception as e:
            logger.error(f"Chat session error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Chat session failed: {str(e)}")

        logger.info("Sending message to get analysis...")
        try:
            response = chat.send_message("Please analyze the audio file")
            logger.info("Received response from Gemini")
            logger.debug(f"Raw response: {response.text}")
            
            response_text = response.text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            
            # Parse and validate response
            response_data = json.loads(response_text)
            analysis = TranscriptionResponse(**response_data)  # Validate against our model
            
            # Return complete response
            result = UploadResponse(
                file_id=file_id,
                size=size,
                is_valid=True,
                analysis=analysis
            )
            logger.info(f"Returning analysis with {len(analysis.conversation_analysis)} turns")
            return result

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}", exc_info=True)
            # Return upload success but no analysis
            return UploadResponse(
                file_id=file_id,
                size=size,
                is_valid=True,
                analysis=None
            )

    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

# Remove separate analyze endpoint since we do it inline
