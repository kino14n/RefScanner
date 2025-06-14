# Usa la imagen oficial ligera de Python
FROM python:3.11-slim

# 1) Instala librerías del sistema para PDF→imagen y OCR
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
       poppler-utils \
       tesseract-ocr \
       tesseract-ocr-spa && \
    rm -rf /var/lib/apt/lists/*

# 2) Crea el directorio de trabajo
WORKDIR /app

# 3) Copia y instala requisitos Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copia el resto del código
COPY . .

# 5) Expone el puerto (Railway proveerá $PORT)
ENV PORT 5000

# 6) Arranca con gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
