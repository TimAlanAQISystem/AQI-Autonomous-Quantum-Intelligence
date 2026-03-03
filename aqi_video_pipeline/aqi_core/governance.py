class Governance:
    def __init__(self):
        self.publishing_allowed = False

    def require_steward_approval(self):
        if not self.publishing_allowed:
            raise PermissionError("Publishing not authorized by steward.")

    def authorize_publishing(self):
        self.publishing_allowed = True