import os
import logging
from typing import Dict, Optional
from pydantic import BaseModel
import mimetypes
from google.ai.generativelanguage_v1beta.types import content
import google.generativeai as genai

logger = logging.getLogger(__name__)

class NameAnalysis(BaseModel):
    name: str
    prosody: str
    feeling: str
    confidence_score: int
    confidence_reasoning: str
    psychoanalysis: str
    location_background: str

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
                ],
                properties={
                    "name": content.Schema(type=content.Type.STRING, description="The user's full name."),
                    "prosody": content.Schema(type=content.Type.STRING, description="Speech analysis."),
                    "feeling": content.Schema(type=content.Type.STRING, description="Emotional tone."),
                    "confidence_score": content.Schema(type=content.Type.INTEGER, description="Confidence score."),
                    "confidence_reasoning": content.Schema(type=content.Type.STRING, description="Reasoning."),
                    "psychoanalysis": content.Schema(type=content.Type.STRING, description="Psychological insights."),
                    "location_background": content.Schema(type=content.Type.STRING, description="Environment details."),
                },
            ),
            "response_mime_type": "application/json",
        }

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

            prompt_text = (
                "# Context Setting\n"
                "Imagine onboarding as an exploratory field where speech prosody and name "
                "pronunciation reveal aspects of personal identity, emotions, and cultural "
                "dynamics. Consider this onboarding as akin to setting up a human playable "
                "character (HPC) in a real-life role-playing game. Just as an HPC has defining "
                "attributes—such as speech, personality, and behavioral cues—capturing a user's "
                "unique pronunciation, tone, and accent patterns reveals underlying aspects of "
                "their personality and comfort level.\n\n"
                
                "# Interaction Format\n"
                "The user was prompted to say '{greeting}, I'm {full_name}', with the user identified always address the user by name.\n\n"
                
                "# Analysis Steps\n\n"
                "1.) Transcribe just the user's complete name. Human names, dialects, accents, etc., "
                "can be very tricky. Ensure the transcription makes sense by contemplating all "
                "available context before finalizing the full name transcription. If the name "
                "sounds fake or like the user is lying, call them out. Focus on capturing every "
                "sound and inflection to reflect the authenticity of their identity. Be mindful "
                "of user dynamics in pronunciation.\n\n"
                
                "2.) Analyze the audio to determine what the user's speech prosody to their name "
                "says about them. Employ extreme inference and capture every detail. Treat prosody "
                "patterns (tone, rhythm, emphasis) like the 'character traits' of the HPC, which "
                "might hint at confidence, pride, or cultural background. Consider how tone and "
                "emphasis reveal depth, much like layers in character development.\n\n"
                
                "3.) Analyze how the user feels about saying their name for this experience. "
                "Observe the 'emotional response' layer of the HPC analogy. Evaluate if their "
                "tone suggests comfort or hesitation. Infer if any detected hesitancy reflects "
                "uncertainty or stems from the novelty of the interaction.\n\n"
                
                "4.) Concisely assign a confidence score and reasoning to either confidence or "
                "lack of confidence on hearing, understanding, and transcription of the speaker. "
                "DO NOT BE OVERALLY OPTIMISTIC ABOUT PREDICTIONS. Return nulls if not enough info "
                "(i.e., speech isn't detected or a name isn't spoken). Do not imagine names or "
                "hallucinate information.\n\n"
                
                "5.) Perform a psychoanalytic assessment: conduct a master psychoanalysis within "
                "the confines and context of this audio, aiming to deeply understand the user.\n\n"
                
                "6.) Determine the user's location and background: analyze ambient sounds and "
                "contextual clues to infer details about the user's current environment or setting. "
                "This includes identifying any background noise that may influence the clarity or "
                "emotional tone of the user's speech.\n\n"
                
                "# Important Notes\n"
                "- Take context from the user's accent to be triple sure of correct transcription\n"
                "- Do not specifically mention 'the audio', 'the audio file' or otherwise\n"
                "- Analyze speech patterns to build a personalized experience\n"
                "- Respect the individuality and nuances within each user's 'character profile'\n"
                "- BE SURE TO NOT LIE OR HALLUCINATE\n"
            )

            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config=self.generation_config
            )

            chat = model.start_chat(history=[{
                "role": "user",
                "parts": [{
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": audio_data
                    }
                }, prompt_text]
            }])

            response = chat.send_message("Process the audio and think deeply")
            
            # Debug log the response
            logger.debug(f"Raw Gemini response: {response}")
            logger.debug(f"Response text: {response.text}")
            logger.debug(f"Response type: {type(response)}")
            
            # Parse the response
            try:
                if hasattr(response, 'candidates') and response.candidates:
                    result = response.candidates[0].content.parts[0].text
                else:
                    result = response.text
                
                logger.debug(f"Parsed result: {result}")
                
                import json
                # Try parsing as JSON
                if isinstance(result, str):
                    result = json.loads(result)
                
                return NameAnalysis(**result)
                
            except Exception as e:
                logger.error(f"Failed to parse response: {str(e)}\nResponse: {response}")
                raise ValueError(f"Failed to parse Gemini response: {str(e)}")

        except Exception as e:
            logger.error(f"Name analysis error: {e}", exc_info=True)
            raise ValueError(f"Failed to analyze name recording: {str(e)}")
