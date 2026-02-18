from pydantic import BaseModel
from typing import Optional, List


class TextRequest(BaseModel):
    """Basic TTS request model"""
    text: str
    ref_audio: Optional[str] = None  # Path to reference audio file
    ref_text: Optional[str] = None  # Reference text or path to .txt file


class VoiceListItem(BaseModel):
    """Voice item for listing"""
    voice_id: str
    name: str
    language: str = "de"
    has_reference: bool = False


class VoicesResponse(BaseModel):
    """Response for voices listing"""
    voices: List[VoiceListItem]


class OpenAISpeechRequest(BaseModel):
    """OpenAI-compatible TTS request"""
    model: str = "gpt-4o-mini-tts"
    input: str
    voice: str = "greta"
    instructions: Optional[str] = None
    response_format: Optional[str] = "mp3"
    speed: Optional[float] = 1.0


class SpeechResponse(BaseModel):
    """Response from synthesize endpoint"""
    audio_base64: Optional[str] = None
    timing: Optional[dict] = None
    format: str = "wav"