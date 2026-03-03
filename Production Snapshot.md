# Production Snapshot — Agent X

Date: 2025-10-27T12:30:00-07:00

This document is the canonical first "Production Snapshot" for Agent X (Alan). It records the full runtime and repository state at the time Agent X is declared healthy and ready for live outbound calls.

Summary status
- Health endpoint (http://127.0.0.1:8765/health): OK
- Control endpoint (http://127.0.0.1:8777/status): OK
- TTS (pyttsx3): OK
- Twilio library: Installed (twilio==9.8.4)
- Twilio environment variables: NOT SET (set before live call)
- Recent audio queue warnings: sampled tail shows 0 new warnings
- V: drive free space: 0.0 GB — CRITICAL: free space required for snapshots/log rotation

Files changed/added by this snapshot process
- `src/call_harness.py` — safe dry/live call helper
- `tools/call_harness_test.py` — dry-run TTS test
- `control_api.py` — added `/twilio/preflight` and `/call` endpoints (guarded live calls)
- `tools/agent_monitor.py` — health probe + log rotation + auto-restart helper
- `tools/morning_preflight.py` — automated readiness check tool
- `tools/create_snapshot.py` — snapshot generator (default target changed to C:\AgentX-Snapshots)
- `tools/create_snapshot_quick.py` — quick snapshot helper
- `tools/run_bluetooth_manager.py`, `src/bluetooth_manager.py` — defensive bluetooth manager & runner

Snapshot artifacts
- Quick snapshot (earlier): `C:\VHDs\agentx-quick-snap-20251027-1216.zip` (created earlier in session)
- Requirements snapshot: `tools/requirements-snapshot.txt` (packages installed in the venv at time of snapshot)
- Full snapshot target: `C:\AgentX-Snapshots\agentx-snap-<timestamp>.zip` (created when storage available)

Preflight summary (raw)
```
{
  "health_ok": true,
  "control_ok": true,
  "twilio": { "twilio_lib": true, "twilio_env": false },
  "tts_ok": true,
  "recent_audio_warnings": { "found": true, "count": 0 },
  "v_drive": { "exists": true, "free_gb": 0.0 }
}
```

How to restore / use this snapshot
1. Ensure the venv is active: `& ".venv\Scripts\python.exe" run_agent_service_full.py` to start runner.
2. Start monitor: `& ".venv\Scripts\python.exe" tools\agent_monitor.py` (or register it as a scheduled task/service for auto-start).
3. If making a live call, set the following environment variables (or POST them to `/twilio/preflight`):
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN
   - TWILIO_PHONE_NUMBER
4. Use `/twilio/preflight` endpoint to validate credentials, then call `/call` with `live=true` and the `to` E.164 number.

Critical follow-ups (action items)
1. Free or extend `V:` drive space (or change snapshot storage) — otherwise daily snapshot and log rotation will fail. I recommend freeing 10+ GB on V: or using C: (`C:\AgentX-Snapshots`).
2. Create a Scheduled Task to run `tools/agent_monitor.py` at system startup (highest privileges). I can generate and run the PowerShell script if you allow elevation.
3. Provide Twilio creds tomorrow morning (or set env vars) and supply target number — I will run `/twilio/preflight` then perform the live call and record call SID and logs.

Notes
- This snapshot file is the authoritative record of system state. Future snapshots SHOULD be created in the same format and stored with incrementing timestamps.
- I will, on each successful preflight, create a new snapshot file `Production Snapshot - YYYYMMDD-HHMM.md` and archive the workspace snapshot zip.

-- End of Production Snapshot (first) --

# Production Snapshot — Agent X (Restoration)

Date: 2025-11-21T09:18:00-07:00

This snapshot marks the successful restoration of Agent X (Alan) after "The Great Buffering" event. Identity has been corrected (Alan Jones), and the full service stack is operational.

Summary status
- Health endpoint (http://127.0.0.1:8765/health): OK
- Control endpoint (http://127.0.0.1:8777/status): OK
- Service Process: Running (PID verified)
- Identity: Confirmed "Alan Jones"
- Snapshot Location: `snapshots/agentx-snap-20251121-0918.zip`

Files changed/added by this restoration process
- `agent_alan_business_ai.py` — Identity correction & context injection
- `agent_alan_config.json` — Configuration updates
- `alan_deep_diagnostic.py` — Diagnostic tool created
- `tools/create_snapshot.py` — Updated to fix syntax warning and use local `snapshots/` directory

Snapshot artifacts
- Full snapshot: `snapshots/agentx-snap-20251121-0918.zip`

-- End of Production Snapshot (Restoration) --
