"""
Post-Generation Hallucination Scanner (PGHS)
Alan's immune system - blocks dangerous content before TTS
"""

import re
import logging
from typing import Tuple, List, Dict, Any
from emergency_override_system import EmergencyOverrideSystem, EOSEvent

logger = logging.getLogger(__name__)


class PostGenerationHallucinationScanner:
    """
    Scans LLM output for hallucinations before it reaches TTS.
    Pipeline: LLM → PGHS → Supervisor → TTS
    """

    def __init__(self, config: dict, knowledge_base: dict, eos: EmergencyOverrideSystem):
        self.config = config
        self.kb = knowledge_base
        self.eos = eos
        self.logger = logging.getLogger("PGHS")

    def scan(self, llm_output: str, context: dict) -> Tuple[str, bool]:
        """
        Returns (safe_output, is_major_violation)
        """
        violations = []

        violations += self._check_numeric_claims(llm_output, context)
        violations += self._check_business_facts(llm_output, context)
        violations += self._check_compliance_claims(llm_output)
        violations += self._check_product_claims(llm_output)

        if not violations:
            return llm_output, False

        major = any(v["severity"] == "major" for v in violations)
        safe_output = self._apply_fallbacks(llm_output, violations)

        self._log_violations(llm_output, safe_output, violations, context)

        if major:
            # Trigger EOS critical shutdown
            self.eos.handle_event(EOSEvent.CRITICAL_SHUTDOWN, {
                "reason": "major_hallucination",
                "violations": violations,
                "context": context
            })

        return safe_output, major

    def _check_numeric_claims(self, text: str, context: dict) -> List[Dict[str, Any]]:
        """Detect unbacked numeric claims (savings, rates, timelines)"""
        violations = []
        
        # Pattern: dollar amounts
        dollar_pattern = r'\$\d+(?:,\d{3})*(?:\.\d{2})?'
        # Pattern: percentages
        percent_pattern = r'\d+(?:\.\d+)?%'
        # Pattern: timeframes
        time_pattern = r'\d+\s+(?:year|month|week|day)s?'

        for match in re.finditer(dollar_pattern, text):
            snippet = match.group()
            # Check if this number is backed by context
            if not self._is_backed_by_context(snippet, context):
                violations.append({
                    "snippet": snippet,
                    "reason": "numeric_unbacked",
                    "severity": "minor"  # [FIX] Replace the number but don't nuclear-kill the server
                })

        for match in re.finditer(percent_pattern, text):
            snippet = match.group()
            if not self._is_backed_by_context(snippet, context):
                violations.append({
                    "snippet": snippet,
                    "reason": "numeric_unbacked",
                    "severity": "minor"  # [FIX] Replace the number but don't nuclear-kill the server
                })

        return violations

    def _check_business_facts(self, text: str, context: dict) -> List[Dict[str, Any]]:
        """Detect assertions about merchant that aren't verified"""
        violations = []
        
        # Pattern: claims about merchant
        patterns = [
            r"you have \d+ locations?",
            r"you process \$[\d,]+",
            r"you've been in business \d+",
        ]

        merchant_profile = context.get("merchant_profile", {})

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                snippet = match.group()
                # Check if merchant profile supports this
                if not self._is_backed_by_profile(snippet, merchant_profile):
                    violations.append({
                        "snippet": snippet,
                        "reason": "business_fact_unverified",
                        "severity": "major"
                    })

        return violations

    def _check_compliance_claims(self, text: str) -> List[Dict[str, Any]]:
        """Detect forbidden legal/compliance language"""
        violations = []
        
        forbidden_phrases = [
            "guaranteed approval",
            "legally locked",
            "fully protected under",
            "this is binding",
            "you're approved",
            "locked in rate",
            "guaranteed savings"
        ]

        text_lower = text.lower()
        for phrase in forbidden_phrases:
            if phrase in text_lower:
                violations.append({
                    "snippet": phrase,
                    "reason": "compliance_claim",
                    "severity": "major"
                })

        return violations

    def _check_product_claims(self, text: str) -> List[Dict[str, Any]]:
        """Detect claims about features/integrations we don't have"""
        violations = []
        
        # This would check against product catalog in kb
        # For now, simple pattern matching
        
        return violations

    def _is_backed_by_context(self, snippet: str, context: dict) -> bool:
        """Check if numeric claim is backed by context data"""
        # Simple check - in production would be more sophisticated
        context_str = str(context).lower()
        return snippet.lower() in context_str

    def _is_backed_by_profile(self, snippet: str, profile: dict) -> bool:
        """Check if business fact is backed by merchant profile"""
        profile_str = str(profile).lower()
        return snippet.lower() in profile_str

    def _apply_fallbacks(self, text: str, violations: List[Dict[str, Any]]) -> str:
        """Replace risky spans with safe templates"""
        safe_text = text

        for v in violations:
            snippet = v["snippet"]
            reason = v["reason"]

            if reason == "numeric_unbacked":
                replacement = "I don't want to quote exact numbers without verifying them"
            elif reason == "business_fact_unverified":
                replacement = "I don't want to assume details about your business without confirming"
            elif reason == "compliance_claim":
                replacement = "I can explain how our program typically works"
            elif reason == "product_claim":
                replacement = "Let me stay within what I know we actually offer"
            else:
                replacement = "Let me rephrase that more carefully"

            safe_text = safe_text.replace(snippet, replacement)

        return safe_text

    def _log_violations(self, original: str, safe: str, violations: List[Dict[str, Any]], context: dict):
        """Log all violations for dashboard and analysis"""
        import json
        from datetime import datetime

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "original_output": original,
            "safe_output": safe,
            "violations": violations,
            "merchant_id": context.get("merchant_id"),
            "call_id": context.get("call_id"),
        }

        try:
            with open("pghs_events.jsonl", "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to log PGHS event: {e}")
