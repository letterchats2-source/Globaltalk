FROM python:3.9-slim

# Sistem kütüphanelerini yükle
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Portu doğrudan 8000 olarak sabitledik
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
