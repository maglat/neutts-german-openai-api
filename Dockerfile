FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    espeak-ng \
    libespeak1 \
    libsndfile1 \
    ffmpeg \
    curl \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/model_cache
ENV TRANSFORMERS_CACHE=/app/model_cache
ENV TOKENIZERS_PARALLELISM=false

# Create directories
WORKDIR /app
RUN mkdir -p /app/model_cache /app/voices

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .
COPY samples/ ./samples/

# Expose port
EXPOSE 8136

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8136/health || exit 1

# Run the server
CMD ["python", "server.py"]