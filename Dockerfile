# Usa una imagen base oficial de Python
FROM python:3.11-slim

# Instala Poppler y Tesseract
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      poppler-utils \
      tesseract-ocr \
      tesseract-ocr-spa && \
    rm -rf /var/lib/apt/lists/*

# Crea directorio de trabajo
WORKDIR /app

# Copia archivos de tu proyecto
COPY . .

# Instala tus dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto que usa Flask
EXPOSE 5000

# Comando por defecto para arrancar tu app con Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
