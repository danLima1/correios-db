from flask import Flask, jsonify, request
import random
import re
import sqlite3
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

def get_db_connection():
    conn = sqlite3.connect('rastreamento.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS tracking_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code TEXT NOT NULL,
                        status1 TEXT NOT NULL,
                        location1 TEXT NOT NULL,
                        delivery_date1 TEXT NOT NULL,
                        status2 TEXT,
                        location2 TEXT,
                        delivery_date2 TEXT,
                        status3 TEXT,
                        location3 TEXT,
                        delivery_date3 TEXT,
                        creation_date TEXT NOT NULL
                    )''')
    conn.commit()
    conn.close()

def generate_code():
    prefix = "BR"
    number = ''.join([str(random.randint(0, 9)) for _ in range(11)])
    return prefix + number

def is_valid_code(code):
    pattern = r"^BR\d{11}$"
    return re.match(pattern, code) is not None

@app.route('/generate-code', methods=['POST'])
def generate_code_route():
    code = generate_code()

    creation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Incluindo horas e minutos para comparar com precisão
    status1 = ("Objeto postado após o horário limite da unidade"
               " Sujeito a encaminhamento no próximo dia útil")
    location1 = "Manaus - AM"
    delivery_date1 = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    # Alterando para 2 minutos para o segundo status
    status2 = "Objeto em transferência - por favor aguarde"
    location2 = "de Unidade de Tratamento, Manaus - AM para Unidade de Tratamento, São Paulo - SP"
    delivery_date2 = (datetime.now() + timedelta(minutes=2)).strftime('%d/%m/%Y %H:%M:%S')

    # Alterando para 4 minutos para o terceiro status
    status3 = "TESTE"
    location3 = "TESTE"
    delivery_date3 = (datetime.now() + timedelta(minutes=4)).strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    conn.execute('''INSERT INTO tracking_codes (code, status1, location1, delivery_date1, 
                                                 status2, location2, delivery_date2,
                                                 status3, location3, delivery_date3,
                                                 creation_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (code, status1, location1, delivery_date1, status2, location2, delivery_date2,
                  status3, location3, delivery_date3, creation_date))
    conn.commit()
    conn.close()

    return jsonify({"code": code})

@app.route('/consult-code', methods=['POST'])
def consult_code_route():
    data = request.get_json()
    code = data.get("code", "")

    if not is_valid_code(code):
        return jsonify({"error": "Invalid code format"}), 400

    conn = get_db_connection()
    result = conn.execute('SELECT * FROM tracking_codes WHERE code = ?', (code,)).fetchone()
    conn.close()

    if result is None:
        return jsonify({"error": "Code not found"}), 404

    creation_date = datetime.strptime(result["creation_date"], '%Y-%m-%d %H:%M:%S')
    time_passed = (datetime.now() - creation_date).total_seconds() / 60  # Diferença em minutos

    # Informações que sempre estarão presentes
    info = {
        "code": result["code"],
        "status1": result["status1"],
        "location1": result["location1"],
        "delivery_date1": result["delivery_date1"]
    }

    # Se passaram 2 minutos, incluir o status2
    if time_passed >= 2:
        info.update({
            "status2": result["status2"],
            "location2": result["location2"],
            "delivery_date2": result["delivery_date2"]
        })

    # Se passaram 4 minutos, incluir o status3 (TESTE)
    if time_passed >= 4:
        info.update({
            "status3": result["status3"],
            "location3": result["location3"],
            "delivery_date3": result["delivery_date3"]
        })

    return jsonify(info)

# Rota para receber Webhook de venda e gerar código de rastreamento
@app.route('/webhook', methods=['POST'])
def webhook_route():
    data = request.get_json()

    # Aqui você pode validar o conteúdo do webhook (exemplo: checar se é uma venda válida)
    if data.get("event") == "sale_created":
        # Chama a função de gerar código
        return generate_code_route()

    return jsonify({"message": "Evento não tratado"}), 400

if __name__ == '__main__':
    create_table()
    app.run(debug=True)
