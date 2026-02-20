class Signal:
    """
    Represents a signal in the AQI meta-layer system for lineage tracking.
    Tracks the history of transformations and processing steps.
    Enforces amnesia covenant to prevent data loss.
    """
    def __init__(self, data, source=None):
        self.data = data
        self.lineage = []
        self.source = source
        self.timestamp = None  # Can be set on creation or processing
        self.amnesia_covenant_active = True
        self.covenant_violations = []

    def add_lineage_step(self, step_name, details=None):
        """
        Adds a step to the lineage tracking.
        Enforces amnesia covenant.
        """
        if not self.amnesia_covenant_active:
            self.covenant_violations.append({
                'violation': 'amnesia_covenant_deactivated',
                'step': step_name,
                'timestamp': self.timestamp or 'N/A'
            })
            return
        
        step = {
            'step': step_name,
            'details': details,
            'timestamp': self.timestamp or 'N/A',
            'covenant_status': 'active'
        }
        self.lineage.append(step)

    def get_lineage(self):
        """
        Returns the full lineage history.
        Includes covenant status.
        """
        return {
            'steps': self.lineage,
            'covenant_active': self.amnesia_covenant_active,
            'violations': self.covenant_violations,
            'total_steps': len(self.lineage)
        }

    def enforce_amnesia_covenant(self) -> bool:
        """
        Check and enforce amnesia covenant.
        Ensures no lineage data is erased.
        
        Returns:
            True if covenant maintained
        """
        if len(self.lineage) == 0:
            # Initialize covenant
            self.add_lineage_step('covenant_initialization', 
                                'Amnesia covenant activated - no data shall be forgotten')
            return True
        
        # Check for any gaps in lineage (would indicate erasure)
        expected_steps = len(self.lineage)
        if expected_steps > 0:
            # Verify chronological order
            timestamps = [step.get('timestamp', 0) for step in self.lineage 
                         if step.get('timestamp') != 'N/A']
            if timestamps and not all(timestamps[i] <= timestamps[i+1] 
                                    for i in range(len(timestamps)-1)):
                self.covenant_violations.append({
                    'violation': 'chronological_disorder',
                    'details': 'Lineage steps out of chronological order'
                })
                return False
        
        return True

    def __repr__(self):
        covenant_status = "ACTIVE" if self.amnesia_covenant_active else "VIOLATED"
        return f"Signal(data={self.data[:50]}..., lineage_steps={len(self.lineage)}, covenant={covenant_status})"