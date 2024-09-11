from flask import Flask, jsonify, request
import random
import re
import sqlite3
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# Conectando ao banco de dados SQLite
def get_db_connection():
    conn = sqlite3.connect('rastreamento.db')
    conn.row_factory = sqlite3.Row
    return conn


# Criar a tabela no banco de dados (caso não exista)
def create_table():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS tracking_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code TEXT NOT NULL,
                        status TEXT NOT NULL,
                        location TEXT NOT NULL,
                        delivery_date TEXT NOT NULL
                    )''')
    conn.commit()
    conn.close()


# Função para gerar código
def generate_code():
    prefix = "BR"
    number = ''.join([str(random.randint(0, 9)) for _ in range(11)])
    return prefix + number


# Função para validar o formato do código
def is_valid_code(code):
    pattern = r"^BR\d{11}$"
    return re.match(pattern, code) is not None


# Rota para gerar código e salvar no banco de dados
@app.route('/generate-code', methods=['GET'])
def generate_code_route():
    code = generate_code()

    # Informações fictícias associadas ao código
    status = "em transito"
    location = "Manaus, TESTE"
    delivery_date = "2024-10-01"

    # Inserir no banco de dados
    conn = get_db_connection()
    conn.execute('INSERT INTO tracking_codes (code, status, location, delivery_date) VALUES (?, ?, ?, ?)',
                 (code, status, location, delivery_date))
    conn.commit()
    conn.close()

    return jsonify({"code": code})


# Rota para consultar o código
@app.route('/consult-code', methods=['POST'])
def consult_code_route():
    data = request.get_json()
    code = data.get("code", "")

    if not is_valid_code(code):
        return jsonify({"error": "Invalid code format"}), 400

    # Buscar as informações no banco de dados
    conn = get_db_connection()
    result = conn.execute('SELECT * FROM tracking_codes WHERE code = ?', (code,)).fetchone()
    conn.close()

    if result is None:
        return jsonify({"error": "Code not found"}), 404

    # Retornar as informações do código
    info = {
        "code": result["code"],
        "status": result["status"],
        "location": result["location"],
        "delivery_date": result["delivery_date"]
    }

    return jsonify(info)


if __name__ == '__main__':
    # Criar a tabela de rastreamento ao iniciar o aplicativo
    create_table()
    app.run(debug=True)
