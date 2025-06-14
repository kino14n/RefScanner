import os
import re
import json
from flask import Flask, render_template, request, jsonify
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer
from datetime import datetime
from pdf2image import convert_from_path
import pytesseract

app = Flask(__name__)

PDF_FOLDER = os.path.join(app.static_folder, 'pdfs')
INDEX_FILE = 'index.json'

CODE_REGEX = re.compile(r'Ref:\s*([A-Za-z0-9-]+)', re.IGNORECASE)

MONTHS = {
    'ENERO':1,'FEBRERO':2,'MARZO':3,'ABRIL':4,'MAYO':5,'JUNIO':6,
    'JULIO':7,'AGOSTO':8,'SEPTIEMBRE':9,'OCTUBRE':10,'NOVIEMBRE':11,'DICIEMBRE':12
}
DATE_NAME_RE = re.compile(r'\b(' + '|'.join(MONTHS.keys()) + r')\b\W+(\d{4})', re.IGNORECASE)
DATE_NUM_RE  = re.compile(r'\b(0[1-9]|1[0-2])([12]\d{3})\b')

def ocr_text(path):
    text = ""
    try:
        pages = convert_from_path(path, dpi=200)
        for img in pages:
            text += pytesseract.image_to_string(img, lang='spa') + "\n"
    except Exception as e:
        app.logger.error(f"OCR falló en {path}: {e}")
    return text.lower()

def build_index():
    idx = {}
    for fname in os.listdir(PDF_FOLDER):
        if not fname.lower().endswith('.pdf'):
            continue
        path = os.path.join(PDF_FOLDER, fname)

        m_name = DATE_NAME_RE.search(fname)
        if m_name:
            mes, año = m_name.group(1).upper(), m_name.group(2)
            sort_date = int(f"{año}{MONTHS[mes]:02d}")
        else:
            m_num = DATE_NUM_RE.search(fname)
            if m_num:
                sort_date = int(f"{m_num.group(2)}{int(m_num.group(1)):02d}")
            else:
                ts = os.path.getmtime(path)
                sort_date = int(datetime.fromtimestamp(ts).strftime("%Y%m"))

        try:
            raw_text = extract_text(path).lower()
        except Exception:
            raw_text = ""

        if 'ref:' not in raw_text:
            raw_text = ocr_text(path)

        per_file = {}
        for pnum, layout in enumerate(extract_pages(path), start=1):
            page_text = ""
            for el in layout:
                if isinstance(el, LTTextContainer):
                    page_text += el.get_text()
            page_text = page_text.lower()
            source = page_text if 'ref:' in page_text else raw_text
            for m in CODE_REGEX.finditer(source):
                code = m.group(1).strip().rstrip('.:;,')
                info = per_file.setdefault(code, {'pages': {}})
                info['pages'][pnum] = info['pages'].get(pnum, 0) + 1

        for code, info in per_file.items():
            pages_list = sorted(info['pages'].keys())
            entry = {
                'manifesto': fname,
                'link': f'/static/pdfs/{fname}',
                'code': code,
                'pages': ','.join(str(p) for p in pages_list),
                'sort_date': sort_date
            }
            idx.setdefault(code.lower(), []).append(entry)

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    app.logger.info(f"Índice reconstruido: {len(idx)} códigos.")
    return idx

def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, encoding='utf-8') as f:
            return json.load(f)
    return build_index()

INDEX = load_index()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/codes')
def list_codes():
    return jsonify(sorted(INDEX.keys()))

@app.route('/search', methods=['POST'])
def search_codes():
    data = request.json or {}
    terms = [c.strip().lower() for c in data.get('codes', []) if c.strip()]
    results = {}
    for term in terms:
        matches = []
        for key, entries in INDEX.items():
            if term in key:
                matches.extend(entries)
        matches.sort(key=lambda x: x['sort_date'], reverse=True)
        results[term] = matches
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
