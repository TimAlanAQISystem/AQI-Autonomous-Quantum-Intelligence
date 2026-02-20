"""
AQI Meta-Layer Dashboard
Web interface for monitoring and interacting with the AQI system.
"""

from flask import Flask, render_template, request, jsonify
import json
import time
from lineage import Signal
from field_layer import FieldLayer
from agents import AgentFactory
from business_engine import BusinessEngine
from cyber_defense_core import CyberDefenseCore

app = Flask(__name__)

# Global instances
agent_factory = AgentFactory()
business_engine = BusinessEngine()
cyber_defense = CyberDefenseCore()

# Create agent fleet
agents = agent_factory.create_agent_fleet(3)
field_layer = FieldLayer(agents)

@app.route('/')
def dashboard():
    """Main dashboard page"""
    metrics = agent_factory.get_agent_metrics(agents)
    security_status = cyber_defense.get_security_status()
    
    return render_template('dashboard.html', 
                         metrics=metrics, 
                         security=security_status)

@app.route('/process_signal', methods=['POST'])
def process_signal():
    """Process a new signal through the meta-layer"""
    data = request.json
    signal_text = data.get('signal', 'Default test signal')
    
    # Create signal
    signal = Signal(signal_text, source="dashboard")
    signal.timestamp = time.time()
    
    # Process through pipeline
    try:
        proposals = field_layer.orchestrate(signal)
        
        # Get final lineage
        lineage = signal.get_lineage()
        
        result = {
            'success': True,
            'proposals_generated': len(proposals),
            'lineage_steps': len(lineage['steps']),
            'covenant_status': lineage['covenant_active'],
            'processing_time': time.time() - signal.timestamp
        }
    except Exception as e:
        result = {
            'success': False,
            'error': str(e)
        }
    
    return jsonify(result)

@app.route('/business_projection', methods=['POST'])
def business_projection():
    """Generate business revenue projections"""
    data = request.json
    monthly_boardings = int(data.get('monthly_boardings', 10))
    avg_volume = float(data.get('avg_volume', 25000))
    months = int(data.get('months', 12))
    
    projection = business_engine.project_revenue(monthly_boardings, avg_volume, months)
    
    return jsonify(projection)

@app.route('/security_status')
def security_status():
    """Get current security status"""
    status = cyber_defense.get_security_status()
    return jsonify(status)

@app.route('/agent_metrics')
def agent_metrics():
    """Get agent fleet metrics"""
    metrics = agent_factory.get_agent_metrics(agents)
    return jsonify(metrics)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)