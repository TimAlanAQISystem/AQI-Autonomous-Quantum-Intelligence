Alan (Agent X) — Full Activation and Recovery

Files created/changed by the activation:
- `run_agent_service_full.py` — runner that starts Alan with full audio, health endpoint, and control API.
- `control_api.py` — FastAPI control API with websocket for interactive conversation (port 8777 by default).
- `create_agent_task.ps1` — PowerShell helper to register a scheduled task to auto-run the full agent at logon.

Quick start (manual):
1. Open a PowerShell prompt (recommended: run as your user, not as Admin unless creating a system-level task).
2. Start Alan now (detached):

```powershell
Start-Process -FilePath "C:\Users\signa\OneDrive\Desktop\Agent X\.venv\Scripts\python.exe" -ArgumentList "C:\Users\signa\OneDrive\Desktop\Agent X\run_agent_service_full.py" -WorkingDirectory "C:\Users\signa\OneDrive\Desktop\Agent X" -WindowStyle Hidden
```

3. Verify health:

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8765/health -UseBasicParsing | Select-Object -Expand Content
# Control API (local): http://127.0.0.1:8777/status
```

4. Create automatic startup (optional): run `create_agent_task.ps1` in PowerShell to register a scheduled task that runs at user logon.

Recovery & re-activation:
- If the service is not running, re-start with the Start-Process command above.
- Check `C:\Users\signa\OneDrive\Desktop\Agent X\inventory\activation_log.txt` for recent events and errors.
- To force a clean restart, reboot or stop any running `python.exe` processes associated with this workspace and then run the Start-Process command.
- To remove scheduled task (if created):

```powershell
schtasks /Delete /TN "AgentX Full Service" /F
```

Notes & safety:
- The control API runs on port 8777 and currently binds to 0.0.0.0 — if you only want local access, change the host to 127.0.0.1 in `run_agent_service_full.py`.
- The audio manager will open the microphone and use VAD; ensure you have the correct default input device selected in Windows Sound settings.
- If you want a more robust Windows Service or supervisor, consider using NSSM or registering a Windows Service wrapper; the scheduled task provides a simple restart on user logon and is easy to remove.

Contact:
- Activation logs: `inventory/activation_log.txt`
- Agent memory: `data/agent_x_memory.json`
