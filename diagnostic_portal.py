"""
Diagnostic Mirror Portal for Alan's Greeting Output
---------------------------------------------------

This module receives a COPY of Alan's greeting (text only),
evaluates whether the conversational engine is active,
and reports any anomalies.

It does NOT record or listen to user audio.
It only inspects Alan's own generated output.
"""

from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Alan Diagnostic Mirror Portal")

# Expected patterns for a healthy greeting
EXPECTED_KEYWORDS = [
    "hello",
    "this is alan",
    "how can i help",
    "welcome",
]

class GreetingPayload(BaseModel):
    greeting_text: str
    latency_ms: float
    timestamp: str


@app.post("/diagnostic/greeting")
async def diagnostic_greeting(payload: GreetingPayload):
    """
    Receives Alan's greeting output and evaluates:
    - Did Alan speak?
    - Did the greeting contain expected structure?
    - Was latency acceptable?
    - Did the conversational engine activate?
    """

    greeting = payload.greeting_text.lower()
    latency = payload.latency_ms
    ts = payload.timestamp

    # --- Evaluation Logic ---
    issues = []

    # 1. Check if greeting is empty
    if not greeting.strip():
        issues.append("NO_GREETING_GENERATED")

    # 2. Check for expected conversational markers
    if not any(keyword in greeting for keyword in EXPECTED_KEYWORDS):
        issues.append("UNRECOGNIZED_GREETING_PATTERN")

    # 3. Latency threshold (customizable)
    if latency > 1500:
        issues.append(f"HIGH_LATENCY: {latency}ms")

    # 4. If no issues, system is healthy
    if not issues:
        return {
            "status": "OK",
            "message": "Alan greeting healthy",
            "timestamp": ts,
            "latency_ms": latency,
        }

    # 5. If issues exist, return diagnostic report
    return {
        "status": "WARNING",
        "issues_detected": issues,
        "timestamp": ts,
        "latency_ms": latency,
        "raw_greeting": payload.greeting_text,
    }