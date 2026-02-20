"""
Test Suite for AQI Meta-Layer
Comprehensive testing of all meta-layer components.
"""

import unittest
import time
from lineage import Signal
from agents import Agent, AgentFactory
from authority import Authority
from ethics import EthicsEngine
from surplus import SurplusEngine
from field_layer import FieldLayer
from business_engine import BusinessEngine
from data_ingestion import DataIngestionEngine
from twilio_integration import TwilioIntegration
from quantum_engine import QuantumPDEEngine
from cyber_defense_core import CyberDefenseCore

class TestMetaLayer(unittest.TestCase):
    """Test cases for AQI meta-layer components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.signal = Signal("Test merchant data", source="test")
        self.signal.timestamp = time.time()
        
        self.agent = Agent("TestAgent", "data_analysis")
        self.factory = AgentFactory()
        
    def test_signal_lineage(self):
        """Test signal lineage tracking"""
        self.signal.add_lineage_step("test_step", "Testing lineage")
        lineage = self.signal.get_lineage()
        
        self.assertIsInstance(lineage, dict)
        self.assertGreater(len(lineage['steps']), 0)
        self.assertTrue(lineage['covenant_active'])
    
    def test_agent_proposal_generation(self):
        """Test agent proposal generation"""
        proposal = self.agent.generate_proposal(self.signal)
        
        self.assertIsInstance(proposal, dict)
        self.assertIn('agent', proposal)
        self.assertIn('action', proposal)
        self.assertIn('scope', proposal)
        self.assertIn('confidence', proposal)
    
    def test_agent_factory(self):
        """Test agent factory scaling"""
        agents = self.factory.create_agent_fleet(2)
        
        self.assertIsInstance(agents, list)
        self.assertGreater(len(agents), 0)
        
        metrics = self.factory.get_agent_metrics(agents)
        self.assertIn('total_agents', metrics)
        self.assertIn('specializations', metrics)
    
    def test_business_engine(self):
        """Test business logic calculations"""
        engine = BusinessEngine()
        
        # Test commission calculation
        calc = engine.calculate_commission(25000)  # $25k monthly volume
        self.assertIn('first_month_total', calc)
        self.assertGreater(calc['first_month_total'], 0)
        
        # Test merchant qualification
        merchant = {
            'monthly_volume': 15000,
            'business_type': 'retail',
            'risk_score': 0.3
        }
        qual = engine.qualify_merchant(merchant)
        self.assertIn('qualified', qual)
    
    def test_data_ingestion(self):
        """Test data ingestion engine"""
        engine = DataIngestionEngine()
        
        signals = engine.fetch_merchant_signals("Test Company")
        self.assertIsInstance(signals, dict)
        self.assertIn('company', signals)
        self.assertIn('signals', signals)
        
        score = engine.score_merchant_potential(signals)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_twilio_integration(self):
        """Test Twilio integration (mock)"""
        twilio = TwilioIntegration()
        
        # Test TwiML generation
        twiml = twilio.generate_twiml_response("Hello from AQI")
        self.assertIsInstance(twiml, str)
        self.assertIn('Response', twiml)
    
    def test_quantum_engine(self):
        """Test quantum PDE engine"""
        engine = QuantumPDEEngine()
        
        problem = {
            'variables': ['option_a', 'option_b', 'option_c'],
            'constraints': [
                {'variable': 'option_a', 'energy_penalty': 0.5},
                {'variable': 'option_b', 'energy_penalty': 0.2}
            ]
        }
        
        state = engine.initialize_quantum_state(problem)
        self.assertIn('superposition', state)
        self.assertIn('potential_well', state)
        
        result = engine.optimize_decision(problem)
        self.assertIn('optimal_solution', result)
    
    def test_cyber_defense(self):
        """Test cyber defense core"""
        defense = CyberDefenseCore()
        
        # Test threat scanning
        clean_data = "Normal business data"
        assessment = defense.scan_for_threats(clean_data)
        self.assertEqual(assessment['risk_level'], 'low')
        
        # Test with threat
        malicious_data = "DROP TABLE users; SELECT * FROM secrets"
        assessment = defense.scan_for_threats(malicious_data)
        self.assertIn('threats_found', assessment)
        
        # Test integrity validation
        valid = defense.validate_integrity('test_component', 'test_data')
        self.assertTrue(valid)
        
        status = defense.get_security_status()
        self.assertIn('overall_status', status)
    
    def test_full_pipeline(self):
        """Test complete meta-layer pipeline"""
        # Create agents
        agents = self.factory.create_agent_fleet(1)
        field = FieldLayer(agents)
        
        # Generate proposals
        proposals = field.orchestrate(self.signal)
        self.assertIsInstance(proposals, list)
        
        # Authority filtering
        authority = Authority()
        filtered = authority.enforce_non_overlap(proposals)
        self.assertIsInstance(filtered, list)
        
        # Ethics evaluation
        ethics = EthicsEngine()
        ethical = []
        for prop in filtered:
            result = ethics.evaluate_repulsion(prop)
            if result[0]:  # is_ethical
                ethical.append(prop)
        
        # Surplus scoring
        surplus = SurplusEngine()
        scored = [(prop, surplus.score(prop)) for prop in ethical]
        
        # Verify pipeline completion
        self.assertIsInstance(scored, list)
        if scored:
            self.assertIsInstance(scored[0], tuple)
            self.assertIsInstance(scored[0][1], (int, float))

if __name__ == '__main__':
    unittest.main()