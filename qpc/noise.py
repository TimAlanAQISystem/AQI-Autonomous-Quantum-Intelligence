"""
QPC Noise Model - Failure and degradation profiles
"""

class NoiseModel:
    def __init__(self):
        self.anomalies = []

    def log_anomaly(self, anomaly_type: str, severity: float, details: str):
        self.anomalies.append({
            "type": anomaly_type,
            "severity": severity,
            "details": details,
            "timestamp": None # Add timestamp in real impl
        })
    
    def get_profile(self):
        """Return the noise profile for the current operation"""
        return self.anomalies
