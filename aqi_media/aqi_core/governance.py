# aqi_core/governance.py

class Governance:
    def __init__(self):
        self._publishing_authorized = False

    def assert_can_publish(self):
        if not self._publishing_authorized:
            raise PermissionError("Publishing not authorized by steward.")

    def authorize_publishing(self):
        self._publishing_authorized = True

    def revoke_publishing(self):
        self._publishing_authorized = False