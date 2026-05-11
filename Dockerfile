FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONNOUSERSITE=1 \
    PORT=5000 \
    DEBUG=False \
    ARPM_RUNTIME_DIR=/app/runtime/arpm-app \
    ARPM_MODEL_ROOT=/app/assets/models

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
WORKDIR /app/backend
CMD ["python", "app.py"]
