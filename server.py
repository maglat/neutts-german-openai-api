import io
import base64
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydub import AudioSegment

from config import HOST, PORT
from models import (
    TextRequest,
    OpenAISpeechRequest,
    VoiceListItem,
    VoicesResponse
)
from tts_service import tts_service


app = FastAPI(
    title="NeuTTS German OpenAI API",
    description="OpenAI-compatible TTS API with NeuTTS German model",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize TTS service on startup"""
    tts_service.initialize_tts()


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "service": "NeuTTS German OpenAI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "voices": "/v1/voices"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "tts_initialized": tts_service.is_initialized(),
        "available_voices": list(tts_service.get_available_voices().keys())
    }


@app.get("/v1/voices", response_model=VoicesResponse)
async def list_voices():
    """List all available voices"""
    voices_list = []

    available = tts_service.get_available_voices()
    for voice_id, data in available.items():
        voices_list.append(VoiceListItem(
            voice_id=voice_id,
            name=data["name"],
            language="de",
            has_reference=data["has_ref_text"]
        ))

    return VoicesResponse(voices=voices_list)


@app.post("/v1/audio/speech")
async def openai_speech(request: OpenAISpeechRequest):
    """
    OpenAI-compatible TTS endpoint
    POST /v1/audio/speech
    """
    if not tts_service.is_initialized():
        tts_service.initialize_tts()

    # Map voice names (support aliases)
    voice_mapping = {
        "greta": "greta",
        "mateo": "mateo",
        "juliette": "juliette",
        "coral": "greta",  # Alias for compatibility
        "dave": "greta",   # Alias for compatibility
    }

    voice_id = voice_mapping.get(request.voice, request.voice)

    # Validate voice exists
    if voice_id not in tts_service.voice_cache:
        available = ", ".join(tts_service.voice_cache.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Voice '{request.voice}' not found. Available voices: {available}"
        )

    try:
        wav_data, timing = tts_service.synthesize(request.input, voice_id)

        # Convert to requested format
        if request.response_format == "pcm":
            # Return raw PCM data
            audio = AudioSegment.from_wav(io.BytesIO(wav_data))
            pcm_data = audio.set_frame_rate(24000).set_channels(1).set_sample_width(2).raw_data
            return StreamingResponse(
                iter([pcm_data]),
                media_type="audio/pcm",
                headers={"Content-Disposition": "attachment; filename=speech.pcm"}
            )
        else:
            # Convert to other formats (mp3, opus, flac, aac, wav)
            audio = AudioSegment.from_wav(io.BytesIO(wav_data))

            format_map = {
                "mp3": "mp3",
                "opus": "opus",
                "aac": "aac",
                "flac": "flac",
                "wav": "wav"
            }
            export_format = format_map.get(request.response_format, "mp3")

            output = io.BytesIO()
            bitrate = "128k" if export_format != "wav" else None
            audio.export(output, format=export_format, bitrate=bitrate)
            final_audio = output.getvalue()

            media_types = {
                "mp3": "audio/mpeg",
                "opus": "audio/opus",
                "aac": "audio/aac",
                "flac": "audio/flac",
                "wav": "audio/wav"
            }
            media_type = media_types.get(export_format, "audio/mpeg")

            return StreamingResponse(
                iter([final_audio]),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename=speech.{export_format}",
                    "X-Audio-Latency": f"{timing['latency_ms']:.2f}ms"
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")


@app.post("/synthesize")
async def synthesize_speech(request: TextRequest):
    """
    Extended TTS endpoint with more control
    POST /synthesize
    """
    if not tts_service.is_initialized():
        tts_service.initialize_tts()

    try:
        # Determine which voice to use
        if request.ref_audio:
            # Custom reference - load it
            voice_id = "custom"
            # Load custom reference
            # This would require additional handling for dynamic loading
            # For now, return error if not in cache
            raise HTTPException(
                status_code=400,
                detail="Custom reference audio not yet supported via this endpoint. Use /v1/audio/speech with a registered voice."
            )
        else:
            # Use default greta voice
            voice_id = "greta"

        wav_data, timing = tts_service.synthesize(request.text, voice_id)

        return {
            "audio": base64.b64encode(wav_data).decode("utf-8"),
            "format": "wav",
            "sample_rate": 24000,
            "timing": timing
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/voices/reload")
async def reload_voices():
    """Reload custom voices from the voices directory"""
    voices = tts_service.reload_custom_voices()
    return {"success": True, "available_voices": voices}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)