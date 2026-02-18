import os
import io
import time
import struct
import glob
from typing import Optional, Dict, Any, Tuple, List
import numpy as np
import torch

from config import (
    MODEL_REPO,
    CODEC_REPO,
    BACKBONE_DEVICE,
    CODEC_DEVICE,
    VOICES_DIR,
    SAMPLES_DIR
)


class TTSService:
    def __init__(self):
        self.tts = None
        self.voice_cache: Dict[str, Dict[str, Any]] = {}

    def initialize_tts(self) -> None:
        """Initialize the NeuTTS model"""
        if self.tts is None:
            print(f"Initializing NeuTTS with model: {MODEL_REPO}")

            from neutts import NeuTTS

            self.tts = NeuTTS(
                backbone_repo=MODEL_REPO,
                backbone_device=BACKBONE_DEVICE,
                codec_repo=CODEC_REPO,
                codec_device=CODEC_DEVICE
            )

            print("NeuTTS initialized successfully!")

            # Load built-in samples
            self._load_builtin_samples()

            # Scan custom voices directory
            self._scan_custom_voices()

            print(f"Cached voices: {list(self.voice_cache.keys())}")

    def _load_builtin_samples(self) -> None:
        """Load built-in German voice samples"""
        builtin_voices = {
            "greta": "greta",
            "mateo": "mateo",
            "juliette": "juliette"
        }

        for voice_id, filename in builtin_voices.items():
            wav_path = os.path.join(SAMPLES_DIR, f"{filename}.wav")
            txt_path = os.path.join(SAMPLES_DIR, f"{filename}.txt")
            pt_path = os.path.join(SAMPLES_DIR, f"{filename}.pt")

            if os.path.exists(wav_path):
                # Encode reference on startup for faster inference
                try:
                    ref_codes = self.tts.encode_reference(wav_path)
                    ref_text = ""

                    if os.path.exists(txt_path):
                        with open(txt_path, "r", encoding="utf-8") as f:
                            ref_text = f.read().strip()
                    elif os.path.exists(pt_path):
                        # Fallback to .pt file
                        ref_codes = torch.load(pt_path)

                    self.voice_cache[voice_id] = {
                        "ref_codes": ref_codes,
                        "ref_text": ref_text,
                        "wav_path": wav_path,
                        "is_builtin": True,
                        "name": f"German {voice_id.title()} (built-in)"
                    }
                    print(f"Loaded built-in voice: {voice_id}")
                except Exception as e:
                    print(f"Failed to load voice {voice_id}: {e}")

    def _scan_custom_voices(self) -> None:
        """Scan custom voices directory for additional voice samples"""
        if not os.path.exists(VOICES_DIR):
            print(f"Custom voices directory does not exist: {VOICES_DIR}")
            return

        # Look for .wav files
        wav_files = glob.glob(os.path.join(VOICES_DIR, "*.wav"))

        for wav_path in wav_files:
            voice_id = os.path.splitext(os.path.basename(wav_path))[0]
            txt_path = os.path.splitext(wav_path)[0] + ".txt"

            if voice_id in self.voice_cache:
                continue  # Skip if already loaded as builtin

            try:
                ref_codes = self.tts.encode_reference(wav_path)
                ref_text = ""

                if os.path.exists(txt_path):
                    with open(txt_path, "r", encoding="utf-8") as f:
                        ref_text = f.read().strip()

                self.voice_cache[voice_id] = {
                    "ref_codes": ref_codes,
                    "ref_text": ref_text,
                    "wav_path": wav_path,
                    "is_builtin": False,
                    "name": f"Custom voice: {voice_id}"
                }
                print(f"Loaded custom voice: {voice_id}")
            except Exception as e:
                print(f"Failed to load custom voice {voice_id}: {e}")

    def reload_custom_voices(self) -> List[str]:
        """Reload custom voices - can be called dynamically"""
        self._scan_custom_voices()
        return list(self.voice_cache.keys())

    def get_available_voices(self) -> Dict[str, Any]:
        """Get all available voices"""
        result = {}
        for voice_id, data in self.voice_cache.items():
            result[voice_id] = {
                "name": data["name"],
                "is_builtin": data["is_builtin"],
                "has_ref_text": bool(data["ref_text"])
            }
        return result

    def get_voice_data(self, voice_id: str) -> Tuple[Optional[torch.Tensor], Optional[str]]:
        """Get reference codes and text for a voice"""
        if voice_id not in self.voice_cache:
            # Try to find it in custom voices
            self.reload_custom_voices()

        if voice_id not in self.voice_cache:
            return None, None

        voice_data = self.voice_cache[voice_id]
        return voice_data["ref_codes"], voice_data["ref_text"]

    def synthesize(self, text: str, voice_id: str) -> bytes:
        """
        Synthesize speech with timing info
        Returns: (wav_data, timing_dict)
        """
        start_time = time.time()

        ref_codes, ref_text = self.get_voice_data(voice_id)

        if ref_codes is None:
            raise ValueError(f"Voice '{voice_id}' not found")

        # Generate audio
        wav = self.tts.infer(text, ref_codes, ref_text)

        latency_ms = (time.time() - start_time) * 1000

        # Convert to WAV
        wav_data = self._numpy_to_wav(wav)

        timing = {
            "latency_ms": latency_ms,
            "sample_rate": 24000,
            "duration_seconds": len(wav) / 24000
        }

        return wav_data, timing

    def synthesize_streaming(self, text: str, voice_id: str):
        """
        Stream audio chunks as they are generated
        Yields: audio chunks
        """
        ref_codes, ref_text = self.get_voice_data(voice_id)

        if ref_codes is None:
            raise ValueError(f"Voice '{voice_id}' not found")

        # Use streaming inference if available
        try:
            for chunk in self.tts.infer_stream(text, ref_codes, ref_text):
                audio = (chunk * 32767).astype(np.int16)
                yield audio.tobytes()
        except AttributeError:
            # Fallback to non-streaming if infer_stream not available
            wav, timing = self.synthesize(text, voice_id)
            yield wav

    def _numpy_to_wav(self, audio: np.ndarray, sample_rate: int = 24000) -> bytes:
        """Convert numpy audio array to WAV bytes"""
        if audio.ndim > 1:
            audio = audio.flatten()

        audio_int16 = (audio * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()

        data_size = len(audio_bytes)
        wav_header = self._create_wav_header(sample_rate, 1, 16, data_size)

        return wav_header + audio_bytes

    def _create_wav_header(self, sample_rate: int, num_channels: int, bits_per_sample: int, data_size: int) -> bytes:
        """Create WAV file header"""
        header = b'RIFF'
        header += struct.pack('<I', 36 + data_size)
        header += b'WAVE'
        header += b'fmt '
        header += struct.pack('<I', 16)  # Subchunk1Size
        header += struct.pack('<H', 1)    # AudioFormat (PCM)
        header += struct.pack('<H', num_channels)
        header += struct.pack('<I', sample_rate)
        header += struct.pack('<I', sample_rate * num_channels * bits_per_sample // 8)  # ByteRate
        header += struct.pack('<H', num_channels * bits_per_sample // 8)  # BlockAlign
        header += struct.pack('<H', bits_per_sample)
        header += b'data'
        header += struct.pack('<I', data_size)
        return header

    def is_initialized(self) -> bool:
        return self.tts is not None


# Global service instance
tts_service = TTSService()