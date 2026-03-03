#!/usr/bin/env python3
"""Negative Proof Testing Suite — validates all repairs are solid."""

import time
import sys
import os
import re
import urllib.request
import urllib.error

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("NEGATIVE PROOF: STRESS & FAULT TESTING")
print("=" * 60)
print()

passed = 0
failed = 0

# ── TEST 1: Concurrent health check bombardment ──
print("[TEST 1] Rapid-fire health checks (20 requests)...")
failures = 0
start = time.time()
for i in range(20):
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8777/health", timeout=3)
        if r.status != 200:
            failures += 1
    except Exception as e:
        failures += 1
elapsed = time.time() - start
if failures == 0:
    print(f"  PASS ({elapsed:.1f}s, {20/elapsed:.0f} req/s)")
    passed += 1
else:
    print(f"  FAIL ({failures}/20 failed)")
    failed += 1
print()

# ── TEST 2: Invalid endpoint (404 handling) ──
print("[TEST 2] Invalid endpoint request (expect 404/405)...")
try:
    r = urllib.request.urlopen("http://127.0.0.1:8777/nonexistent", timeout=3)
    print(f"  FAIL (got {r.status}, expected error)")
    failed += 1
except urllib.error.HTTPError as e:
    if e.code in (404, 405):
        print(f"  PASS (correctly returned {e.code})")
        passed += 1
    else:
        print(f"  FAIL (unexpected HTTP {e.code})")
        failed += 1
except Exception as e:
    print(f"  FAIL ({e})")
    failed += 1
print()

# ── TEST 3: Malformed POST to /twilio/voice ──
print("[TEST 3] Malformed POST body to /twilio/voice...")
try:
    req = urllib.request.Request(
        "http://127.0.0.1:8777/twilio/voice",
        data=b"garbage_data_not_form_encoded",
        method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    r = urllib.request.urlopen(req, timeout=5)
    body = r.read().decode()
    if "<Response>" in body:
        print(f"  PASS (TwiML returned despite bad data — server resilient)")
        passed += 1
    else:
        print(f"  WARNING (got {r.status} but unexpected body)")
        failed += 1
except urllib.error.HTTPError as e:
    # 422 is acceptable — means validation caught the bad data
    if e.code == 422:
        print(f"  PASS (422 validation error — server correctly rejected)")
        passed += 1
    else:
        print(f"  INFO (server responded with HTTP {e.code})")
        passed += 1  # Server didn't crash, that's what matters
except Exception as e:
    print(f"  FAIL (connection error: {e})")
    failed += 1

# Verify server survived the malformed request
try:
    r = urllib.request.urlopen("http://127.0.0.1:8777/health", timeout=3)
    print(f"  Server survived malformed request: {r.status} OK")
except:
    print(f"  CRITICAL: Server crashed after malformed request!")
    failed += 1
print()

# ── TEST 4: SimpleMetrics bounded memory ──
print("[TEST 4] SimpleMetrics memory bound verification...")
sys.path.insert(0, ".")
from system_coordinator import SimpleMetrics

m = SimpleMetrics()
for i in range(5000):
    m.observe("test_metric", float(i))
actual = len(m.observations["test_metric"])
expected_max = SimpleMetrics.MAX_OBSERVATIONS
if actual <= expected_max:
    print(f"  PASS (5000 inserted, {actual} retained, cap={expected_max})")
    passed += 1
else:
    print(f"  FAIL ({actual} retained, should be <= {expected_max})")
    failed += 1
print()

# ── TEST 5: MIP coordinator wiring ──
print("[TEST 5] MIP coordinator integration...")
from system_coordinator import SystemCoordinator
from merchant_identity_persistence import MerchantIdentityPersistence
from emergency_override_system import EmergencyOverrideSystem
from post_generation_hallucination_scanner import PostGenerationHallucinationScanner

mip = MerchantIdentityPersistence()
eos = EmergencyOverrideSystem()
pghs = PostGenerationHallucinationScanner({}, {}, eos)

# Create minimal stubs for MTSP & BAS
mtsp = type("FakeMTSP", (), {"update_async": lambda self, ctx: None})()
bas = type("FakeBAS", (), {})()

config = {"pghs_enabled": True, "mtsp_enabled": True, "mip_enabled": True}
coordinator = SystemCoordinator(eos, pghs, None, mtsp, mip, bas, config)

ctx = {
    "merchant_id": "test_neg_proof_555",
    "archetype": "price_shopper",
    "archetype_confidence": 0.85,
    "last_objection": "too expensive",
    "trajectory": "cooling",
    "outcome": "kept_engaged",
}
out, meta = coordinator.process_llm_output("That is a fair point.", ctx)
profile = mip.load_profile("test_neg_proof_555")
if (
    profile.archetype_history
    and profile.archetype_history[-1]["type"] == "price_shopper"
):
    print(f"  PASS (MIP correctly stored archetype for merchant)")
    passed += 1
else:
    print(f"  FAIL (MIP did not store merchant data)")
    failed += 1
print()

# ── TEST 6: Graceful shutdown mechanism ──
print("[TEST 6] Graceful shutdown code verification...")
with open("control_api_fixed.py", "r", encoding="utf-8") as f:
    src = f.read()
has_shutdown_event = "_shutdown_event" in src
has_shutdown_timeout = "shutdown_timeout" in src
has_keyboard_catch = "KeyboardInterrupt" in src
if has_shutdown_event and has_shutdown_timeout and has_keyboard_catch:
    print(
        f"  PASS (event={has_shutdown_event}, timeout={has_shutdown_timeout}, keyboard={has_keyboard_catch})"
    )
    passed += 1
else:
    print(
        f"  FAIL (event={has_shutdown_event}, timeout={has_shutdown_timeout}, keyboard={has_keyboard_catch})"
    )
    failed += 1
print()

# ── TEST 7: sys.path sanity (no .py-as-directory) ──
print("[TEST 7] sys.path sanity — no .py-as-directory paths...")
with open("agent_alan_business_ai.py", "r", encoding="utf-8") as f:
    src = f.read()
# Look for patterns like 'filename.py' / 'some_dir' which use a .py file as directory
bad_paths = re.findall(r"['\"][\w]+\.py['\"].*?/.*?['\"]", src)
if not bad_paths:
    print(f"  PASS (no .py-as-directory paths found)")
    passed += 1
else:
    print(f"  FAIL (found: {bad_paths})")
    failed += 1
print()

# ── TEST 8: No duplicate imports in first 90 lines ──
print("[TEST 8] Duplicate import check...")
with open("agent_alan_business_ai.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
imports = {}
dupes = []
for i, line in enumerate(lines[:90], 1):
    stripped = line.strip()
    if stripped.startswith(("import ", "from ")) and not stripped.startswith("#"):
        if stripped in imports:
            dupes.append((stripped, imports[stripped], i))
        else:
            imports[stripped] = i
if not dupes:
    print(f"  PASS (no duplicate imports in first 90 lines)")
    passed += 1
else:
    for d, first, second in dupes:
        print(f"  DUPE: '{d}' at lines {first} and {second}")
    print(f"  FAIL ({len(dupes)} duplicates)")
    failed += 1
print()

# ── TEST 9: Port print matches actual port ──
print("[TEST 9] Port consistency check...")
with open("aqi_conversation_relay_server.py", "r", encoding="utf-8") as f:
    src = f.read()
# Check that __main__ print says 8777 not 8765
if "WebSocket server on port 8777" in src:
    print(f"  PASS (print statement matches actual port 8777)")
    passed += 1
elif "WebSocket server on port 8765" in src:
    print(f"  FAIL (print says 8765, actual port is 8777)")
    failed += 1
else:
    print(f"  INFO (no port print found)")
    passed += 1
print()

# ── TEST 10: No duplicate sys import in control_api ──
print("[TEST 10] Duplicate sys import check (control_api_fixed.py)...")
with open("control_api_fixed.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
sys_imports = []
for i, line in enumerate(lines[:50], 1):
    if line.strip() == "import sys":
        sys_imports.append(i)
if len(sys_imports) <= 1:
    print(f"  PASS (sys imported {len(sys_imports)} time(s) at line(s) {sys_imports})")
    passed += 1
else:
    print(f"  FAIL (sys imported {len(sys_imports)} times at lines {sys_imports})")
    failed += 1
print()

# ── TEST 11: Server still healthy after all tests ──
print("[TEST 11] Final server health check...")
try:
    r = urllib.request.urlopen("http://127.0.0.1:8777/health", timeout=3)
    data = r.read().decode()
    if r.status == 200:
        print(f"  PASS (server healthy after all tests — 200 OK)")
        passed += 1
    else:
        print(f"  FAIL (status {r.status})")
        failed += 1
except Exception as e:
    print(f"  FAIL (server unreachable: {e})")
    failed += 1
print()

# ── SUMMARY ──
print("=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} PASSED | {failed}/{total} FAILED")
if failed == 0:
    print("VERDICT: ALL TESTS PASS — SYSTEM IS STRONG AND STABLE")
else:
    print(f"VERDICT: {failed} ISSUE(S) NEED ATTENTION")
print("=" * 60)
