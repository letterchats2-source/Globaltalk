FROM python:3.9-slim

# Sistem kütüphanelerini yükle (Ses isleme için gerekli)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Render'in portunu kullan
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]