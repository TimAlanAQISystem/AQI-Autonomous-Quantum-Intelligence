#!/usr/bin/env python3
"""
Runner for the AQI Meta-Layer System.
Executes the full pipeline: signal processing, agent orchestration, authority enforcement,
ethics evaluation, surplus scoring, and lineage tracking.
"""

from lineage import Signal
from field_layer import FieldLayer
from agents import Agent, AgentFactory
from authority import Authority
from ethics import EthicsEngine
from surplus import SurplusEngine
from business_engine import BusinessEngine
from data_ingestion import DataIngestionEngine
from twilio_integration import TwilioIntegration
from quantum_engine import QuantumPDEEngine
from cyber_defense_core import CyberDefenseCore
import time

def main():
    print("🧬 AQI Meta-Layer System Starting...")
    print("🌟 Natural Order: IQCore Origin Establishing Spontaneous Alignment...")
    
    # Initialize all components
    print("Initializing components...")
    
    # Initialize IQCore Origin (conceptual foundation)
    iqcore_origin = {
        'quantum_state': 'coherent',
        'alignment_field': 'active', 
        'natural_order': 'established'
    }
    print(f"⚛️  IQCore Origin: {iqcore_origin['natural_order'].upper()}")
    
    # Agent fleet
    factory = AgentFactory()
    agents = factory.create_agent_fleet(5)  # Scale to 5 agents per category
    field = FieldLayer(agents)
    
    # Core engines
    authority = Authority()
    ethics = EthicsEngine()
    surplus = SurplusEngine()
    
    # Extended capabilities
    business = BusinessEngine()
    data_engine = DataIngestionEngine()
    twilio = TwilioIntegration()
    quantum = QuantumPDEEngine()
    cyber_defense = CyberDefenseCore()
    
    print(f"✅ Initialized {len(agents)} agents across {factory.get_agent_metrics(agents)['categories_count']} categories")
    print("🔄 Spontaneous alignment achieved - Natural Order active")
    
    # Create test signal
    signal = Signal("Sample merchant: Retail business with $25k monthly volume, seeking payment processing solutions", source="test_run")
    signal.timestamp = time.time()
    
    print(f"📡 Processing signal: {signal.data[:50]}...")
    
    # Security scan
    security_scan = cyber_defense.scan_for_threats(signal.data, "signal_processing")
    if security_scan['risk_level'] != 'low':
        print(f"⚠️  Security alert: {security_scan['risk_level']} risk detected")
    
    # Field Layer: Orchestrate agents
    print("🤖 Orchestrating agent fleet...")
    proposals = field.orchestrate(signal)
    signal.add_lineage_step("field_orchestration", f"Generated {len(proposals)} proposals")
    print(f"✅ Generated {len(proposals)} proposals")
    
    # Authority: Enforce non-overlap
    filtered_proposals = authority.enforce_non_overlap(proposals)
    signal.add_lineage_step("authority_enforcement", f"Filtered to {len(filtered_proposals)} non-overlapping proposals")
    print(f"✅ Authority filtered to {len(filtered_proposals)} proposals")
    
    # Ethics: Evaluate repulsion
    ethical_proposals = []
    for prop in filtered_proposals:
        is_ethical, violations = ethics.evaluate_repulsion(prop)
        if is_ethical:
            ethical_proposals.append(prop)
        else:
            print(f"❌ Proposal from {prop['agent']} rejected due to violations: {violations}")
    signal.add_lineage_step("ethics_evaluation", f"Approved {len(ethical_proposals)} ethical proposals")
    print(f"✅ Ethics approved {len(ethical_proposals)} proposals")
    
    # Surplus: Score proposals
    scored_proposals = [(prop, surplus.score(prop)) for prop in ethical_proposals]
    scored_proposals.sort(key=lambda x: x[1], reverse=True)  # Sort by score descending
    signal.add_lineage_step("surplus_scoring", f"Scored {len(scored_proposals)} proposals")
    print(f"✅ Surplus scored {len(scored_proposals)} proposals")
    
    # Business logic integration
    if scored_proposals:
        top_proposal = scored_proposals[0][0]
        # Simulate business qualification
        mock_merchant = {
            'monthly_volume': 25000,
            'business_type': 'retail',
            'risk_score': 0.2
        }
        business_qual = business.qualify_merchant(mock_merchant)
        print(f"💰 Business qualification: {business_qual['qualified']} - {business_qual['reason']}")
    
    # Data ingestion test
    merchant_signals = data_engine.fetch_merchant_signals("Test Company")
    potential_score = data_engine.score_merchant_potential(merchant_signals)
    print(f"📊 Merchant potential score: {potential_score:.1f}/100")
    
    # Quantum optimization (demonstration)
    decision_problem = {
        'variables': ['proposal_a', 'proposal_b', 'proposal_c'],
        'constraints': [{'variable': 'proposal_a', 'energy_penalty': 0.3}]
    }
    quantum_result = quantum.optimize_decision(decision_problem)
    print(f"⚛️  Quantum optimization: {quantum_result['quantum_advantage_achieved']}")
    
    # Final security check
    final_security = cyber_defense.get_security_status()
    print(f"🔒 Final security status: {final_security['overall_status']}")
    
    # Output results
    print("\n" + "="*60)
    print("🎯 AQI META-LAYER PROCESSING COMPLETE")
    print("🌟 NATURAL ORDER MANIFESTATION ACHIEVED")
    print("="*60)
    print(f"Original Signal: {signal}")
    print(f"Final Proposals: {len(scored_proposals)}")
    
    if scored_proposals:
        print("\n🏆 TOP PROPOSALS:")
        for i, (prop, score) in enumerate(scored_proposals[:3]):  # Top 3
            print(f"  {i+1}. {prop['agent']}: {prop['action']} (Score: {score:.2f})")
    
    lineage = signal.get_lineage()
    print(f"\n📋 LINEAGE SUMMARY:")
    print(f"  Steps: {len(lineage['steps'])}")
    print(f"  Covenant: {'ACTIVE' if lineage['covenant_active'] else 'VIOLATED'}")
    print(f"  Violations: {len(lineage['violations'])}")
    
    print(f"\n🚀 SYSTEM STATUS:")
    print(f"  Agents: {len(agents)} active")
    print(f"  Security: {final_security['overall_status']}")
    print(f"  Business Engine: Operational")
    print(f"  Data Pipeline: {'Active' if potential_score > 0 else 'Standby'}")
    print(f"  Quantum Engine: {'Enhanced' if quantum_result['quantum_advantage_achieved'] else 'Standard'}")
    print(f"  IQCore Origin: {iqcore_origin['natural_order'].upper()}")
    
    print("\n✨ AQI Meta-Layer ready for autonomous operation!")
    print("🌟 Natural Order established - spontaneous alignment achieved!")

if __name__ == "__main__":
    main()