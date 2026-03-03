from flask import Flask, request, jsonify, abort


API_KEY = "change_this_to_a_secret_key"
app = Flask(__name__)


def require_api_key():
    key = request.headers.get('X-API-KEY')
    if key != API_KEY:
        abort(401, description="Unauthorized: Invalid API Key")

@app.route('/aqi/status', methods=['GET'])
def get_status():
    require_api_key()
    return jsonify({
        'system': 'AQI',
        'status': 'online',
        'message': 'Java door is open for integration.'
    })


@app.route('/aqi/data', methods=['POST'])
def receive_data():
    require_api_key()
    data = request.json
    return jsonify({
        'received': data,
        'result': 'Data accepted by AQI system.'
    })

if __name__ == '__main__':
    # Bind only to localhost for security
    app.run(host='127.0.0.1', port=5050)
