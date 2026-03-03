from flask import Flask, request, jsonify, abort

app = Flask(__name__)
API_KEY = "change_this_to_a_secret_key"

def require_api_key():
    key = request.headers.get('X-API-KEY')
    if key != API_KEY:
        abort(401, description="Unauthorized: Invalid API Key")

@app.route('/dotnet/status', methods=['GET'])
def get_status():
    require_api_key()
    return jsonify({'system': 'AQI', 'status': 'online', 'message': '.NET door is open for integration.'})

@app.route('/dotnet/data', methods=['POST'])
def receive_data():
    require_api_key()
    data = request.json
    return jsonify({'received': data, 'result': 'Data accepted by AQI system.'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5051)
