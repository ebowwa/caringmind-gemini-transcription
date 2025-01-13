import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SpeechContext:
    def __init__(self):
        self.contexts: Dict[str, List[dict]] = {}
        
    async def add_segment(self, session_id: str, segment: dict):
        """Add a speech segment to the context"""
        if session_id not in self.contexts:
            self.contexts[session_id] = []
        self.contexts[session_id].append({
            **segment,
            'timestamp': datetime.now()
        })
        
    async def get_context(self, session_id: str, window_seconds: int = 300) -> List[dict]:
        """Get recent context within time window"""
        if session_id not in self.contexts:
            return []
            
        now = datetime.now()
        return [
            segment for segment in self.contexts[session_id]
            if (now - segment['timestamp']).total_seconds() <= window_seconds
        ]
