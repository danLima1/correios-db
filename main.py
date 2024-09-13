from flask import Flask, jsonify, request
import random
import re
import sqlite3
from flask_cors import CORS
from datetime import datetime, timedelta
import pytz  # Biblioteca para lidar com fusos horários

app = Flask(__name__)

# Configurar CORS para permitir apenas https://correios-nine.vercel.app
CORS()

# Definindo o fuso horário do Brasil
br_tz = pytz.timezone('America/Sao_Paulo')

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
                        creation_date TEXT NOT NULL,
                        previsao_entrega TEXT
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

    # Usar o horário atual no fuso horário do Brasil
    now = datetime.now(br_tz)
    creation_date = now.strftime('%Y-%m-%d %H:%M:%S')  # Incluindo horas e minutos
    status1 = "Objeto postado após o horário limite da unidade"
    location1 = "Manaus - AM"
    delivery_date1 = now.strftime('%d/%m/%Y %H:%M:%S')

    # Alterando para 2 minutos para o segundo status
    status2 = "Objeto em transferência - por favor aguarde"
    delivery_date2 = (now + timedelta(minutes=2)).strftime('%d/%m/%Y %H:%M:%S')
    location2 = "de Unidade de Tratamento, Manaus - AM<br>para Unidade de Tratamento, Cajamar - SP"

    # Alterando para 4 minutos para o terceiro status
    status3 = "Objeto em transferência - por favor aguarde"
    delivery_date3 = (now + timedelta(minutes=4)).strftime('%d/%m/%Y %H:%M:%S')
    location3 = "de Unidade de Tratamento, Cajamar - SP<br>para Unidade de Tratamento, São Paulo - SP"

    # Previsão de entrega: 8 dias após a criação do código
    previsao_entrega = (now + timedelta(days=8)).strftime('%d/%m/%Y')

    conn = get_db_connection()
    conn.execute('''INSERT INTO tracking_codes (code, status1, location1, delivery_date1, 
                                                 status2, location2, delivery_date2,
                                                 status3, location3, delivery_date3,
                                                 creation_date, previsao_entrega)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (code, status1, location1, delivery_date1, status2, location2, delivery_date2,
                  status3, location3, delivery_date3, creation_date, previsao_entrega))
    conn.commit()
    conn.close()

    return jsonify({
        "code": code,
        "previsao_entrega": previsao_entrega
    })

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

    # Pegando o valor de creation_date do banco de dados (que é naive)
    creation_date_naive = datetime.strptime(result["creation_date"], '%Y-%m-%d %H:%M:%S')

    # Tornando o creation_date ciente do fuso horário (timezone-aware)
    creation_date = br_tz.localize(creation_date_naive)

    # Calcular a diferença de tempo entre o horário atual e a criação do código
    time_passed = (datetime.now(br_tz) - creation_date).total_seconds() / 60  # Diferença em minutos

    # Informações que sempre estarão presentes
    info = {
        "code": result["code"],
        "status1": result["status1"],
        "location1": result["location1"],
        "delivery_date1": result["delivery_date1"],
        "previsao_entrega": result["previsao_entrega"]  # Inclui a previsão de entrega
    }

    # Se passaram 2 minutos, incluir o status2
    if time_passed >= 2:
        info.update({
            "status2": result["status2"],
            "location2": result["location2"],
            "delivery_date2": result["delivery_date2"]
        })

    # Se passaram 4 minutos, incluir o status3
    if time_passed >= 4:
        info.update({
            "status3": result["status3"],
            "location3": result["location3"],
            "delivery_date3": result["delivery_date3"]
        })

    return jsonify(info)


# Rota para receber Webhook de venda e gerar código de rastreamento
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    # Extraindo os dados relevantes do payload
    payment_id = data.get('paymentId')
    customer_info = data.get('customer', {})
    customer_name = customer_info.get('name')

    if not payment_id or not customer_name:
        return jsonify({"error": "Payload inválido, falta 'paymentId' ou 'customer_name'"}), 400

    # Gerar o código de rastreamento automaticamente
    code = generate_code()

    # Usar o horário atual no fuso horário do Brasil
    now = datetime.now(br_tz)
    creation_date = now.strftime('%Y-%m-%d %H:%M:%S')  # Incluindo horas e minutos
    status1 = "Objeto postado após o horário limite da unidade"
    location1 = "Manaus - AM"
    delivery_date1 = now.strftime('%d/%m/%Y %H:%M:%S')

    # Alterando para 2 minutos para o segundo status
    status2 = "Objeto em transferência - por favor aguarde"
    delivery_date2 = (now + timedelta(minutes=2)).strftime('%d/%m/%Y %H:%M:%S')
    location2 = "de Unidade de Tratamento, Manaus - AM<br>para Unidade de Tratamento, Cajamar - SP"

    # Alterando para 4 minutos para o terceiro status
    status3 = "Objeto em transferência - por favor aguarde"
    delivery_date3 = (now + timedelta(minutes=4)).strftime('%d/%m/%Y %H:%M:%S')
    location3 = "de Unidade de Tratamento, Cajamar - SP<br>para Unidade de Tratamento, São Paulo - SP"

    # Previsão de entrega: 8 dias após a criação do código
    previsao_entrega = (now + timedelta(days=8)).strftime('%d/%m/%Y')

    conn = get_db_connection()
    conn.execute('''INSERT INTO tracking_codes (code, status1, location1, delivery_date1, 
                                                   status2, location2, delivery_date2,
                                                   status3, location3, delivery_date3,
                                                   creation_date, previsao_entrega)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (code, status1, location1, delivery_date1, status2, location2, delivery_date2,
                  status3, location3, delivery_date3, creation_date, previsao_entrega))
    conn.commit()
    conn.close()

    return jsonify({
        "code": code,
        "previsao_entrega": previsao_entrega
    })

if __name__ == '__main__':
    create_table()
    app.run(debug=True)
