FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    DEBUG=false \
    ARPM_RUNTIME_DIR=/app/runtime/arpm-app \
    ARPM_MODEL_ROOT=/app/assets/models

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt ./requirements-docker.txt
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY . .

EXPOSE 5000

CMD ["python", "backend/app.py"]
