import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from pydantic import BaseModel
import base64
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.post("/upload", response_model=TranscriptionResponse)
async def upload_audio(request: AudioRequest):
    try:
        logger.info("Received audio data request")
        
        # Validate and decode base64
        try:
            audio_data = base64.b64decode(request.audio_base64)
            logger.info(f"Successfully decoded base64 data, size: {len(audio_data)} bytes")
        except Exception as e:
            logger.error(f"Base64 decoding error: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid base64 audio data")

        # Create model
        logger.info("Creating Gemini model...")
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",  # Using flash model as in example
            generation_config=generation_config
        ) # gemini-2.0-flash-exp, gemini-1.5-flash

        # Start chat session with inline audio data
        logger.info("Starting chat session...")
        try:
            chat = model.start_chat(history=[
                {
                    "role": "user",
                    "parts": [{
                        "inline_data": {
                            "mime_type": "audio/ogg",
                            "data": request.audio_base64
                        }
                    },
                    """Analyze the provided audio conversation between multiple participants. For each speaker, extract and render in HTML:
                    - Diarization: Speaker labels in <h1> tags
                    - Transcription: Verbatim text in <p> tags
                    - Timestamps: Time ranges in <h2> tags
                    - Tone Analysis: Include dominant tone and supporting indicators
                    - Confidence: 0-100% rating for tone detection
                    - Summary: Concise summary of speaker's contribution
                    
                    Return a JSON object with full_audio_transcribed boolean and conversation_analysis array."""
                    ]
                }
            ])
            logger.info("Chat session started successfully")
        except Exception as e:
            logger.error(f"Chat session error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Chat session failed: {str(e)}")

        # Get response
        logger.info("Sending message to get analysis...")
        try:
            response = chat.send_message("Please analyze the audio file")
            logger.info("Received response from Gemini")
            logger.debug(f"Raw response: {response.text}")
            
            # Parse JSON response
            response_text = response.text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Message sending error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
