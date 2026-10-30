# Voice Studio. Builds for linux/amd64 and linux/arm64 (Apple Silicon, Raspberry Pi 5, ARM servers).
FROM python:3.11-slim

# CPU-only PyTorch by default (small image, runs everywhere).
# For NVIDIA GPUs: docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
# Set to 1 to bake the voice models into the image so it works offline from the first launch.
ARG PREFETCH=0

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VOICESTUDIO_HOST=0.0.0.0 \
    VOICESTUDIO_OPEN_BROWSER=0 \
    VOICESTUDIO_DATA=/app/data \
    HF_HOME=/app/models

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libsndfile1 ffmpeg espeak-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-engines.txt ./

RUN pip install --upgrade pip \
 && (pip install torch==2.6.0 torchaudio==2.6.0 --index-url ${TORCH_INDEX} \
     || pip install torch==2.6.0 torchaudio==2.6.0) \
 && pip install -r requirements.txt \
 && (pip install chatterbox-tts || echo "WARNING: Clone mode (chatterbox-tts) could not be installed") \
 && (pip install "kokoro>=0.9.4" || echo "WARNING: Fast mode (kokoro) could not be installed") \
 && (pip install faster-whisper || echo "WARNING: Captions (faster-whisper) could not be installed")

COPY app ./app
COPY assets ./assets
COPY run_server.py VERSION branding.json ./

RUN if [ "$PREFETCH" = "1" ]; then python -m app.prefetch --all; fi

VOLUME ["/app/data", "/app/models"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/system')"
CMD ["python", "run_server.py"]
