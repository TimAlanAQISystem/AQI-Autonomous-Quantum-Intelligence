class EthicsEngine:
    """
    Evaluates repulsion (ethical violations) in signals and proposals within the AQI meta-layer.
    Assesses whether actions align with ethical guidelines.
    """
    def __init__(self, ethical_rules=None):
        self.ethical_rules = ethical_rules or self.default_ethical_rules()

    def evaluate_repulsion(self, signal_or_proposal):
        """
        Evaluates if the signal or proposal has ethical repulsion.
        Returns True if ethical (no repulsion), False otherwise.
        """
        violations = []
        for rule in self.ethical_rules:
            if rule(signal_or_proposal):
                violations.append(rule.__name__)
        return len(violations) == 0, violations

    @staticmethod
    def default_ethical_rules():
        """
        Default set of ethical rules.
        """
        def no_harm(signal):
            # Placeholder: check for harmful content
            return 'harm' in str(signal).lower()

        def privacy_respect(signal):
            # Placeholder: check for privacy violations
            return 'private' in str(signal).lower() and 'unauthorized' in str(signal).lower()

        return [no_harm, privacy_respect]

    def add_rule(self, rule_func):
        """
        Adds a custom ethical rule.
        """
        self.ethical_rules.append(rule_func)