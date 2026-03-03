# VIP LAUNCH MODE — FINAL CANONICAL SPECIFICATION
### AQI Agent X / Alan — High-Stakes Governance Layer
### February 16, 2026

---

## ARCHITECTURE OVERVIEW

VIP Launch Mode is a hardened governance layer that sits on top of the Autonomous Repair & Diagnostics Engine (ARDE). It is designed for Monday-grade traffic — when failure is unacceptable and the system must behave like a surgeon, not a gymnast.

```
                  ┌──────────────────────────────────┐
                  │      VIP GOVERNANCE LAYER         │
                  │  • Tightened ARDE thresholds       │
                  │  • Traffic halt on CRITICAL        │
                  │  • Hardened readiness gate          │
                  │  • Deep probe integrity checks     │
                  └──────────────┬───────────────────┘
                                 │
                  ┌──────────────▼───────────────────┐
                  │              ARDE                  │
                  │  7 subsystems • 20s cycle (VIP)    │
                  │  2 max attempts • 45s cooldown     │
                  └──────────────┬───────────────────┘
                                 │
         ┌───────────┬───────────┼───────────┬───────────┐
         │           │           │           │           │
      Alan     Agent X       TTS      Tunnel       Env
      Brain    Support    Pipeline    Sync       Vars
```

---

## A. ACTIVATION

### Enable VIP Mode (Runtime)
```
POST /vip/activate
```
Enables hardened governance and switches ARDE + readiness into VIP mode.

### Disable VIP Mode (Runtime)
```
POST /vip/deactivate
```
Returns system to normal governance.

### Enable via Environment (Before Server Start)
```
VIP_LAUNCH_MODE=1
```
Set before server start — ARDE initializes in VIP mode automatically.

---

## B. BEHAVIOR CHANGES IN VIP MODE

### 1. ARDE Parameter Tightening

| Parameter | Normal Mode | VIP Mode | Rationale |
|-----------|-------------|----------|-----------|
| Check interval | 60s | **20s** | 3× monitoring density |
| Repair cooldown | 120s | **45s** | Faster but controlled repair cadence |
| Max repair attempts | 3 | **2** | Faster escalation to CRITICAL |
| Greeting cache minimum | 3 | **5** | Stricter cache requirement |
| Stability window | — | **300s (5 min)** | No repairs allowed in window for readiness |

### 2. Traffic Halt Logic

If any subsystem reaches **CRITICAL** while VIP mode is active:

- ARDE sets a global flag: `traffic_halted = true`
- `/health` and `/readiness/vip` both return:
  ```json
  { "traffic_halted": true, "traffic_halt_reason": "CRITICAL subsystem(s): tts" }
  ```
- Traffic remains halted until you explicitly clear it:
  ```
  POST /vip/clear-halt
  ```

**Auto-Recovery:** If all subsystems return to `ok`, ARDE auto-clears the halt flag. This prevents permanent halt after transient failures.

**Purpose:** This prevents the system from limping through VIP traffic with a degraded brain or muted voice.

### 3. Hardened VIP Readiness Gate

`GET /readiness/vip` adds **three additional checks** beyond normal readiness:

#### A. No ARDE Repairs in Last 5 Minutes
If ARDE has repaired anything recently → **BLOCKED**. The system must be stable for a full 5-minute window before VIP traffic is greenlit.

#### B. No Subsystem in WARN or DEGRADED
VIP mode requires a **perfect** state. Any subsystem not reporting `ok` → **BLOCKED**.

#### C. Deep Probe Integrity for Both Brains

**Alan:**
- `system_prompt` present
- `build_llm_prompt` present
- Config + model loaded

**Agent X:**
- PVE (`_apply_prompt_velocity`) present
- IQ cores loaded
- Rapport layer loaded
- `priority_dispatch` present

If any of these fail → **BLOCKED**

---

## C. VIP ENDPOINT SCHEMAS

### 1. `POST /vip/activate`

**Request:** `{}`

**Response:**
```json
{
  "status": "activated",
  "activated_at": "2026-02-16T08:00:00.000000",
  "vip_mode": true,
  "traffic_halted": false,
  "message": "VIP Launch Mode activated. ARDE thresholds tightened."
}
```

If already active:
```json
{
  "status": "already_active",
  "activated_at": "2026-02-16T08:00:00.000000"
}
```

---

### 2. `POST /vip/deactivate`

**Request:** `{}`

**Response:**
```json
{
  "status": "deactivated",
  "vip_mode": false,
  "traffic_halted": false,
  "message": "VIP Launch Mode deactivated. Governance returned to normal."
}
```

---

### 3. `GET /vip/status`

**Response:**
```json
{
  "vip_mode": true,
  "activated_at": "2026-02-16T08:00:00.000000",
  "traffic_halted": false,
  "traffic_halt_reason": "",
  "effective_check_interval": 20,
  "effective_repair_cooldown": 45,
  "effective_max_attempts": 2,
  "readiness_requirements": {
    "no_recent_repairs_minutes": 5,
    "no_warn_or_degraded": true,
    "deep_probe_required": true,
    "greeting_cache_minimum": 5
  }
}
```

---

### 4. `POST /vip/clear-halt`

**Request:** `{}`

**Response:**
```json
{
  "status": "cleared",
  "vip_mode": true,
  "traffic_halted": false,
  "message": "Traffic halt cleared. System may resume handling calls."
}
```

---

### 5. `GET /readiness/vip`

**Response (READY):**
```json
{
  "posture": "READY",
  "allowed": true,
  "vip_mode": true,
  "traffic_halted": false,
  "passed": "9/9",
  "checks": [
    { "name": "Coupled Boot", "pass": true },
    { "name": "ARDE Running", "pass": true },
    { "name": "Env Vars", "pass": true },
    { "name": "TTS + Greeting Cache ≥ 5", "pass": true },
    { "name": "Real Call Dry Run", "pass": true },
    { "name": "Log Cleanliness", "pass": true },
    { "name": "No Recent Repairs (5m)", "pass": true },
    { "name": "No WARN/DEGRADED", "pass": true },
    { "name": "Deep Probe Integrity", "pass": true }
  ],
  "subsystems": {
    "alan": "ONLINE",
    "agent_x": "ONLINE",
    "coupled": true
  },
  "deep_probe": {
    "alan_integrity": true,
    "agent_x_integrity": true
  },
  "greeting_cache_count": 5,
  "recent_repairs": 0
}
```

**Response (BLOCKED):**
```json
{
  "posture": "BLOCKED",
  "allowed": false,
  "vip_mode": true,
  "traffic_halted": false,
  "passed": "7/9",
  "checks": [
    { "name": "No Recent Repairs (5m)", "pass": false, "reason": "Repair detected 2m ago" },
    { "name": "Deep Probe Integrity", "pass": false, "reason": "Alan system_prompt missing" }
  ]
}
```

**Response (HALTED):**
```json
{
  "posture": "HALTED",
  "allowed": false,
  "vip_mode": true,
  "traffic_halted": true,
  "traffic_halt_reason": "CRITICAL subsystem(s): tts",
  "message": "Traffic halted due to CRITICAL. Clear with POST /vip/clear-halt"
}
```

---

## D. STRESS-TEST SCRIPT — `vip_stress_test.py`

### Purpose
Official 7-phase stress harness for validating VIP readiness before Monday traffic.

### Execution

Run all phases:
```
python vip_stress_test.py
```

Run specific phases:
```
python vip_stress_test.py --phase 1,2,7
```

Custom server URL:
```
python vip_stress_test.py --base-url http://192.168.1.100:8777
```

### Output
- Terminal: colored pass/fail per check, phase summary, overall verdict
- Report saved to: `logs/vip_stress_test_report.json`

### The 7 Phases

#### Phase 1: Cold Start Integrity
Validates the system boots cleanly and all components wire correctly.
- Health endpoint returns 200
- Alan ONLINE, Agent X ONLINE, coupled boot = true
- ARDE running with ≥ 3 cycles
- All 7 subsystems reporting `ok`
- Deep probe verdict = `ALL_SYSTEMS_GO`
- Greeting cache ≥ 5 entries
- Tunnel URL file exists and valid
- `/readiness/vip` = READY

#### Phase 2: Multi-Call Load (10 Concurrent Requests)
Simulates Monday's real traffic pattern with concurrent HTTP load.
- 10 simultaneous requests to 5 endpoints (health, readiness, VIP readiness, ARDE, deep probe)
- Measures avg/P95/max latency
- Avg < 1000ms, P95 < 2000ms, max < 3000ms
- ARDE stays `ALL_SYSTEMS_GO` after load

#### Phase 3: Latency Spike Resilience
Tests server stability under rapid sequential pressure.
- 20 rapid sequential requests with tight timing
- Average response < 500ms
- Deep probe under pressure returns healthy verdict
- No CRITICAL events generated by load

#### Phase 4: Subsystem Failure Injection
Tests ARDE's detection and deep probe integrity.
- Forced diagnostic baseline
- ARDE repair history accessible with cycle count > 0
- Alan deep probe: `has_system_prompt`, `has_build_llm_prompt`
- Agent X deep probe: `has_process_turn`, `has_pve`, `has_priority_dispatch`, `iq_cores_loaded`, `rapport_loaded`
- Relay deep probe: `has_master_closer`, `has_crg`, `has_evolution`, `has_coordinator`
- Post-repair status = `ALL_SYSTEMS_GO`

#### Phase 5: Greeting Cache Verification
Validates greeting cache meets VIP requirements.
- Cache populated (count > 0)
- Cache ≥ 3 (normal minimum)
- Cache ≥ 5 (VIP minimum)
- ARDE `greeting_cache` status = `ok`
- TTS subsystem = `ok` (needed for rebuilds)

#### Phase 6: Environment & Credential Verification
Confirms all required env vars and API keys are present.
- `TWILIO_SID` present
- `TWILIO_TOKEN` present
- `PHONE` present
- `OPENAI_API_KEY` present
- `GROQ_API_KEY` present
- ARDE Twilio subsystem = `ok`
- ARDE OpenAI subsystem = `ok`
- VIP readiness not HALTED by env issues

#### Phase 7: Full System Recovery & Final Readiness
Comprehensive final validation of the entire stack.
- Alan ONLINE, Agent X ONLINE, coupled boot intact
- Traffic NOT halted
- ARDE overall = `ALL_SYSTEMS_GO`
- All 7 subsystems `ok`
- No recent repair failures
- Deep probe verdict = `ALL_SYSTEMS_GO`
- Greeting cache ≥ 5
- VIP Readiness Gate = READY

### Report Format
```json
{
  "timestamp": "2026-02-16T07:30:00.000000",
  "base_url": "http://127.0.0.1:8777",
  "duration_s": 42.7,
  "all_passed": true,
  "phases": [
    {
      "phase": 1,
      "name": "Cold Start Integrity",
      "passed": true,
      "checks": [...],
      "duration_s": 3.2
    }
  ]
}
```

---

## E. VIP LAUNCH RUNBOOK (ONE PAGE)

### 1. Activate VIP Mode
```
POST /vip/activate
```
Confirm: `/vip/status` → `vip_mode=true`, interval=20s, max_attempts=2

### 2. Validate Cold Start
```
GET /readiness/vip
```
Must return `posture=READY`, `allowed=true`, all 9 checks passing.

### 3. Run Stress Test (Recommended)
```
python vip_stress_test.py
```
Confirm: All 7 phases green. Report saved to `logs/vip_stress_test_report.json`.

### 4. Begin VIP Traffic
System is allowed to take calls **only** if:
- `/readiness/vip` = READY
- `traffic_halted = false`
- No WARN/DEGRADED subsystems
- No recent repairs in 5 minutes
- Deep probe passes for both brains

### 5. If Anything Fails During VIP
- System halts traffic automatically on CRITICAL
- `/readiness/vip` returns HALTED
- Fix the subsystem (ARDE may auto-repair within 20s)
- If auto-recovery succeeds, traffic halt clears automatically
- If manual intervention needed:
  ```
  POST /vip/clear-halt
  ```

### 6. Emergency Recovery
```
Kill:    Get-Process python | Stop-Process -Force
Wait:    Start-Sleep 5
Cache:   Remove-Item -Recurse -Force __pycache__
Start:   .venv\Scripts\python.exe -m hypercorn control_api_fixed:app --bind 0.0.0.0:8777
Tunnel:  cloudflared tunnel --url http://127.0.0.1:8777
```
Save new tunnel URL → `active_tunnel_url.txt` + `active_tunnel_url_fixed.txt`

### 7. Deactivate VIP Mode (End of Day)
```
POST /vip/deactivate
```

---

## F. VIP DASHBOARD OVERLAY

The dashboard at `http://127.0.0.1:8777/dashboard` provides real-time VIP telemetry.

### Top Bar (Red/Green)
| Indicator | Source |
|-----------|--------|
| VIP Mode | ON / OFF |
| Traffic | ACTIVE / HALTED |
| ARDE | Cycle count, last repair |
| Greeting Cache | Count (must be ≥ 5) |
| Tunnel | URL + last sync |
| Active Calls | Number |

### Subsystem Health Matrix

| Subsystem | Status | Attempts | Last Repair | Notes |
|-----------|--------|----------|-------------|-------|
| Alan | ONLINE | 0 | — | Deep probe OK |
| Agent X | ONLINE | 0 | — | PVE + IQ cores OK |
| TTS | ONLINE | 0 | — | Voice stable |
| Greeting Cache | OK | 0 | — | ≥ 5 entries |
| Tunnel | OK | 0 | — | Twilio synced |
| Twilio | OK | — | — | Env vars valid |
| OpenAI | OK | — | — | Key valid |

### ARDE Event Stream (Last 20)
Rolling log of diagnostic and repair events.

### Deep Probe Snapshot
- **Alan:** system_prompt, build_llm_prompt, model, config
- **Agent X:** PVE, rapport, IQ cores, priority_dispatch
- **Relay Server:** engines, greeting cache
- **TTS:** model + voice
- **Tunnel:** URL + sync time

### Call Activity
Active and recent call panel with SID, duration, and status.

---

## G. IMPLEMENTATION FILES

| File | Size | Purpose |
|------|------|---------|
| `autonomous_repair_engine.py` | 34,305 bytes (738 lines) | ARDE with VIP mode |
| `control_api_fixed.py` | 80,962 bytes (~1850 lines) | FastAPI server with VIP endpoints |
| `vip_stress_test.py` | 30,557 bytes (644 lines) | 7-phase stress harness |
| `vip_dashboard.html` | 20,663 bytes | Real-time telemetry dashboard |
| `RUNBOOK_MONDAY_VIP.md` | 4,946 bytes | One-page operational guide |

### VIP Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/vip/activate` | POST | Enable VIP governance |
| `/vip/deactivate` | POST | Return to normal governance |
| `/vip/status` | GET | VIP mode state + effective thresholds |
| `/vip/clear-halt` | POST | Clear traffic halt after CRITICAL |
| `/readiness/vip` | GET | 9-check VIP readiness gate |
| `/dashboard` | GET | Real-time telemetry dashboard |
| `/diagnostics/arde` | GET | ARDE engine state |
| `/diagnostics/deep` | GET | Deep probe of both brains |
| `/repair/force` | POST | Trigger immediate repair cycle |

---

## H. CONSTITUTIONAL NOTES

1. **VIP mode is temporary.** It is designed for Monday — when failure is unacceptable. Deactivate at end of day.
2. **Traffic halt is a safety valve.** It prevents limping through VIP traffic with a degraded subsystem. Auto-clears when all subsystems recover.
3. **The readiness gate is the single source of truth.** If `/readiness/vip` says BLOCKED, the system is not ready for VIP traffic. Full stop.
4. **ARDE does not guess.** It diagnoses, repairs, escalates, or halts. It never silently degrades.
5. **The stress test is non-destructive.** It tests the server's HTTP layer and validates ARDE state. It does not inject real failures or remove real env vars.

---

*Specification finalized: February 15, 2026*
*Status: ALL PRODUCTION CODE IMPLEMENTED AND COMPILE-VERIFIED*
*This document is the canonical reference for VIP Launch Mode.*
