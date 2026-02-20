class SurplusEngine:
    """
    Scores surplus value in signals and proposals within the AQI meta-layer.
    Evaluates the potential benefit or value addition.
    """
    def __init__(self, scoring_function=None):
        self.scoring_function = scoring_function or self.default_scoring

    def score(self, signal_or_proposal):
        """
        Calculates the surplus score.
        """
        return self.scoring_function(signal_or_proposal)

    @staticmethod
    def default_scoring(obj):
        """
        Default scoring: based on data length or complexity.
        """
        data = obj.data if hasattr(obj, 'data') else str(obj)
        return len(data) * 0.1  # Placeholder score

    def set_scoring_function(self, func):
        """
        Sets a custom scoring function.
        """
        self.scoring_function = func