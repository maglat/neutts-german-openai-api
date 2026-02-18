# NeuTTS German OpenAI API

OpenAI-kompatible TTS-API mit dem **NeuTTS Nano German** Modell (Q4 GGUF).

## Features

- Vollständige OpenAI TTS API-Kompatibilität (`/v1/audio/speech`)
-Deutsches Sprachmodell: `neuphonic/neutts-nano-german-q4-gguf`
- Eingebaute deutsche Stimmen: greta, mateo, juliette
- Unterstützung für eigene Stimmen via Volume Mount
- CPU-optimiert (GPU optional)
- Streaming-Unterstützung für Echtzeit-Audio

## Schnellstart

### Mit Docker Compose

```bash
# Klonen oder dieses Verzeichnis verwenden
cd neutts-german-openai-api

# Starten
docker-compose up --build
```

Der Service läuft dann auf Port **8136**.

### Eigene Stimmen hinzufügen

1. Lege `.wav`-Dateien im `voices/` Ordner ab
2. Optional:对应的 `.txt` Datei mit Referenz-Text
3. Rufe `POST /v1/voices/reload` auf oder starte den Container neu

Beispiel:
```
voices/
├── meine_stimme.wav
└── meine_stimme.txt
```

## API-Endpunkte

### OpenAI-kompatibel

```bash
POST /v1/audio/speech
```

**Beispiel-Request:**
```bash
curl -X POST http://localhost:8136/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Hallo, das ist ein Test der deutschen Sprachsynthese.",
    "voice": "greta",
    "response_format": "mp3"
  }' --output speech.mp3
```

### Verfügbare Stimmen auflisten

```bash
GET /v1/voices
```

### Health Check

```bash
GET /health
```

## Verfügbare Stimmen

| Voice ID | Name | Typ |
|----------|------|-----|
| greta | Greta (deutsche Frau) | builtin |
| mateo | Mateo (deutscher Mann) | builtin |
| juliette | Juliette (deutsche Frau) | builtin |

Eigene Stimmen werden unter ihrer Dateiname ohne Extension gelistet.

## Umgebungsvariablen

| Variable | Standardwert | Beschreibung |
|----------|--------------|---------------|
| PORT | 8136 | Server-Port |
| MODEL_REPO | neuphonic/neutts-nano-german-q4-gguf | HuggingFace Model |
| CODEC_REPO | neuphonic/neucodec | Codec Repository |
| BACKBONE_DEVICE | cpu | Gerät für Backbone (cpu/gpu) |
| CODEC_DEVICE | cpu | Gerät für Codec (cpu/gpu) |
| VOICES_DIR | /app/voices | Verzeichnis für eigene Stimmen |

## GPU-Unterstützung (optional)

Für GPU-Beschleunigung:

```yaml
# docker-compose.yml anpassen
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

Und Umgebungsvariable setzen:
```
BACKBONE_DEVICE=gpu
```

## Integration

### OpenWebUI

```yaml
# In OpenWebUI Konfiguration
openai:
  base_url: "http://localhost:8136/v1/"
  api_key: "dummy"
```

### LiveKit

```python
import openai
openai.api_base = "http://localhost:8136/v1/"
```

### Pipecat

```python
ElevenLabsTTSService(
    api_key="dummy",
    voice_id="greta",
    base_url="http://localhost:8136/v1/"
)
```

## Lizenz

Siehe [NeuTTS Lizenz](https://github.com/neuphonic/neutts) für das Basismodell.

Dieses Projekt ist eine Anpassung basierend auf [neutts-openai-api](https://github.com/Edward-Zion-Saji/neutts-openai-api).