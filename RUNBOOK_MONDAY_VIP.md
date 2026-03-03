# MONDAY VIP LAUNCH RUNBOOK
### One-Page Operational Guide — February 16, 2026
### *Print this. Laminate it. Tape it next to your keyboard.*

---

## PRE-LAUNCH CHECKLIST (Do This First)

```
1. Start server:   .venv\Scripts\python.exe -m hypercorn control_api_fixed:app --bind 0.0.0.0:8777
2. Start tunnel:   cloudflared tunnel --url http://127.0.0.1:8777
3. Save tunnel URL to active_tunnel_url.txt AND active_tunnel_url_fixed.txt
4. Activate VIP:   POST http://127.0.0.1:8777/vip/activate
5. Confirm VIP:    GET  http://127.0.0.1:8777/vip/status  → vip_mode=true, interval=20s
6. Run stress:     python vip_stress_test.py  → All 7 phases green
7. Hit readiness:  GET  http://127.0.0.1:8777/readiness/vip  → posture=READY, 9/9 checks
8. Make one real test call to confirm greeting plays and Alan responds.
9. Create marker:  New-Item -Path ".vip_dry_run_confirmed" -ItemType File
```

---

## IF CALLS FAIL TO CONNECT

1. **Check health:**  
   `GET http://127.0.0.1:8777/health`  
   → Confirm `alan: ONLINE`, `agent_x: ONLINE`, `coupled: true`

2. **Check ARDE:**  
   `GET http://127.0.0.1:8777/diagnostics/arde`  
   → If ARDE is running and repairing, **wait 60 seconds** for one cycle to complete.  
   → If ARDE is NOT running or not repairing, force it:  
   `POST http://127.0.0.1:8777/repair/force`

3. **Check tunnel:**  
   `GET https://<your-tunnel-url>/health`  
   → If this fails, the tunnel is dead. Restart cloudflared and save the new URL.

4. **If still broken — full restart sequence:**
   ```
   a. Kill all Python processes:     Get-Process python | Stop-Process -Force
   b. Wait 5 seconds
   c. Clear cache:                   Remove-Item -Recurse -Force __pycache__
   d. Restart server:                .venv\Scripts\python.exe -m hypercorn control_api_fixed:app --bind 0.0.0.0:8777
   e. Restart tunnel:                cloudflared tunnel --url http://127.0.0.1:8777
   f. Save new tunnel URL to both files
   g. Verify:                        GET /readiness/vip
   ```

---

## IF ALAN FEELS "OFF" OR MISSING IQ

1. **Hit deep diagnostic:**  
   `GET http://127.0.0.1:8777/diagnostics/deep`

2. **Confirm Alan's probe fields:**
   - `has_system_prompt: true`
   - `has_build_llm_prompt: true`
   - `has_config: true`
   - `model` shows expected model name
   - `max_tokens` shows expected value

3. **Confirm Agent X's probe fields:**
   - `has_process_turn: true`
   - `has_pve: true` (Prompt Velocity Engine)
   - `has_priority_dispatch: true`
   - `has_mannerism_advisory: true`
   - `iq_cores_loaded: true`
   - `rapport_loaded: true`

4. **If fields are missing:**  
   → Check ARDE repair history: `GET /diagnostics/arde` — look at `repair_history`  
   → If ARDE hasn't attempted repair, force it: `POST /repair/force`  
   → If ARDE tried and failed (3 attempts), it's NOT a wiring issue — it's config or model-level. Check `agent_alan_config.json` and environment variables.

---

## IF GREETING DOESN'T PLAY

1. Check `GET /diagnostics/arde` → look at `greeting_cache` status
2. If `warning` or `degraded` → check TTS status in same response
3. If TTS is down → check `OPENAI_API_KEY` in environment
4. Force repair: `POST /repair/force`
5. If still broken → restart server (TTS client re-initializes on boot)

---

## IF TUNNEL URL CHANGES MID-SESSION

1. Capture new URL from cloudflared output
2. Save to both files:
   ```
   Set-Content "active_tunnel_url.txt" "https://new-url.trycloudflare.com"
   Set-Content "active_tunnel_url_fixed.txt" "https://new-url.trycloudflare.com"
   ```
3. Server's tunnel monitor will auto-sync to Twilio within 120 seconds
4. To force immediate sync: `POST /repair/force`

---

## VIP READINESS — TRAFFIC GATE

**Before allowing any VIP calls, this must return READY with 9/9 checks:**

```
GET http://127.0.0.1:8777/readiness/vip
```

| # | Check | What It Verifies |
|---|-------|-----------------|
| 1 | Coupled Boot | Alan + Agent X both ONLINE, coupled=true |
| 2 | ARDE Running | Engine active, cycles progressing |
| 3 | Env Vars | Twilio SID/Token/Phone, OpenAI key present |
| 4 | TTS + Greetings | TTS online, greeting cache ≥ 5 entries (VIP mode) |
| 5 | Real Call Dry Run | `.vip_dry_run_confirmed` marker file exists |
| 6 | Log Cleanliness | No CRITICAL in ARDE logs, supervisor queue clean |
| 7 | No Recent Repairs (5m) | ARDE stability — no repairs in last 300 seconds |
| 8 | No WARN/DEGRADED | All 7 subsystems must be `ok` — VIP demands perfect state |
| 9 | Deep Probe Integrity | Alan: system_prompt + build_llm_prompt. Agent X: PVE + IQ cores + rapport |

**If ANY check fails → DO NOT allow VIP traffic.**

---

## IF TRAFFIC GETS HALTED

VIP mode automatically halts traffic when any subsystem reaches CRITICAL.

1. **Check what happened:**
   `GET http://127.0.0.1:8777/vip/status` → `traffic_halt_reason` tells you which subsystem
2. **Wait for ARDE auto-repair:** ARDE runs every 20s in VIP mode. If the issue is transient, it auto-clears.
3. **If auto-repair doesn't fix it:** Fix manually, then clear the halt:
   `POST http://127.0.0.1:8777/vip/clear-halt`
4. **Verify:** `GET /readiness/vip` → must return `posture=READY`

---

## DASHBOARD

Open in browser during live calls:

```
http://127.0.0.1:8777/dashboard
```

One glance = full system truth. Shows:
- System vital signs (Alan, Agent X, ARDE, tunnel, calls)
- Subsystem health matrix (all 7 systems)
- ARDE event stream (last 20 events)
- Deep probe snapshot (brain integrity)
- Active call panel

---

## EMERGENCY CONTACTS

| What | Where |
|------|-------|
| Server | Port 8777, PID in `Get-NetTCPConnection -LocalPort 8777` |
| Tunnel | cloudflared process, URL in `active_tunnel_url.txt` |
| Logs | `logs/arde_repair_log.json` |
| Stress Report | `logs/vip_stress_test_report.json` |
| Config | `agent_alan_config.json` |
| Force Repair | `POST http://127.0.0.1:8777/repair/force` |
| VIP Status | `GET http://127.0.0.1:8777/vip/status` |
| VIP Gate | `GET http://127.0.0.1:8777/readiness/vip` |
| Clear Halt | `POST http://127.0.0.1:8777/vip/clear-halt` |
| Dashboard | `http://127.0.0.1:8777/dashboard` |

---

## END OF DAY — DEACTIVATE VIP MODE

```
POST http://127.0.0.1:8777/vip/deactivate
```
Returns to normal governance: 60s cycle, 120s cooldown, 3 max attempts.

---

*Print this page. Tape it to your monitor. Sleep well.*
