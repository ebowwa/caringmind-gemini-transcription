import logging
from typing import Dict, List, Optional
from pydantic import BaseModel
from .name_analysis import NameAnalysis, NameAnalysisService

logger = logging.getLogger(__name__)

class SpeakerCharacteristics(BaseModel):
    voice_pattern: str
    common_phrases: List[str]
    speech_style: str
    role: str
    relationship: Optional[str] = "self"  # self, family, friend
    related_to: Optional[str] = None  # user_id of the main user

class SpeakerProfile(BaseModel):
    user_id: str
    name: str
    characteristics: SpeakerCharacteristics
    voice_samples: List[str]  # Base64 encoded audio samples

class SpeakerProfileService:
    def __init__(self):
        self.profiles: Dict[str, SpeakerProfile] = {}
        self.name_analyzer = NameAnalysisService()
        
    async def add_profile(self, profile: SpeakerProfile):
        self.profiles[profile.user_id] = profile
        
    async def get_profile(self, user_id: str) -> Optional[SpeakerProfile]:
        return self.profiles.get(user_id)
        
    async def get_speaker_context(self, user_id: str) -> str:
        """Generate context string for speaker identification"""
        profile = await self.get_profile(user_id)
        if not profile:
            return ""
            
        return f"""
        Speaker context:
        - Name: {profile.name}
        - Voice pattern: {profile.characteristics.voice_pattern}
        - Speech style: {profile.characteristics.speech_style}
        - Role: {profile.characteristics.role}
        - Common phrases: {', '.join(profile.characteristics.common_phrases)}
        """
    
    async def get_related_profiles(self, user_id: str) -> List[SpeakerProfile]:
        """Get all profiles related to a user"""
        return [
            profile for profile in self.profiles.values()
            if profile.characteristics.related_to == user_id
        ]

    async def link_profiles(self, main_user_id: str, related_user_id: str, relationship: str):
        """Link two profiles with a relationship"""
        if related_user_id in self.profiles:
            profile = self.profiles[related_user_id]
            profile.characteristics.relationship = relationship
            profile.characteristics.related_to = main_user_id

    async def create_from_name_recording(
        self,
        user_id: str,
        audio_data: str,
        mime_type: str = "audio/wav",
        relationship: str = "self"
    ) -> tuple[SpeakerProfile, NameAnalysis]:
        """Create a speaker profile from a name recording"""
        try:
            # Add debug logging
            logger.debug(f"Creating profile for user {user_id} with mime type {mime_type}")
            
            # Get name analysis from the audio
            analysis = await self.name_analyzer.analyze_name_recording(
                audio_data=audio_data,
                mime_type=mime_type.lower()  # Normalize mime type
            )
            
            # Create profile from analysis
            profile = SpeakerProfile(
                user_id=user_id,
                name=analysis.name,
                characteristics=SpeakerCharacteristics(
                    voice_pattern=analysis.voice_characteristics.pattern,
                    speech_style=analysis.voice_characteristics.style,
                    common_phrases=analysis.voice_characteristics.common_phrases,
                    role=relationship
                ),
                voice_samples=[audio_data]  # Store the base64 audio
            )
            
            # Store the profile
            await self.add_profile(profile)
            
            return profile, analysis
            
        except Exception as e:
            logger.error(f"Failed to create profile from name recording: {e}")
            raise ValueError(f"Profile creation failed: {str(e)}")
