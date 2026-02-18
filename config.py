import os
from pathlib import Path

# Configuration - these can be overridden via environment variables
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8136"))

# Model configuration
MODEL_REPO = os.getenv("MODEL_REPO", "neuphonic/neutts-nano-german-q4-gguf")
CODEC_REPO = os.getenv("CODEC_REPO", "neuphonic/neucodec")
BACKBONE_DEVICE = os.getenv("BACKBONE_DEVICE", "cpu")
CODEC_DEVICE = os.getenv("CODEC_DEVICE", "cpu")

# Voice/sample directories
# Custom voices mounted from host
VOICES_DIR = os.getenv("VOICES_DIR", "/app/voices")
# Built-in samples
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")

# Cache directory for HuggingFace models
HF_HOME = os.getenv("HF_HOME", "/app/model_cache")