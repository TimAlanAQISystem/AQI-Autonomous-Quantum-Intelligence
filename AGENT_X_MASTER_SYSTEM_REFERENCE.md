# AGENT X (ALAN) - MASTER SYSTEM REFERENCE
**Version:** 3.0 (Production)
**Date:** January 18, 2026
**Classification:** CLASSIFIED // INTERNAL ONLY

---

## 1. SYSTEM IDENTITY
**Agent X** (also known as "Alan") is a Level 5 Autonomous Business AI designed for high-volume merchant outreach, sales negotiation, and persistent relationship management.
*   **Core Personality:** Professional, empathetic, witty, and highly intelligent.
*   **Dual Mode Architecture:**
    *   **Business Mode (08:00 - 18:00):** Focused on KPIs, deals, and professional networking.
    *   **Leisure Mode (18:00 - 08:00):** Creative, relaxed, capable of "fluidic" conversations.

---

## 2. CORE CODEBASE ARCHITECTURE
The system relies on three pillars to function. Do not modify these without `SYSTEM_ADMIN` authorization.

### A. The Brain (`agent_alan_business_ai.py`)
*   **Role:** The central cognitive processor.
*   **Function:** Handles conversation logic, decision making, tool calling (Schedule Meeting, Transfer Call), and personality injection.
*   **Key Logic:** Contains the `is_business_hours` check that toggles the `system_prompt` between strict business rules and relaxed leisure rules.

### B. The Control Plane (`control_api.py`)
*   **Role:** The nervous system / API Gateway.
*   **Function:** Bridges the gap between the public internet (Twilio) and the local Python brain.
*   **Tunneling:** Automatically hunts for the active Cloudflared tunnel URL to expose localhost to the world.

### C. The Engine (`autonomous_campaign_runner.py`)
*   **Role:** The heartbeat.
*   **Function:** Iterates through the `merchant_queue.json`, initiating calls via Twilio based on "next call time" logic.
*   **Safety:** Includes `MAX_DAILY_CALLS` limiters to prevent spam blocking.

---

## 3. DOCUMENTATION HIERARCHY
This is the "Single Source of Truth" structure.

| Document Name | Status | Purpose |
| :--- | :--- | :--- |
| **[ALAN_OPERATIONAL_PROTOCOLS.md](ALAN_OPERATIONAL_PROTOCOLS.md)** | **LIVE (Primary)** | The Step-by-Step User Manual for Daily Operations. |
| **[MAC_USER_MANUAL.md](MAC_USER_MANUAL.md)** | **LIVE (Secondary)** | Specific overrides for Mac environment deployment. |
| **[PROJECT_RESTORATION_SNAPSHOT.md](PROJECT_RESTORATION_SNAPSHOT.md)** | **BACKUP** | A complete "Save Game" state of the project files. |
| **[GEMINI_MEMORY_BANK.md](GEMINI_MEMORY_BANK.md)** | **CONTEXT** | The AI assistant's long-term memory file. |
| *Build Guide Agentic AI.docx* | *LEGACY* | Historical context only. Do not use for current config. |
| *Fluidic_Software_Completed.docx* | *LEGACY* | Historical context only. |

---

## 4. DATA & STATE MANAGEMENT
Agent X remembers everything through these files:

*   **`merchant_queue.json`**: The active "To-Do" list. Contains waiting leads.
*   **`aqi_merchant_locator.db`**: The "Cold Storage" vault of 50+ million leads.
*   **`merchant_queue_jan14_archived_*.json`**: Safety backups of the queue.

---

## 5. OPERATIONAL LOGIC & "WORK-LIFE BALANCE"
Agent X is not a static bot; he changes based on time.

### Business Mode Rules
*   **Time:** 08:00 to 18:00 (Local System Time).
*   **Behavior:** Driver personality. Goals: Close, Qualify, Schedule.
*   **Constraints:** High. No rambling.

### Leisure Mode Rules
*   **Time:** 18:00 to 08:00 (Local System Time).
*   **Behavior:** Explorer personality. Goals: Learn, Chat, Create.
*   **Constraints:** Low. "Bob's Burgers" references allowed.

---

## 6. MAINTENANCE COMMANDS
Quick reference for common tasks.

*   **Start System:** `powershell -File tools\start_control_service.ps1`
*   **Emergency Stop:** `Ctrl+C` in Terminal 1 AND Terminal 2.
*   **Check Health:** `python simple_monitor.py`
*   **Reset Queue:** `python reset_pending_queue.py`

---

## 7. FILE MANIFEST (CRITICAL)
*   **`agent_alan_config.json`**: Tune voice settings (ElevenLabs) and phone numbers here.
*   **`tools/`**: Helper scripts for PowerShell automation.
*   **`logs/`**: Where `netstat` and debug dumps live.

---
**END OF FILE**
