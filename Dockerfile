# Dockerfile
ARG CACHEBUST=1
FROM python:3.11-slim

# Instala Poppler y Tesseract (OCR en español)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      poppler-utils \
      tesseract-ocr \
      tesseract-ocr-spa \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia todo tu código y plantillas
COPY . .

# Instala dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Variables de entorno
ENV PYTHONUNBUFFERED=1

# Expone el puerto que usa Gunicorn
EXPOSE 5000

# Arranca Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "1"]
