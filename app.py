import os, re
from flask import Flask, render_template, request, jsonify, url_for
from pdfminer.high_level import extract_text

app = Flask(__name__)
PDF_FOLDER = os.path.join(app.static_folder, 'pdfs')

CODE_REGEX = re.compile(r'Ref:\s*([^/]+)\/', re.IGNORECASE)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_codes():
    data = request.json or {}
    codes = [c.strip() for c in data.get('codes', []) if c.strip()]
    results = {}

    for fname in os.listdir(PDF_FOLDER):
        if not fname.lower().endswith('.pdf'):
            continue
        path = os.path.join(PDF_FOLDER, fname)
        text = extract_text(path)
        for code in codes:
            matches = [m for m in CODE_REGEX.finditer(text) if m.group(1).strip().lower() == code.lower()]
            if matches:
                count = len(matches)
                results.setdefault(code, []).append({
                    'manifesto': fname,
                    'link': url_for('static', filename=f'pdfs/{fname}', _external=True),
                    'code': code,
                    'occurrences': count
                })
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
