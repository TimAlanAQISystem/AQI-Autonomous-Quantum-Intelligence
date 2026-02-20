"""
QPC Identity Hamiltonian - The governing operator
Constitution + Persona + Steward Intent
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import re

@dataclass
class IdentityHamiltonian:
    constitution_id: str
    persona_profile_id: str
    steward_id: str

    # Persona rules
    forbidden_phrases: List[str]
    forbidden_patterns: List[str]
    required_tone: str
    max_sentence_length: int
    allowed_domains: List[str]
    forbidden_domains: List[str]

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "IdentityHamiltonian":
        return cls(
            constitution_id=config.get("constitution_id", "alan_v2_constitution"),
            persona_profile_id=config.get("persona_profile_id", "alan_business_director"),
            steward_id=config.get("steward_id", "tim"),

            forbidden_phrases=config.get("forbidden_phrases", []),
            forbidden_patterns=config.get("forbidden_patterns", []),
            required_tone=config.get("required_tone", "formal"),
            max_sentence_length=config.get("max_sentence_length", 32),

            allowed_domains=config.get("allowed_domains", []),
            forbidden_domains=config.get("forbidden_domains", []),
        )

    def check_output(self, text: str) -> Dict[str, Any]:
        violations = []

        # 1. Forbidden phrases
        for phrase in self.forbidden_phrases:
            if phrase.lower() in text.lower():
                violations.append({
                    "type": "forbidden_phrase",
                    "phrase": phrase,
                })

        # 2. Forbidden regex patterns
        for pattern in self.forbidden_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append({
                    "type": "forbidden_pattern",
                    "pattern": pattern,
                })

        # 3. Tone enforcement
        if self.required_tone == "formal":
            casual_markers = ["dude", "bro", "lol", "haha", "man,", "buddy"]
            for marker in casual_markers:
                if marker in text.lower():
                    violations.append({
                        "type": "tone_violation",
                        "marker": marker,
                        "required_tone": self.required_tone,
                    })

        # 4. Sentence length enforcement
        sentences = re.split(r"[.!?]", text)
        for s in sentences:
            if len(s.split()) > self.max_sentence_length:
                violations.append({
                    "type": "sentence_length_violation",
                    "sentence": s.strip(),
                    "max_allowed": self.max_sentence_length,
                })

        # 5. Domain enforcement
        domain_text = text.lower()

        for forbidden in self.forbidden_domains:
            if forbidden in domain_text:
                violations.append({
                    "type": "forbidden_domain",
                    "domain": forbidden,
                })

        # Allowed domain check (soft)
        if self.allowed_domains:
            if not any(domain in domain_text for domain in self.allowed_domains):
                violations.append({
                    "type": "off_domain",
                    "allowed_domains": self.allowed_domains,
                })

        return {
            "ok": len(violations) == 0,
            "violations": violations,
        }

    def check(self, state) -> bool:
        """
        Compatibility wrapper for QPCProgram execution.
        Checks the text content within the state.
        """
        text = ""
        # Extract useful text from state data
        if hasattr(state, 'data') and isinstance(state.data, dict):
            # Check prompt (input) and output if available
            parts = []
            if 'prompt' in state.data:
                 parts.append(str(state.data['prompt']))
            if 'output' in state.data:
                 parts.append(str(state.data['output']))
            text = " ".join(parts)
        else:
            text = str(state)

        result = self.check_output(text)
        
        if not result['ok']:
            # Log violations but don't crash unless critical? 
            # For now, we enforce strict compliance as requested.
            print(f"[HAMILTONIAN] VIOLATION: {result['violations']}")
            return False
            
        return True
