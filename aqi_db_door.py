from flask import Flask, request, jsonify, abort
import sqlite3

app = Flask(__name__)
API_KEY = "change_this_to_a_secret_key"
DB_PATH = "aqi_system.db"

def require_api_key():
    key = request.headers.get('X-API-KEY')
    if key != API_KEY:
        abort(401, description="Unauthorized: Invalid API Key")

@app.route('/db/query', methods=['POST'])
def db_query():
    require_api_key()
    query = request.json.get('query')
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5053)
