# Alan High Availability & Zero-Downtime Upgrade Playbook
**Date:** November 29, 2025
**Purpose:** Keep Alan online (fully functional for business hours) while implementing model upgrades and capacity scaling—minimize downtime and risk from hardware failures or planned changes.

---

## Executive Summary
This playbook provides a practical, step-by-step method to keep `LocalLLMCore` operational during business hours and accommodate growth for a "beyond superintelligent" LocalLLM. It stresses redundancy, staged upgrades, traffic routing, fallback models, heartbeat-driven monitoring, canarying, and automation for safe rollouts. The goals are: zero-downtime model upgrades, fast and safe rollback, graceful degradation, and keeping critical capabilities functional when hardware (Raptor) is unplugged.

Key Constraints:
- Business hours uptime must be >= 99.95%.
- Alan must be able to continue critical tasks (lead triage, call initiation, identity checks) during upgrades.
- Upgrades must be reversable and auditable.

---

## High-Level Architecture (Recommended)
- Multi-host cluster with model router (stateless) that serves requests to multiple model runners (blue and green).
- Model runners provide REST/GRPC endpoints and expose health endpoints.
- A fast, low-capacity fallback model (quantized / distilled) runs locally as a last resort when full model nodes are not available.
- Teleport Heartbeat service monitors model nodes and triggers alarms or failover.
- Prometheus & Grafana observe key metrics; PagerDuty or OpsGenie handles escalation.

Diagram (logical):
```
Client (Alan) -> Model Router -> [Blue Model Runner (vX), Green Model Runner (vY), Fallback Runner (quantized)]
                      ^                 ^                ^
                      |                 |                |
                   Healthchecks      Canary            Local Fallback
```

---

## Core Concepts & Why They Work
- Blue/Green Deployments: run two model versions in parallel, switch traffic atomically to the new version only when it proves stable.
- Canarying: route a small percentage of traffic to the new model; compare outputs and monitor metrics.
- Hot-swap routing: maintain a router that can switch endpoints without network reconfiguration.
- Fallback model: small quantized model that can perform essential tasks under reduced capability, guaranteeing Alan's baseline operations.
- Heartbeat: both model runners and Teleport must send signed heartbeat messages to the control node to assert presence; missing heartbeats trigger immediate traffic switching to healthy nodes.

---

## Step-by-step Implementation: Minimum Viable HA (Quick Win - 1–2 Weeks)
1) Add a Model Router (stateless, small service)
   - Purpose: route requests to versions and manage weights.
   - Options: Envoy with header-based routing, Nginx with upstream weights, or a custom ASGI router.

2) Deploy a Local Fallback (distilled quantized model)
   - Purpose: ensure Alan can handle core tasks (lead triage, phone/email basic verification, outbound call triggers) at low capacity.
   - Steps:
     - Build a quantized 4/8-bit model from your main pipeline.
     - Serve on low-latency runner with single-GPU or CPU.

3) Add healthcheck endpoints to all model runners
   - GET /health -> {status: 'ok', error_count: 0, active_model: 'vX'}
   - POST /probe -> run a small inference to ensure response time and correctness.

4) Add Heartbeat & Telemetry
   - Model runners push signed heartbeat to Teleport every 5s with timestamp & version.
   - Teleport records heartbeats and detects outages or degrade.

5) Canary and Metrics
   - Configure the model router to route 1–5% traffic to the new model.
   - Monitor: latency, correctness, drift, confidence score, error rate, CPU/GPU metrics.
   - Validate via: domain task checks and a set of validation queries.

6) Rolling cutover (Blue/Green)
   - If canary metrics are healthy for 24–72 hours, gradually increase traffic weight to new model (10% -> 33% -> 100%).
   - Ensure heartbeats remain stable and the router can reverse the weight in < 1 minute.

7) Scheduled maintenance windows
   - For heavy upgrades requiring full rebuilds or parameter changes, schedule outside business hours.

---

## Step-by-step Implementation: Full HA & Scaling (2–8 weeks)
1) Multi-host model runners with NVLink & shared storage (TrueNAS)
2) Use model sharding (ZeRO or FSDP) to scale models across GPUs
3) Implement MoE / ensemble routing through router
4) Observability: Add Prometheus metrics for all runners; instrument model router for per-version metrics
5) Add WAF & RBAC to router control and restricted access for model serve endpoints

---

## Fallback & Graceful Degradation Behavior
- **If primary runner fails**: Router switches to another healthy runner (green or fallback). All in-progress sessions are restarted with minimal state loss.
- **If fallback active**: Alan should operate in 'Essential mode'—prioritize critical tasks (lead triage, calls, risk checks). Non-critical operations (training, heavy retraining) must be disabled.
- **If Teleport heartbeat lost**: Teleport mode shifts to offline redundancy: auto-sync local logs & restrict outbound actions requiring network.

---

## Runbook: urgent ops for an unplugged Raptor / Full Node Down
1) Telemetry alerts trigger automated router weight shift away from the failed node.
2) PagerDuty paging to operations on-call.
3) If all main runners are unavailable, route to fallback model and set Alan to Essential Mode.
4) If the fallback model is overloaded, rate-limit incoming requests and prioritize critical operator-initiated calls.
5) Restore process:
   - On a known/replaceable hardware failure, bring replacement node online, load model, verify healthchecks, and rejoin routing pool.
   - Recover last writer DB checkpoint if necessary.

---

## Implementation Examples & Scripts (Minimal)
1) Model Runner healthcheck (Flask example)
```python
from flask import Flask, jsonify
app = Flask('model_runner')

@app.route('/health')
def health():
    return jsonify({ 'status': 'ok', 'active_model': 'v1' })

@app.route('/probe', methods=['POST'])
def probe():
    # tiny inference to ensure path is good
    res = 'pong'
    return jsonify({ 'result': res, 'lat_ms': 12 })

if __name__ == '__main__':
    app.run(port=8000)
```

2) Systemd service (Linux) for model runner
```
[Unit]
Description=Model Runner v1
After=network.target

[Service]
User=alan
Group=alan
ExecStart=/opt/alan/models/run_model_runner.sh --model-path=/srv/models/v1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

3) Simple traffic router config (Envoy example, minimal)
```
static_resources:
  listeners:
    - name: listener_http
      address:
        socket_address: { address: 0.0.0.0, port_value: 8080 }
      filter_chains:
        - filters:
            - name: envoy.http_connection_manager
              config: ...

  clusters:
    - name: blue_cluster
      connect_timeout: 1s
      lb_policy: ROUND_ROBIN
      hosts: [{ socket_address: { address: 10.1.1.10, port_value: 8000 }}]
    - name: green_cluster
      hosts: [{ socket_address: { address: 10.1.1.11, port_value: 8000 }}]
    - name: fallback_cluster
      hosts: [{ socket_address: { address: 127.0.0.1, port_value: 8050 }}]

routes:
  - match: {}
    route:
      cluster: blue_cluster
      retry_policy: {num_retries: 2}
      weighted_clusters:
        clusters: [{ name: blue_cluster, weight: 90 }, { name: green_cluster, weight: 10 }]
```

4) Prometheus alert (Heartbeats)
```
- alert: MissingModelHeartbeat
  expr: absent(teleport_model_heartbeat) > 0
  for: 30s
  labels:
    severity: critical
  annotations:
    description: Model runner heartbeat missing for more than 30s
```

---

## Step-by-step Rollout & Rollback Checklist (Operator Guide)
1. Stage the new model on a green node (not receiving production traffic).
2. Confirm health endpoints and probe tests are green (latency under target window and accuracy within thresholds).
3. Start canary traffic (1–5%). Use synthetic tests & monitor.
4. Monitor for at least 24 hours or until stability is proven (no regression in metrics). If an issue arises, revert weight in < 2 minutes.
5. Incrementally increase weight (10% → 33% → 100%) and continue monitoring.

Rollback:
- Immediately shift traffic back to blue nodes and remove the new model from the router.
- Mark the failed model run as 'failed' and capture logs and differences for RCA.

---

## Business Hour Mode — Keep Alan Working
1. Define a 'business hours' flag in config.
2. During business hours:
  - No heavy offline training jobs
  - No model weight updates or reindexing of vector DBs that lock resources
  - Only allow canaries to 1-2% traffic
  - Rely on fallback model for long-running maintenance events
3. Use scheduled maintenance windows for heavy jobs (nighttime / weekend) with automatic restart and validation.

---

## Additional Considerations
- **UPS & Hardware Redundancy**: Single hosts should not be single points of failure — distribute across racks or at least two hosts with GPU failover.
- **Teleport Protocol Integration**: Teleport must be part of the heartbeat chain; heartbeats should be signed and time-stamped.
- **RBAC & Audit**: Only authorized personnel can flip router weights or trigger full upgrades. All changes must be logged.

---

## Quick Action Items (Immediate Implementation)
1. Build and deploy a quantized fallback model and enable as an extra cluster (fastest win).
2. Add health endpoints to current model runners if not present.
3. Deploy a small model router (Envoy example) and configure initial routing (blue=live; green=idle).
4. Implement simple heartbeat metric push from model runners to Teleport/Prometheus.
5. Set business hours configuration to restrict heavy jobs.

---

## Final Notes
This playbook is meant to be immediately actionable and prioritized for reliability. It preserves Alan’s key features while enabling safe upgrades and scalability. When you’re ready, I can produce: the actual Envoy router configs (complete), quantization & model build scripts, and a ready-to-run operator script that executes the staging → canary → blue/green cutover process.

*** End of Playbook ***
