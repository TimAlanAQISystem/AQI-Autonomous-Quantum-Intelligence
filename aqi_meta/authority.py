class Authority:
    """
    Enforces non-overlap in proposals within the AQI meta-layer.
    Ensures that selected proposals do not conflict or overlap in their actions or scopes.
    """
    def __init__(self, overlap_criteria=None):
        self.overlap_criteria = overlap_criteria or self.default_overlap_check

    def enforce_non_overlap(self, proposals):
        """
        Filters proposals to remove overlapping ones.
        """
        filtered = []
        for proposal in proposals:
            if not any(self.overlap_criteria(proposal, existing) for existing in filtered):
                filtered.append(proposal)
        return filtered

    @staticmethod
    def default_overlap_check(p1, p2):
        """
        Default overlap check: assumes proposals have 'scope' as a set.
        """
        if 'scope' in p1 and 'scope' in p2:
            return bool(set(p1['scope']) & set(p2['scope']))
        return False

    def set_overlap_criteria(self, func):
        """
        Allows custom overlap criteria.
        """
        self.overlap_criteria = func