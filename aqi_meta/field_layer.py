from agents import Agent

class FieldLayer:
    """
    Orchestrates multi-agent processing in the AQI meta-layer.
    Manages a field of agents to process signals and generate coordinated proposals.
    """
    def __init__(self, agents=None):
        self.agents = agents or []

    def add_agent(self, agent):
        """
        Adds an agent to the field.
        """
        self.agents.append(agent)

    def orchestrate(self, signal):
        """
        Orchestrates agents to process the signal and generate proposals.
        """
        proposals = []
        for agent in self.agents:
            proposal = agent.generate_proposal(signal)
            proposals.append(proposal)
        return proposals

    def get_agents(self):
        """
        Returns the list of agents.
        """
        return self.agents

    def __repr__(self):
        return f"FieldLayer(agents={len(self.agents)})"