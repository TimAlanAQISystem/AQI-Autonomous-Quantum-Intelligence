"""
QPC Coherence Window - Bounded reasoning scope
"""
import time
import uuid

class CoherenceWindow:
    def __init__(
        self,
        max_depth: int = 10,
        max_duration_ms: int = 5000,
        max_external_calls: int = 3
    ):
        self.window_id = str(uuid.uuid4())
        self.max_depth = max_depth
        self.max_duration_ms = max_duration_ms
        self.max_external_calls = max_external_calls
        
        self.start_time = time.time()
        self.current_depth = 0
        self.current_external_calls = 0

    def check_budget(self) -> bool:
        """Verify we are still within the coherence window"""
        elapsed_ms = (time.time() - self.start_time) * 1000
        
        if elapsed_ms > self.max_duration_ms:
            return False
        if self.current_depth > self.max_depth:
            return False
        if self.current_external_calls > self.max_external_calls:
            return False
            
        return True

    def increment_depth(self):
        self.current_depth += 1

    def increment_call(self):
        self.current_external_calls += 1
