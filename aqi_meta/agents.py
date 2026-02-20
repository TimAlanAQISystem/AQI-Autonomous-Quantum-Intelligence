import os
import openai
from openai import OpenAI

class Agent:
    """
    Represents an agent in the AQI meta-layer for proposal generation.
    Each agent processes signals and generates proposals using LLM when available.
    """
    def __init__(self, name, specialization=None):
        self.name = name
        self.specialization = specialization
        self.client = None
        self.llm_available = False
        
        # Initialize OpenAI client if key available
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                self.llm_available = True
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI client for {self.name}: {e}")

    def generate_proposal(self, signal):
        """
        Generates a proposal based on the input signal.
        Uses LLM for intelligent proposal generation when available.
        """
        if self.llm_available and self.client:
            try:
                prompt = f"""
                You are {self.name}, an AI agent specializing in {self.specialization or 'general intelligence'}.
                
                Analyze this signal: {signal.data}
                
                Generate a proposal for how to respond or act on this signal.
                Include:
                - Action: What should be done
                - Scope: Areas affected (e.g., ['business', 'technical'])
                - Confidence: Your confidence level (0-1)
                
                Respond in JSON format:
                {{
                    "action": "description of action",
                    "scope": ["area1", "area2"],
                    "confidence": 0.85
                }}
                """
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",  # Using cost-effective model
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.7
                )
                
                # Parse JSON response
                import json
                result = json.loads(response.choices[0].message.content.strip())
                
                proposal = {
                    'agent': self.name,
                    'action': result.get('action', f'Process {signal.data[:20]}...'),
                    'scope': result.get('scope', ['general']),
                    'confidence': result.get('confidence', 0.8)
                }
                
            except Exception as e:
                print(f"LLM call failed for {self.name}, using fallback: {e}")
                proposal = self._fallback_proposal(signal)
        else:
            proposal = self._fallback_proposal(signal)
            
        return proposal

    def _fallback_proposal(self, signal):
        """
        Fallback proposal generation when LLM is not available.
        """
        return {
            'agent': self.name,
            'action': f'Analyze and process: {signal.data[:50]}...',
            'scope': ['general'],
            'confidence': 0.7
        }

    def __repr__(self):
        return f"Agent(name={self.name}, specialization={self.specialization}, llm={self.llm_available})"


class AgentFactory:
    """
    Factory for creating and managing multiple agents.
    Supports scaling to hundreds of specialized agents.
    """
    
    def __init__(self):
        self.agent_templates = {
            'data_analysis': [
                'DataAnalyzer', 'PatternRecognizer', 'TrendPredictor', 'AnomalyDetector',
                'CorrelationEngine', 'StatisticalModeler', 'DataValidator', 'InsightExtractor'
            ],
            'decision_making': [
                'DecisionOptimizer', 'RiskAssessor', 'StrategyPlanner', 'OutcomePredictor',
                'ChoiceEvaluator', 'ConsequenceAnalyzer', 'DecisionValidator', 'ActionPrioritizer'
            ],
            'action_planning': [
                'TaskPlanner', 'ResourceAllocator', 'TimelineOptimizer', 'DependencyMapper',
                'ExecutionCoordinator', 'ProgressTracker', 'MilestoneManager', 'SuccessMeasurer'
            ],
            'risk_assessment': [
                'RiskQuantifier', 'ThreatAnalyzer', 'VulnerabilityScanner', 'ImpactPredictor',
                'MitigationPlanner', 'ContingencyDesigner', 'SafetyValidator', 'CrisisManager'
            ],
            'optimization': [
                'PerformanceOptimizer', 'EfficiencyAnalyzer', 'ResourceMaximizer', 'CostReducer',
                'QualityEnhancer', 'ScalabilityPlanner', 'AutomationEngine', 'ImprovementIdentifier'
            ],
            'communication': [
                'MessageComposer', 'StakeholderAnalyzer', 'ChannelOptimizer', 'ResponseGenerator',
                'FeedbackProcessor', 'RelationshipBuilder', 'ClarityEnhancer', 'PersuasionEngine'
            ],
            'learning': [
                'KnowledgeIntegrator', 'SkillAcquirer', 'PatternLearner', 'AdaptationEngine',
                'ExperienceProcessor', 'ImprovementTracker', 'ExpertiseBuilder', 'InnovationGenerator'
            ],
            'monitoring': [
                'SystemWatcher', 'PerformanceMonitor', 'HealthChecker', 'AlertGenerator',
                'MetricsCollector', 'AnomalyDetector', 'TrendAnalyzer', 'ComplianceValidator'
            ]
        }
        
    def create_agent_fleet(self, count_per_category: int = 5) -> List[Agent]:
        """
        Create a fleet of agents across all categories.
        
        Args:
            count_per_category: Number of agents per specialization category
            
        Returns:
            List of Agent instances
        """
        agents = []
        
        for category, templates in self.agent_templates.items():
            # Create specified number of agents per category
            for i in range(min(count_per_category, len(templates))):
                template = templates[i % len(templates)]
                agent_name = f"{template}_{category}_{i+1}"
                agent = Agent(agent_name, category)
                agents.append(agent)
        
        return agents
    
    def create_specialized_agent(self, name: str, specialization: str, 
                               custom_instructions: str = None) -> Agent:
        """
        Create a specialized agent with custom instructions.
        
        Args:
            name: Agent name
            specialization: Specialization area
            custom_instructions: Custom behavior instructions
            
        Returns:
            Configured Agent instance
        """
        agent = Agent(name, specialization)
        if custom_instructions:
            agent.custom_instructions = custom_instructions
        return agent
    
    def get_agent_metrics(self, agents: List[Agent]) -> Dict[str, Any]:
        """
        Get metrics about the agent fleet.
        
        Args:
            agents: List of agents to analyze
            
        Returns:
            Fleet metrics
        """
        total_agents = len(agents)
        llm_enabled = sum(1 for agent in agents if agent.llm_available)
        specializations = {}
        
        for agent in agents:
            spec = agent.specialization or 'general'
            specializations[spec] = specializations.get(spec, 0) + 1
        
        return {
            'total_agents': total_agents,
            'llm_enabled_agents': llm_enabled,
            'llm_coverage': llm_enabled / total_agents if total_agents > 0 else 0,
            'specializations': specializations,
            'categories_count': len(specializations)
        }