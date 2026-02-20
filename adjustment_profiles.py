
CONSERVATIVE_PROFILE = {
    "max_pacing_cps": 0.2,          # calls per second
    "min_interval_sec": 8,
    "new_lead_ratio": 0.4,
    "retry_lead_ratio": 0.6,
    "max_retries_per_lead": 3,
    "vad_sensitivity_delta": 0.0,   # no change
    "opener_delay_ms_delta": 0,     # no change
}

BALANCED_PROFILE = {
    "max_pacing_cps": 0.4,
    "min_interval_sec": 5,
    "new_lead_ratio": 0.6,
    "retry_lead_ratio": 0.4,
    "max_retries_per_lead": 3,
    "vad_sensitivity_delta": 0.05,  # ±5% allowed
    "opener_delay_ms_delta": 100,   # up to +/‑100ms
}

AGGRESSIVE_PROFILE = {
    "max_pacing_cps": 0.8,
    "min_interval_sec": 3,
    "new_lead_ratio": 0.75,
    "retry_lead_ratio": 0.25,
    "max_retries_per_lead": 4,
    "vad_sensitivity_delta": 0.10,  # ±10%
    "opener_delay_ms_delta": 150,   # up to +/‑150ms
}
