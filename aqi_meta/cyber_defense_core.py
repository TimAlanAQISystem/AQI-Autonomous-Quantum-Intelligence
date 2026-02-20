"""
Cyber Defense Core for AQI Meta-Layer
Provides autonomous security monitoring and threat response.
"""

import os
import hashlib
import time
from typing import Dict, List, Any, Optional
import logging

class CyberDefenseCore:
    """
    Autonomous cyber defense system for AQI.
    Monitors for threats, validates integrity, and responds to attacks.
    """
    
    def __init__(self):
        self.threat_patterns = self._load_threat_patterns()
        self.integrity_hashes = {}
        self.security_log = []
        self.defense_active = True
        
        # Setup logging
        self.logger = logging.getLogger('CyberDefenseCore')
        self.logger.setLevel(logging.INFO)
        
    def _load_threat_patterns(self) -> Dict[str, List[str]]:
        """Load known threat patterns and signatures"""
        return {
            'injection_attacks': [
                'DROP TABLE', 'UNION SELECT', 'SCRIPT', '<script>', 'eval(',
                'exec(', 'system(', 'shell_exec('
            ],
            'data_exfiltration': [
                'SELECT * FROM', 'DUMP', 'EXPORT', 'wget', 'curl',
                'base64', 'hex', 'encode'
            ],
            'denial_of_service': [
                'FLOOD', 'DDOS', 'INFINITE LOOP', 'WHILE TRUE',
                'FORK BOMB', 'RESOURCE EXHAUSTION'
            ],
            'privilege_escalation': [
                'SUDO', 'ROOT', 'ADMIN', 'ELEVATE', 'SETUID',
                'CHMOD 777', 'SUPERUSER'
            ],
            'amnesia_violations': [
                'DELETE', 'TRUNCATE', 'DROP', 'ERASE', 'FORGET',
                'CLEAR HISTORY', 'WIPE'
            ]
        }
    
    def scan_for_threats(self, data: Any, context: str = 'general') -> Dict[str, Any]:
        """
        Scan data for security threats.
        
        Args:
            data: Data to scan (string, dict, list, etc.)
            context: Context of the scan
            
        Returns:
            Threat assessment
        """
        threats_found = []
        risk_level = 'low'
        
        # Convert data to string for scanning
        data_str = str(data).upper()
        
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                if pattern.upper() in data_str:
                    threats_found.append({
                        'type': threat_type,
                        'pattern': pattern,
                        'context': context,
                        'timestamp': time.time()
                    })
                    # Escalate risk level
                    if threat_type in ['injection_attacks', 'privilege_escalation']:
                        risk_level = 'high'
                    elif risk_level == 'low':
                        risk_level = 'medium'
        
        assessment = {
            'threats_found': threats_found,
            'risk_level': risk_level,
            'scan_context': context,
            'data_size': len(data_str),
            'timestamp': time.time()
        }
        
        if threats_found:
            self.logger.warning(f"Threats detected: {len(threats_found)} threats, risk: {risk_level}")
            self.security_log.append(assessment)
        
        return assessment
    
    def validate_integrity(self, component: str, data: Any) -> bool:
        """
        Validate integrity of system components.
        
        Args:
            component: Component name
            data: Component data to validate
            
        Returns:
            True if integrity intact
        """
        data_str = str(data)
        current_hash = hashlib.sha256(data_str.encode()).hexdigest()
        
        if component in self.integrity_hashes:
            stored_hash = self.integrity_hashes[component]
            if current_hash != stored_hash:
                self.logger.error(f"Integrity violation in {component}")
                self.security_log.append({
                    'event': 'integrity_violation',
                    'component': component,
                    'timestamp': time.time()
                })
                return False
        
        # Update stored hash
        self.integrity_hashes[component] = current_hash
        return True
    
    def activate_defense_measures(self, threat_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Activate appropriate defense measures based on threat assessment.
        
        Args:
            threat_assessment: Results from threat scan
            
        Returns:
            Defense actions taken
        """
        actions_taken = []
        risk_level = threat_assessment.get('risk_level', 'low')
        
        if risk_level == 'high':
            actions_taken.extend(self._high_risk_response(threat_assessment))
        elif risk_level == 'medium':
            actions_taken.extend(self._medium_risk_response(threat_assessment))
        else:
            actions_taken.append('threat_logged')
        
        self.security_log.append({
            'event': 'defense_activated',
            'threat_assessment': threat_assessment,
            'actions': actions_taken,
            'timestamp': time.time()
        })
        
        return {
            'actions_taken': actions_taken,
            'defense_status': 'active' if self.defense_active else 'standby',
            'threat_contained': len(actions_taken) > 1
        }
    
    def _high_risk_response(self, threat_assessment: Dict[str, Any]) -> List[str]:
        """Response to high-risk threats"""
        actions = [
            'isolate_component',
            'alert_administrator',
            'log_security_incident',
            'increase_monitoring'
        ]
        
        # Check for amnesia violations specifically
        threats = threat_assessment.get('threats_found', [])
        for threat in threats:
            if threat['type'] == 'amnesia_violations':
                actions.append('amnesia_covenant_enforcement')
                break
        
        return actions
    
    def _medium_risk_response(self, threat_assessment: Dict[str, Any]) -> List[str]:
        """Response to medium-risk threats"""
        return [
            'log_security_event',
            'increase_monitoring',
            'validate_integrity'
        ]
    
    def get_security_status(self) -> Dict[str, Any]:
        """
        Get current security status.
        
        Returns:
            Security status summary
        """
        recent_threats = [log for log in self.security_log 
                         if log.get('threats_found') and 
                         time.time() - log['timestamp'] < 3600]  # Last hour
        
        return {
            'defense_active': self.defense_active,
            'threats_last_hour': len(recent_threats),
            'integrity_checks': len(self.integrity_hashes),
            'security_events': len(self.security_log),
            'monitored_components': list(self.integrity_hashes.keys()),
            'overall_status': 'secure' if len(recent_threats) == 0 else 'monitoring'
        }
    
    def quarantine_data(self, data: Any, reason: str) -> Dict[str, Any]:
        """
        Quarantine suspicious data for analysis.
        
        Args:
            data: Data to quarantine
            reason: Reason for quarantine
            
        Returns:
            Quarantine record
        """
        quarantine_record = {
            'data_hash': hashlib.sha256(str(data).encode()).hexdigest(),
            'reason': reason,
            'timestamp': time.time(),
            'status': 'quarantined'
        }
        
        self.security_log.append({
            'event': 'data_quarantined',
            'record': quarantine_record
        })
        
        return quarantine_record
    
    def audit_trail(self, component: str = None, hours: int = 24) -> List[Dict]:
        """
        Get security audit trail.
        
        Args:
            component: Specific component to audit (optional)
            hours: Hours of history to retrieve
            
        Returns:
            Audit trail entries
        """
        cutoff_time = time.time() - (hours * 3600)
        
        trail = [entry for entry in self.security_log 
                if entry.get('timestamp', 0) > cutoff_time]
        
        if component:
            trail = [entry for entry in trail 
                    if entry.get('component') == component]
        
        return trail