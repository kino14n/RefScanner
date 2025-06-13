import os
import re
import json
from flask import Flask, render_template, request, jsonify
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
from datetime import datetime

app = Flask(__name__)

# Carpeta donde están los PDFs
PDF_FOLDER = os.path.join(app.static_folder, 'pdfs')
# Archivo para guardar el índice persistente
INDEX_FILE = 'index.json'
# Regex para extraer cualquier texto entre "Ref:" y el primer "/"
CODE_REGEX = re.compile(r'Ref:\s*(.+?)/', re.IGNORECASE)

# Mapeo de meses en español a número
MONTHS = {
    'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
    'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
    'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
}
# Regex para capturar "MES YYYY" en el nombre del PDF
DATE_NAME_RE = re.compile(
    r'\b(' + '|'.join(MONTHS.keys()) + r')\b\W+(\d{4})',
    re.IGNORECASE
)
# Regex para capturar secuencias numéricas MMYYYY (fallback)
DATE_NUM_RE = re.compile(r'\b(0[1-9]|1[0-2])([12]\d{3})\b')


def build_index():
    """
    Recorre todos los PDFs, extrae códigos y construye un índice en memoria.
    Guarda el índice en INDEX_FILE para arranques posteriores.
    """
    idx = {}

    for fname in os.listdir(PDF_FOLDER):
        if not fname.lower().endswith('.pdf'):
            continue

        path = os.path.join(PDF_FOLDER, fname)

        # 1) Intentar extraer fecha del nombre: "MARZO 2025"
        m_name = DATE_NAME_RE.search(fname)
        if m_name:
            mes, año = m_name.group(1).upper(), m_name.group(2)
            sort_date = int(f"{año}{MONTHS[mes]:02d}")
        else:
            # 2) Intentar extraer MMYYYY
            m_num = DATE_NUM_RE.search(fname)
            if m_num:
                sort_date = int(f"{m_num.group(2)}{int(m_num.group(1)):02d}")
            else:
                # 3) Fallback a fecha de modificación del archivo
                ts = os.path.getmtime(path)
                sort_date = int(datetime.fromtimestamp(ts).strftime("%Y%m"))

        # Por archivo, acumulamos totales y páginas
        per_file = {}
        try:
            for page_number, page_layout in enumerate(extract_pages(path), start=1):
                text = ""
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        text += element.get_text()
                for m in CODE_REGEX.finditer(text):
                    raw = m.group(1).strip()
                    # Limpiar puntos, comas, dos puntos o punto y coma al final
                    code = raw.rstrip('.:;,')
                    info = per_file.setdefault(code, {'total': 0, 'pages': {}})
                    info['total'] += 1
                    info['pages'][page_number] = info['pages'].get(page_number, 0) + 1
        except Exception as e:
            app.logger.error(f"⚠️ Error leyendo {fname}: {e}")
            continue

        # Construir entradas finales para este archivo
        for code, info in per_file.items():
            best_page = max(info['pages'].items(), key=lambda x: x[1])[0]
            entry = {
                'manifesto': fname,
                'link': f'/static/pdfs/{fname}',
                'code': code,
                'occurrences': info['total'],
                'page': best_page,
                'sort_date': sort_date
            }
            idx.setdefault(code.lower(), []).append(entry)

    # Guardar índice para arranques futuros
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    app.logger.info(f"✅ Índice construido y guardado con {len(idx)} códigos únicos.")
    return idx


def load_index():
    """
    Carga el índice desde disco si existe, si no, lo construye.
    """
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, encoding='utf-8') as f:
            idx = json.load(f)
        app.logger.info(f"📂 Índice cargado desde {INDEX_FILE} ({len(idx)} códigos).")
        return idx
    return build_index()


# Al iniciar la app, cargamos o construimos el índice
INDEX = load_index()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/codes')
def list_codes():
    """Devuelve un JSON con todos los códigos indexados (llaves)."""
    return jsonify(sorted(INDEX.keys()))


@app.route('/search', methods=['POST'])
def search_codes():
    """
    Recibe {"codes":["A","B",...]} y devuelve coincidencias ordenadas
    por fecha descendente según 'sort_date'.
    """
    data = request.json or {}
    app.logger.info(f"🔎 Recibido /search payload: {data}")

    terms = [c.strip().lower() for c in data.get('codes', []) if c.strip()]
    results = {}

    for term in terms:
        matches = []
        for key, entries in INDEX.items():
            if term in key:
                matches.extend(entries)
        # Ordenar de más reciente a más antiguo
        matches.sort(key=lambda x: x['sort_date'], reverse=True)
        results[term] = matches

    app.logger.info(f"🏷️ Resultados: {results}")
    return jsonify(results)


if __name__ == '__main__':
    # En desarrollo, debug=True habilita autoreload
    app.run(host='0.0.0.0', port=5000, debug=True)
