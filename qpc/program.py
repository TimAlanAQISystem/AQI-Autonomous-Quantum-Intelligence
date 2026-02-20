"""
QPC Program - Sequenced, governed cognitive operations
"""
from typing import List, Dict, Any, Tuple
from .state import QPCState
# from .coherence import CoherenceWindow
# from .identity import IdentityHamiltonian

class QPCProgram:
    def __init__(self, name: str, steps: List[Any] = None, coherence_window=None, identity_hamiltonian=None):
        self.name = name
        self.steps = []
        if steps:
            for s in steps:
                if isinstance(s, tuple) and len(s) == 2:
                    self.add_step(s[0], s[1])
    
    def add_step(self, op_name: str, task: Any, constraints: Dict[str, Any] = None):
        self.steps.append({
            "op": op_name,
            "task": task,
            "constraints": constraints or {}
        })

    def run(
        self,
        initial_state: QPCState,
        coherence_window: Any, # CoherenceWindow
        identity_hamiltonian: Any  # IdentityHamiltonian
    ) -> Tuple[QPCState, List[Dict[str, Any]]]:
        """
        Execute the program steps under governance.
        Returns (Final State, Execution Log)
        """
        current_state = initial_state
        execution_log = []
        
        # v0 Implementation: Simple sequential execution
        for i, step in enumerate(self.steps):
            # 1. Check Coherence
            if not coherence_window.check_budget():
                 raise RuntimeError("Coherence Window Budget Exceeded")
            
            # 2. Check Identity (Hamiltonian)
            if not identity_hamiltonian.check(current_state): # Fixed: .check(QPCState)
               raise RuntimeError("Identity Hamiltonian Violation")

            # 3. Execute Step
            try:
                # If the step is an explicit callable, execute it
                if callable(step['task']):
                     output = step['task'](current_state)
                # If it's just data/dict (legacy prompt dict), we pass it as output
                else:
                     output = step['task']
            except Exception as e:
                # [QPC] Failure should be captured as state noise, but for now we raise
                raise e 
            
            # 4. Log
            execution_log.append({
                "step": i,
                "op": step['op'],
                "timestamp": getattr(current_state, 'timestamp', None),
            })
            
            # 5. Evolve State
            # Capture the output into a new state
            if isinstance(output, QPCState):
                current_state = output
            else:
                # If output is raw data, wrap it
                new_data = current_state.data.copy() if hasattr(current_state, 'data') else {}
                new_data['output'] = output
                current_state = QPCState.from_context(new_data, parent_state_id=current_state.state_id)
            
        return current_state, execution_log
