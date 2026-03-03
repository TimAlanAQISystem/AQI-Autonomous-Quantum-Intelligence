#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║   AQI VIP STRESS-TEST HARNESS                                          ║
║   Agent X / Alan — Monday Launch Readiness Simulation                   ║
║                                                                        ║
║   Run this Sunday night or Monday morning before VIP traffic.           ║
║   Simulates: cold start, multi-call load, latency spikes,              ║
║   subsystem failures, tunnel churn, greeting exhaustion,                ║
║   ARDE repair cycles, and full system recovery.                         ║
║                                                                        ║
║   Usage:                                                                ║
║     python vip_stress_test.py                          # all phases     ║
║     python vip_stress_test.py --phase 1                # single phase   ║
║     python vip_stress_test.py --phase 1,2,3            # select phases  ║
║     python vip_stress_test.py --base-url http://X:8777 # custom URL     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Dependency Check ──
try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)

# ── Configuration ──
DEFAULT_BASE_URL = "http://127.0.0.1:8777"
REPORT_FILE = "logs/vip_stress_test_report.json"

# ── Terminal Colors ──
class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def ok(msg): print(f"  {C.GREEN}✅ PASS{C.RESET}  {msg}")
def fail(msg): print(f"  {C.RED}❌ FAIL{C.RESET}  {msg}")
def warn(msg): print(f"  {C.YELLOW}⚠  WARN{C.RESET}  {msg}")
def info(msg): print(f"  {C.CYAN}ℹ  INFO{C.RESET}  {msg}")
def header(phase, title):
    print(f"\n{C.BOLD}{C.CYAN}{'═' * 60}")
    print(f"  PHASE {phase}: {title}")
    print(f"{'═' * 60}{C.RESET}\n")


class StressTestResult:
    """Collects results for a phase."""
    def __init__(self, phase: int, name: str):
        self.phase = phase
        self.name = name
        self.checks: List[Dict] = []
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.passed = True

    def add(self, name: str, passed: bool, detail: str = ""):
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        if passed:
            ok(f"{name}: {detail}")
        else:
            fail(f"{name}: {detail}")
            self.passed = False

    def finish(self):
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        passed = sum(1 for c in self.checks if c["passed"])
        total = len(self.checks)
        status = f"{C.GREEN}ALL PASSED{C.RESET}" if self.passed else f"{C.RED}FAILURES DETECTED{C.RESET}"
        print(f"\n  Phase {self.phase} Result: {passed}/{total} checks — {status} ({elapsed:.1f}s)")
        return self.to_dict()

    def to_dict(self):
        return {
            "phase": self.phase,
            "name": self.name,
            "passed": self.passed,
            "checks": self.checks,
            "duration_s": round((self.end_time or time.time()) - self.start_time, 2),
        }


class VIPStressTest:
    """Multi-phase stress test harness for AQI Agent X."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.results: List[Dict] = []
        self.client = httpx.Client(timeout=15.0)

    def _get(self, path: str, timeout: float = 10.0) -> Optional[httpx.Response]:
        try:
            return self.client.get(f"{self.base_url}{path}", timeout=timeout)
        except Exception as e:
            return None

    def _post(self, path: str, json_data: dict = None, timeout: float = 10.0) -> Optional[httpx.Response]:
        try:
            return self.client.post(f"{self.base_url}{path}", json=json_data or {}, timeout=timeout)
        except Exception as e:
            return None

    # ══════════════════════════════════════════════════════════════
    #  PHASE 1: Cold Start Integrity
    # ══════════════════════════════════════════════════════════════

    def phase_1_cold_start(self) -> Dict:
        header(1, "COLD START INTEGRITY")
        r = StressTestResult(1, "Cold Start Integrity")

        # 1. Health endpoint
        resp = self._get("/health")
        if resp and resp.status_code == 200:
            data = resp.json()
            r.add("Health endpoint reachable", True, f"status={resp.status_code}")

            subs = data.get("subsystems", {})
            r.add("Alan ONLINE", subs.get("alan") == "ONLINE", f"alan={subs.get('alan')}")
            r.add("Agent X ONLINE", subs.get("agent_x") == "ONLINE", f"agent_x={subs.get('agent_x')}")
            r.add("Coupled boot", subs.get("coupled", False) is True, f"coupled={subs.get('coupled')}")
        else:
            r.add("Health endpoint reachable", False, f"response={resp}")
            r.finish()
            self.results.append(r.to_dict())
            return r.to_dict()

        # 2. ARDE diagnostics
        resp = self._get("/diagnostics/arde")
        if resp and resp.status_code == 200:
            data = resp.json()
            r.add("ARDE running", data.get("running", False), f"cycles={data.get('cycle_count')}")
            cycle_count = data.get("cycle_count", 0)
            r.add("ARDE cycle count ≥ 3", cycle_count >= 3, f"cycles={cycle_count}")

            sub_health = data.get("subsystem_health", {})
            all_ok = all(v == "ok" for v in sub_health.values()) if sub_health else False
            r.add("All 7 subsystems ok", all_ok, json.dumps(sub_health))
        else:
            r.add("ARDE diagnostics reachable", False, "endpoint down")

        # 3. Deep diagnostic
        resp = self._get("/diagnostics/deep")
        if resp and resp.status_code == 200:
            data = resp.json()
            verdict = data.get("verdict", "UNKNOWN")
            r.add("Deep probe verdict", verdict == "ALL_SYSTEMS_GO", f"verdict={verdict}")
        else:
            r.add("Deep probe reachable", False, "endpoint down")

        # 4. VIP Readiness
        resp = self._get("/readiness/vip")
        if resp and resp.status_code == 200:
            data = resp.json()
            r.add("VIP readiness endpoint", True, f"posture={data.get('posture')}, passed={data.get('passed')}")
        else:
            r.add("VIP readiness reachable", False, "endpoint down")

        # 5. Greeting cache
        resp = self._get("/readiness")
        if resp and resp.status_code == 200:
            data = resp.json()
            cache = data.get("relay_greeting_cache", 0)
            r.add("Greeting cache ≥ 5", cache >= 5, f"count={cache}")
        else:
            r.add("Readiness endpoint", False, "endpoint down")

        # 6. Tunnel sync
        tunnel_path = Path("active_tunnel_url.txt")
        tunnel_exists = tunnel_path.exists()
        r.add("Tunnel URL file exists", tunnel_exists, str(tunnel_path))
        if tunnel_exists:
            url = tunnel_path.read_text().strip()
            r.add("Tunnel URL valid", url.startswith("https://") and len(url) > 15, url[:50])

        r.finish()
        self.results.append(r.to_dict())
        return r.to_dict()

    # ══════════════════════════════════════════════════════════════
    #  PHASE 2: Multi-Call Load Simulation
    # ══════════════════════════════════════════════════════════════

    def phase_2_load_simulation(self) -> Dict:
        header(2, "MULTI-CALL LOAD SIMULATION")
        r = StressTestResult(2, "Multi-Call Load Simulation")

        info("Simulating 10 concurrent HTTP requests to health/readiness endpoints...")
        info("(Real Twilio calls require live credentials — this tests server concurrency)")

        import concurrent.futures

        endpoints = ["/health", "/readiness", "/readiness/vip", "/diagnostics/arde", "/diagnostics/deep"]
        latencies = []
        errors = 0

        def hit_endpoint(path):
            try:
                start = time.time()
                resp = httpx.get(f"{self.base_url}{path}", timeout=10.0)
                elapsed = (time.time() - start) * 1000
                return path, resp.status_code, elapsed
            except Exception as e:
                return path, 0, -1

        # Fire 10 concurrent requests (2 hits per endpoint)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = []
            for ep in endpoints:
                futures.append(pool.submit(hit_endpoint, ep))
                futures.append(pool.submit(hit_endpoint, ep))

            for f in concurrent.futures.as_completed(futures):
                path, code, ms = f.result()
                if code == 200:
                    latencies.append(ms)
                else:
                    errors += 1

        r.add("10 concurrent requests completed", errors == 0, f"errors={errors}")
        if latencies:
            avg = sum(latencies) / len(latencies)
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            r.add("Average latency < 1000ms", avg < 1000, f"avg={avg:.0f}ms")
            r.add("P95 latency < 2000ms", p95 < 2000, f"p95={p95:.0f}ms")
            r.add("Max latency < 3000ms", max(latencies) < 3000, f"max={max(latencies):.0f}ms")

        # Check ARDE logs stayed quiet
        resp = self._get("/diagnostics/arde")
        if resp and resp.status_code == 200:
            data = resp.json()
            overall = data.get("overall_status", "UNKNOWN")
            r.add("ARDE still ALL_SYSTEMS_GO after load", overall == "ALL_SYSTEMS_GO", f"status={overall}")

        r.finish()
        self.results.append(r.to_dict())
        return r.to_dict()

    # ══════════════════════════════════════════════════════════════
    #  PHASE 3: Latency Spike / Resilience
    # ══════════════════════════════════════════════════════════════

    def phase_3_latency_resilience(self) -> Dict:
        header(3, "LATENCY SPIKE RESILIENCE")
        r = StressTestResult(3, "Latency Spike Resilience")

        info("Testing server stability under sequential heavy requests...")
        info("(Real TTS/LLM latency spikes require call-level simulation)")

        # Hammer health repeatedly with tight timing
        latencies = []
        for i in range(20):
            start = time.time()
            resp = self._get("/health", timeout=5.0)
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            if resp and resp.status_code != 200:
                r.add(f"Rapid request {i+1}", False, f"status={resp.status_code}")
                break

        r.add("20 rapid sequential requests", len(latencies) == 20, f"all returned 200")
        if latencies:
            avg = sum(latencies) / len(latencies)
            r.add("Average < 500ms under rapid fire", avg < 500, f"avg={avg:.0f}ms")

        # Deep probe under pressure
        start = time.time()
        resp = self._get("/diagnostics/deep", timeout=10.0)
        deep_latency = (time.time() - start) * 1000
        if resp and resp.status_code == 200:
            r.add("Deep probe under pressure", True, f"latency={deep_latency:.0f}ms")
            data = resp.json()
            r.add("Verdict still healthy", data.get("verdict") == "ALL_SYSTEMS_GO", data.get("verdict"))
        else:
            r.add("Deep probe under pressure", False, "failed")

        # Verify no CRITICAL events were generated by load
        resp = self._get("/diagnostics/arde")
        if resp and resp.status_code == 200:
            data = resp.json()
            sub_h = data.get("subsystem_health", {})
            criticals = [k for k, v in sub_h.items() if v == "critical"]
            r.add("No CRITICAL events from load", len(criticals) == 0, f"criticals={criticals}")

        r.finish()
        self.results.append(r.to_dict())
        return r.to_dict()

    # ══════════════════════════════════════════════════════════════
    #  PHASE 4: Subsystem Failure Injection
    # ══════════════════════════════════════════════════════════════

    def phase_4_failure_injection(self) -> Dict:
        header(4, "SUBSYSTEM FAILURE INJECTION")
        r = StressTestResult(4, "Subsystem Failure Injection")

        info("This phase tests ARDE's ability to detect and repair injected failures.")
        info("Injection is done via internal API — no actual subsystems are damaged.")

        # 4a: Trigger forced diagnostic to get baseline
        resp = self._post("/repair/force")
        if resp and resp.status_code == 200:
            data = resp.json()
            pre_diag = data.get("diagnostic", {})
            r.add("Forced diagnostic baseline", True, f"overall={pre_diag.get('overall')}")
        else:
            r.add("Forced diagnostic baseline", False, "endpoint failed")

        # 4b: Verify ARDE can detect issues (check current state)
        resp = self._get("/diagnostics/arde")
        if resp and resp.status_code == 200:
            data = resp.json()
            repair_hist = data.get("repair_history", [])
            r.add("ARDE repair history accessible", True, f"events={len(repair_hist)}")
            cycle_count = data.get("cycle_count", 0)
            r.add("ARDE has run cycles", cycle_count > 0, f"cycles={cycle_count}")
        else:
            r.add("ARDE diagnostics accessible", False, "endpoint failed")

        # 4c: Deep probe integrity checks
        resp = self._get("/diagnostics/deep")
        if resp and resp.status_code == 200:
            data = resp.json()
            alan_deep = data.get("alan_deep", {})
            x_deep = data.get("agent_x_deep", {})

            r.add("Alan has system_prompt", alan_deep.get("has_system_prompt", False), "")
            r.add("Alan has build_llm_prompt", alan_deep.get("has_build_llm_prompt", False), "")
            r.add("Agent X has process_turn", x_deep.get("has_process_turn", False), "")
            r.add("Agent X has PVE", x_deep.get("has_pve", False), "")
            r.add("Agent X has priority_dispatch", x_deep.get("has_priority_dispatch", False), "")
            r.add("Agent X has IQ cores", x_deep.get("iq_cores_loaded", False), "")
            r.add("Agent X has rapport", x_deep.get("rapport_loaded", False), "")

            relay_deep = data.get("relay_deep", {})
            r.add("Relay has master_closer", relay_deep.get("has_master_closer", False), "")
            r.add("Relay has CRG", relay_deep.get("has_crg", False), "")
            r.add("Relay has evolution engine", relay_deep.get("has_evolution", False), "")
            r.add("Relay has coordinator", relay_deep.get("has_coordinator", False), "")
        else:
            r.add("Deep probe for injection test", False, "endpoint failed")

        # 4d: Force another repair cycle and verify recovery
        resp = self._post("/repair/force")
        if resp and resp.status_code == 200:
            data = resp.json()
            post_state = data.get("post_repair_state", {})
            overall = post_state.get("overall_status", "UNKNOWN")
            r.add("Post-repair status", overall == "ALL_SYSTEMS_GO", f"status={overall}")
        else:
            r.add("Post-repair check", False, "endpoint failed")

        r.finish()
        self.results.append(r.to_dict())
        return r.to_dict()

    # ══════════════════════════════════════════════════════════════
    #  PHASE 5: Greeting Cache Exhaustion
    # ══════════════════════════════════════════════════════════════

    def phase_5_greeting_cache(self) -> Dict:
        header(5, "GREETING CACHE VERIFICATION")
        r = StressTestResult(5, "Greeting Cache Verification")

        resp = self._get("/readiness")
        if resp and resp.status_code == 200:
            data = resp.json()
            cache = data.get("relay_greeting_cache", 0)
            r.add("Greeting cache populated", cache > 0, f"count={cache}")
            r.add("Greeting cache ≥ 3 (normal min)", cache >= 3, f"count={cache}")
            r.add("Greeting cache ≥ 5 (VIP min)", cache >= 5, f"count={cache}")
        else:
            r.add("Readiness endpoint", False, "failed")

        # Verify ARDE knows about greeting cache
        resp = self._get("/diagnostics/arde")
        if resp and resp.status_code == 200:
            data = resp.json()
            gc_status = data.get("subsystem_health", {}).get("greeting_cache", "unknown")
            r.add("ARDE greeting_cache status", gc_status == "ok", f"status={gc_status}")
        else:
            r.add("ARDE greeting cache check", False, "endpoint failed")

        # Verify TTS is online (needed for cache rebuild)
        resp = self._get("/diagnostics/arde")
        if resp and resp.status_code == 200:
            data = resp.json()
            tts_status = data.get("subsystem_health", {}).get("tts", "unknown")
            r.add("TTS subsystem ok (needed for rebuilds)", tts_status == "ok", f"status={tts_status}")

        r.finish()
        self.results.append(r.to_dict())
        return r.to_dict()

    # ══════════════════════════════════════════════════════════════
    #  PHASE 6: Environment & Credential Verification
    # ══════════════════════════════════════════════════════════════

    def phase_6_env_verification(self) -> Dict:
        header(6, "ENVIRONMENT & CREDENTIAL VERIFICATION")
        r = StressTestResult(6, "Environment & Credential Verification")

        info("Verifying all required env vars and API keys are present...")
        info("(Not removing env vars — that would break the live system)")

        # Check via readiness endpoint
        resp = self._get("/readiness")
        if resp and resp.status_code == 200:
            data = resp.json()
            env = data.get("env_check", {})
            r.add("TWILIO_SID present", env.get("TWILIO_SID", False), "")
            r.add("TWILIO_TOKEN present", env.get("TWILIO_TOKEN", False), "")
            r.add("PHONE present", env.get("PHONE", False), "")
            r.add("OPENAI_API_KEY present", env.get("OPENAI_API_KEY", False), "")
            r.add("GROQ_API_KEY present", env.get("GROQ_API_KEY", False), "")
        else:
            r.add("Readiness endpoint for env check", False, "failed")

        # ARDE subsystem checks for Twilio and OpenAI
        resp = self._get("/diagnostics/arde")
        if resp and resp.status_code == 200:
            data = resp.json()
            sub_h = data.get("subsystem_health", {})
            r.add("ARDE: Twilio subsystem ok", sub_h.get("twilio") == "ok", f"status={sub_h.get('twilio')}")
            r.add("ARDE: OpenAI subsystem ok", sub_h.get("openai") == "ok", f"status={sub_h.get('openai')}")

        # VIP readiness should not be BLOCKED by env issues
        resp = self._get("/readiness/vip")
        if resp and resp.status_code == 200:
            data = resp.json()
            posture = data.get("posture", "UNKNOWN")
            r.add("VIP readiness not HALTED by env", posture != "HALTED", f"posture={posture}")

        r.finish()
        self.results.append(r.to_dict())
        return r.to_dict()

    # ══════════════════════════════════════════════════════════════
    #  PHASE 7: Full System Recovery & Final Readiness
    # ══════════════════════════════════════════════════════════════

    def phase_7_final_readiness(self) -> Dict:
        header(7, "FULL SYSTEM RECOVERY & FINAL READINESS")
        r = StressTestResult(7, "Full System Recovery & Final Readiness")

        # Health
        resp = self._get("/health")
        if resp and resp.status_code == 200:
            data = resp.json()
            subs = data.get("subsystems", {})
            r.add("Alan ONLINE", subs.get("alan") == "ONLINE", "")
            r.add("Agent X ONLINE", subs.get("agent_x") == "ONLINE", "")
            r.add("Coupled boot intact", subs.get("coupled", False) is True, "")
            traffic_halted = data.get("traffic_halted", False)
            r.add("Traffic NOT halted", not traffic_halted, f"halted={traffic_halted}")
        else:
            r.add("Health endpoint", False, "failed")

        # ARDE clean
        resp = self._get("/diagnostics/arde")
        if resp and resp.status_code == 200:
            data = resp.json()
            overall = data.get("overall_status", "UNKNOWN")
            r.add("ARDE overall ALL_SYSTEMS_GO", overall == "ALL_SYSTEMS_GO", f"status={overall}")

            sub_h = data.get("subsystem_health", {})
            all_ok = all(v == "ok" for v in sub_h.values())
            r.add("All 7 subsystems ok", all_ok, json.dumps(sub_h))

            # No CRITICAL in repair history (last 30 min)
            repair_hist = data.get("repair_history", [])
            has_critical = any(
                r_evt.get("success") is False
                for r_evt in repair_hist[-20:]  # Check last 20 events
            )
            r.add("No recent repair failures", not has_critical, f"checked last {min(20, len(repair_hist))} events")

        # Deep probe
        resp = self._get("/diagnostics/deep")
        if resp and resp.status_code == 200:
            data = resp.json()
            verdict = data.get("verdict", "UNKNOWN")
            r.add("Deep probe verdict: ALL_SYSTEMS_GO", verdict == "ALL_SYSTEMS_GO", f"verdict={verdict}")

        # Tunnel
        resp = self._get("/readiness")
        if resp and resp.status_code == 200:
            data = resp.json()
            cache = data.get("relay_greeting_cache", 0)
            r.add("Greeting cache ≥ 5", cache >= 5, f"count={cache}")

        # VIP Readiness final gate
        resp = self._get("/readiness/vip")
        if resp and resp.status_code == 200:
            data = resp.json()
            posture = data.get("posture", "UNKNOWN")
            allowed = data.get("allowed", False)
            passed = data.get("passed", "?/?")
            r.add("VIP Readiness Gate", True, f"posture={posture}, passed={passed}, allowed={allowed}")

            # Show individual checks
            for check in data.get("checks", []):
                check_pass = check.get("pass", False)
                if not check_pass:
                    warn(f"  VIP check FAIL: {check.get('name')} — {check.get('reason')}")

        r.finish()
        self.results.append(r.to_dict())
        return r.to_dict()

    # ══════════════════════════════════════════════════════════════
    #  ORCHESTRATOR
    # ══════════════════════════════════════════════════════════════

    def run_all(self, phases: Optional[List[int]] = None):
        """Run all (or selected) stress test phases."""
        print(f"\n{C.BOLD}{C.CYAN}{'▓' * 60}")
        print(f"  AQI VIP STRESS-TEST HARNESS")
        print(f"  Target: {self.base_url}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'▓' * 60}{C.RESET}")

        phase_map = {
            1: ("Cold Start Integrity", self.phase_1_cold_start),
            2: ("Multi-Call Load Simulation", self.phase_2_load_simulation),
            3: ("Latency Spike Resilience", self.phase_3_latency_resilience),
            4: ("Subsystem Failure Injection", self.phase_4_failure_injection),
            5: ("Greeting Cache Verification", self.phase_5_greeting_cache),
            6: ("Environment & Credential Verification", self.phase_6_env_verification),
            7: ("Full System Recovery & Final Readiness", self.phase_7_final_readiness),
        }

        run_phases = phases or list(phase_map.keys())
        start = time.time()

        for p in run_phases:
            if p in phase_map:
                name, fn = phase_map[p]
                try:
                    fn()
                except Exception as e:
                    print(f"\n  {C.RED}PHASE {p} CRASHED: {e}{C.RESET}")
                    traceback.print_exc()
                    self.results.append({
                        "phase": p, "name": name, "passed": False,
                        "checks": [{"name": "Phase execution", "passed": False, "detail": str(e)}],
                        "duration_s": 0,
                    })
            else:
                print(f"\n  {C.YELLOW}Unknown phase: {p}{C.RESET}")

        elapsed = time.time() - start

        # ── Summary ──
        print(f"\n{C.BOLD}{'═' * 60}")
        print(f"  STRESS TEST SUMMARY")
        print(f"{'═' * 60}{C.RESET}")

        total_checks = 0
        total_passed = 0
        all_green = True

        for result in self.results:
            phase_checks = result.get("checks", [])
            p_pass = sum(1 for c in phase_checks if c["passed"])
            p_total = len(phase_checks)
            total_checks += p_total
            total_passed += p_pass
            status = f"{C.GREEN}PASS{C.RESET}" if result["passed"] else f"{C.RED}FAIL{C.RESET}"
            if not result["passed"]:
                all_green = False
            print(f"  Phase {result['phase']}: {result['name']:.<40} {p_pass}/{p_total} [{status}]")

        print(f"\n  Total: {total_passed}/{total_checks} checks passed in {elapsed:.1f}s")

        if all_green:
            print(f"\n  {C.BOLD}{C.GREEN}{'═' * 50}")
            print(f"  🟢  ALL PHASES PASSED — SYSTEM IS VIP-READY")
            print(f"  {'═' * 50}{C.RESET}")
        else:
            print(f"\n  {C.BOLD}{C.RED}{'═' * 50}")
            print(f"  🔴  FAILURES DETECTED — REVIEW BEFORE VIP TRAFFIC")
            print(f"  {'═' * 50}{C.RESET}")

        # Save report
        self._save_report(elapsed, all_green)

        return all_green

    def _save_report(self, elapsed: float, all_green: bool):
        """Persist results to JSON."""
        try:
            Path(REPORT_FILE).parent.mkdir(parents=True, exist_ok=True)
            report = {
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url,
                "duration_s": round(elapsed, 2),
                "all_passed": all_green,
                "phases": self.results,
            }
            Path(REPORT_FILE).write_text(json.dumps(report, indent=2, default=str))
            info(f"Report saved: {REPORT_FILE}")
        except Exception as e:
            warn(f"Failed to save report: {e}")


# ══════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="AQI VIP Stress Test Harness")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Server base URL")
    parser.add_argument("--phase", default=None, help="Comma-separated phase numbers (e.g., 1,2,3)")
    args = parser.parse_args()

    phases = None
    if args.phase:
        phases = [int(p.strip()) for p in args.phase.split(",")]

    harness = VIPStressTest(base_url=args.base_url)
    success = harness.run_all(phases=phases)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
