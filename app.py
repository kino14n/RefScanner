import os, re, json
from flask import Flask, render_template, request, jsonify
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer
from datetime import datetime
from pdf2image import convert_from_path
import pytesseract

app = Flask(__name__)

# Carpeta donde están los PDFs
PDF_FOLDER = os.path.join(app.static_folder, 'pdfs')

# Regex para capturar el código tras "Ref:"
CODE_REGEX = re.compile(r'Ref:\s*([A-Za-z0-9\-\._]+)', re.IGNORECASE)

# Map de meses para parsear fechas del nombre de manifiesto
MONTHS = {
  'ENERO':1,'FEBRERO':2,'MARZO':3,'ABRIL':4,'MAYO':5,'JUNIO':6,
  'JULIO':7,'AGOSTO':8,'SEPTIEMBRE':9,'OCTUBRE':10,'NOVIEMBRE':11,'DICIEMBRE':12
}

def parse_date_from_name(name):
    # Asume formato "..._MMM-YYYY ..." en el nombre
    m = re.search(r'(\w+)[\s\-_]+(\d{4})', name.upper())
    if not m: return datetime.min
    mes, anho = m.group(1), int(m.group(2))
    return datetime(year=anho, month=MONTHS.get(mes,1), day=1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    codes = [c.strip().upper() for c in re.split(r'[,\n]', data.get('codes','')) if c.strip()]
    results = {c: [] for c in codes}

    for pdf in os.listdir(PDF_FOLDER):
        path = os.path.join(PDF_FOLDER, pdf)
        # extrae todo el texto de cada página
        text = extract_text(path)
        for code in codes:
            if code in text:
                # averigua en qué páginas
                pages = []
                for i, page in enumerate(extract_pages(path), start=1):
                    page_text = "".join([el.get_text() for el in page if isinstance(el, LTTextContainer)])
                    if code in page_text:
                        pages.append(str(i))
                results[code].append({
                    'manifiesto': pdf,
                    'link': f'/static/pdfs/{pdf}',
                    'paginas': ",".join(pages),
                    'fecha': parse_date_from_name(pdf)
                })

    # aplanar y ordenar por fecha descendente
    flat = []
    for code, items in results.items():
        if not items:
            flat.append({'codigo': code, 'mensaje': f'No se encontró “{code}”.'})
        else:
            for it in sorted(items, key=lambda x: x['fecha'], reverse=True):
                flat.append({
                    'codigo': code,
                    'manifiesto': it['manifiesto'],
                    'link': it['link'],
                    'paginas': it['paginas']
                })
    return jsonify(flat)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=True)
