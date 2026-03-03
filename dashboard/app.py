import os
import sys
import json
import time
import subprocess
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request

# Configuration
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
DATA_DIR = os.path.join(BASE_DIR, 'data')

app = Flask(__name__)

# --- HELPER FUNCTIONS ---

def get_agent_status(agent_name):
    """
    Checks if an agent is running. 
    For now, we simulate this or check for specific lock files/ports.
    In a real deployment, we'd check PIDs.
    """
    # Simulation for the prototype
    # In production, check for PID files in logs/
    return "Active" if os.path.exists(os.path.join(BASE_DIR, f"{agent_name}.pid")) else "Standby"

def read_last_logs(lines=20):
    """Reads the main system log."""
    log_file = os.path.join(LOG_DIR, 'system.log') # Assuming a main log
    if not os.path.exists(log_file):
        return ["System log not found."]
    
    try:
        with open(log_file, 'r') as f:
            return f.readlines()[-lines:]
    except:
        return ["Error reading logs."]

def get_council_decisions():
    """Reads the council log if it exists."""
    # We'll assume council logs to a specific file or just return dummy data for now
    # based on the aqi_council.py output we saw earlier.
    return [
        {"timestamp": "2025-11-22 12:08", "topic": "Expand Merchant Services", "verdict": "APPROVED (With Legal Amendments)"}
    ]

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    return jsonify({
        "system_status": "OPERATIONAL",
        "agents": [
            {"name": "Alan", "role": "Business AI", "status": "Active", "icon": "💼"},
            {"name": "Agent X", "role": "System Core", "status": "Active", "icon": "🧠"},
            {"name": "Veronica", "role": "Legal", "status": "Active", "icon": "⚖️"},
            {"name": "RSE", "role": "Research", "status": "Standby", "icon": "📡"}
        ],
        "financials": {
            "daily_calls": 0,
            "leads_found": 12,
            "compliance_blocks": 1
        }
    })

@app.route('/api/logs')
def api_logs():
    return jsonify({"logs": read_last_logs()})

@app.route('/api/council')
def api_council():
    return jsonify({"decisions": get_council_decisions()})

@app.route('/api/action', methods=['POST'])
def api_action():
    data = request.json
    action = data.get('action')
    agent = data.get('agent')
    
    # Here we would actually trigger the scripts
    print(f"Received command: {action} for {agent}")
    
    return jsonify({"status": "success", "message": f"Command '{action}' sent to {agent}"})

if __name__ == '__main__':
    print("🚀 AQI COMMAND DASHBOARD STARTING...")
    print("   http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
