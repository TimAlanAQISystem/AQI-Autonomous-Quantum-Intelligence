#!/usr/bin/env python3
"""
Negative Proof: Persistence Pillar Tests
Proves that CallMemory, Preferences, and ConversationHistory
survive call endings and are restored on the next call.
"""

import sys
import os
import json
import time
import urllib.request

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

print("=" * 60)
print("PERSISTENCE PILLAR — NEGATIVE PROOF")
print("=" * 60)
print()

passed = 0
failed = 0

# ── TEST 1: MerchantProfile has new fields ──
print("[TEST 1] MerchantProfile schema has persistence fields...")
from merchant_identity_persistence import MerchantProfile
p = MerchantProfile(merchant_id="test", phone_number="test")
has_call_memories = hasattr(p, 'call_memories')
has_detected_preferences = hasattr(p, 'detected_preferences')
has_conversation_summaries = hasattr(p, 'conversation_summaries')
if has_call_memories and has_detected_preferences and has_conversation_summaries:
    print(f"  PASS (call_memories={has_call_memories}, detected_preferences={has_detected_preferences}, conversation_summaries={has_conversation_summaries})")
    passed += 1
else:
    print(f"  FAIL (call_memories={has_call_memories}, detected_preferences={has_detected_preferences}, conversation_summaries={has_conversation_summaries})")
    failed += 1
print()

# ── TEST 2: CallMemory persists through update_profile_from_call ──
print("[TEST 2] CallMemory persistence via MIP...")
from merchant_identity_persistence import MerchantIdentityPersistence
import tempfile

# Use a temp file so we don't pollute real data
tmp_db = tempfile.mktemp(suffix=".json")
mip = MerchantIdentityPersistence(db_path=tmp_db)

# Simulate call 1
call_data_1 = {
    "outcome": "kept_engaged",
    "archetype": "price_shopper",
    "call_memory": {
        "key_points": ["worried about rates", "loyal to current processor"],
        "objections": [{"type": "rate", "strength": 4}],
        "agreements": ["open to looking at numbers"],
        "goals": ["keep costs predictable"]
    },
    "preferences": {
        "detail_level": "low",
        "pacing": "fast",
        "formality": "casual",
        "closing_style_bias": "direct"
    },
    "conversation_turns": [
        {"user": "Yeah what do you want?", "alan": "Hey, this is Alan with Signature Card. I wanted to chat about your processing rates."},
        {"user": "I'm happy with my rates", "alan": "Got it. Quick question — are you on interchange plus or flat rate?"},
        {"user": "Flat rate I think, like 2.9", "alan": "Gotcha. At your volume, interchange plus would save you about 400 a month. Want to see the math?"},
    ]
}
mip.update_profile_from_call("+15551234567", call_data_1)

# Simulate call 2
call_data_2 = {
    "outcome": "statement_obtained",
    "archetype": "value_seeker",
    "call_memory": {
        "key_points": ["asked for statement review", "mentioned kill fee concern"],
        "objections": [{"type": "kill_fee", "strength": 3}],
        "agreements": ["will send statement", "follow up Thursday"],
        "goals": ["save on processing"]
    },
    "preferences": {
        "detail_level": "medium",
        "pacing": "normal",
        "formality": "casual",
        "closing_style_bias": "consultative"
    },
    "conversation_turns": [
        {"user": "You called before right?", "alan": "Yeah I did. Last time we talked about your flat rate setup."},
        {"user": "Right. So what can you do for me?", "alan": "If you send me a recent statement, I can show you exactly where you're overpaying."},
    ]
}
mip.update_profile_from_call("+15551234567", call_data_2)

# Now verify everything persisted
profile = mip.load_profile("+15551234567")

# Check call memories
if len(profile.call_memories) == 2:
    cm1 = profile.call_memories[0]
    cm2 = profile.call_memories[1]
    if (cm1.get("key_points") and "worried about rates" in cm1["key_points"]
        and cm2.get("agreements") and "will send statement" in cm2["agreements"]):
        print(f"  PASS (2 call memories stored, data intact)")
        passed += 1
    else:
        print(f"  FAIL (call memory data corrupted)")
        failed += 1
else:
    print(f"  FAIL (expected 2 call memories, got {len(profile.call_memories)})")
    failed += 1
print()

# ── TEST 3: Preferences persist ──
print("[TEST 3] MerchantPreferences persistence...")
if (profile.detected_preferences.get("pacing") == "normal"
    and profile.detected_preferences.get("formality") == "casual"
    and profile.detected_preferences.get("closing_style_bias") == "consultative"):
    print(f"  PASS (preferences from call 2: pacing=normal, formality=casual, closing=consultative)")
    passed += 1
else:
    print(f"  FAIL (preferences: {profile.detected_preferences})")
    failed += 1

# Also check legacy field sync
if profile.preferred_pacing == "normal" and profile.preferred_tone == "casual":
    print(f"  Legacy sync: PASS (preferred_pacing=normal, preferred_tone=casual)")
    passed += 1
else:
    print(f"  Legacy sync: FAIL (pacing={profile.preferred_pacing}, tone={profile.preferred_tone})")
    failed += 1
print()

# ── TEST 4: Conversation summaries persist (per-merchant) ──
print("[TEST 4] Per-merchant conversation summaries...")
if len(profile.conversation_summaries) == 2:
    conv1 = profile.conversation_summaries[0]
    conv2 = profile.conversation_summaries[1]
    if conv1["turn_count"] == 3 and conv2["turn_count"] == 2:
        print(f"  PASS (2 conversations stored: {conv1['turn_count']} turns + {conv2['turn_count']} turns)")
        passed += 1
    else:
        print(f"  FAIL (turn counts wrong)")
        failed += 1
else:
    print(f"  FAIL (expected 2 summaries, got {len(profile.conversation_summaries)})")
    failed += 1
print()

# ── TEST 5: seed_context_from_profile restores everything ──
print("[TEST 5] Context seeding restores all memory...")
ctx = mip.seed_context_from_profile(profile)
checks = {
    "is_returning": ctx.get("is_returning") == True,
    "restored_preferences": ctx.get("restored_preferences") is not None,
    "previous_call_memories": ctx.get("previous_call_memories") is not None and len(ctx.get("previous_call_memories", [])) == 2,
    "previous_conversations": ctx.get("previous_conversations") is not None and len(ctx.get("previous_conversations", [])) == 2,
    "archetype_hint": ctx.get("archetype_hint") == "value_seeker",
}
all_ok = all(checks.values())
if all_ok:
    print(f"  PASS (all context fields restored)")
    passed += 1
else:
    for k, v in checks.items():
        if not v:
            print(f"  FAIL: {k} = {ctx.get(k)}")
    failed += 1
print()

# ── TEST 6: Bounded growth (MAX_CALL_MEMORIES = 3) ──
print("[TEST 6] Bounded growth — max 3 call memories...")
# Add 2 more calls (total 4 — should evict oldest)
for i in range(2):
    mip.update_profile_from_call("+15551234567", {
        "call_memory": {"key_points": [f"call_{i+3}_point"], "objections": [], "agreements": [], "goals": []},
        "preferences": {"detail_level": "medium", "pacing": "normal", "formality": "neutral"},
    })
profile = mip.load_profile("+15551234567")
if len(profile.call_memories) == 3:
    # Oldest should be call 2 (call 1 evicted)
    if "asked for statement review" in profile.call_memories[0].get("key_points", []):
        print(f"  PASS (4 calls → 3 retained, oldest evicted)")
        passed += 1
    else:
        print(f"  FAIL (wrong call evicted. First cm: {profile.call_memories[0]})")
        failed += 1
else:
    print(f"  FAIL (expected 3, got {len(profile.call_memories)})")
    failed += 1
print()

# ── TEST 7: Bounded growth (MAX_CONVERSATION_SUMMARIES = 2) ──
print("[TEST 7] Bounded growth — max 2 conversation summaries...")
# Add 1 more conversation (total 3 — should evict oldest)
mip.update_profile_from_call("+15551234567", {
    "conversation_turns": [
        {"user": "Third call test", "alan": "Welcome back again."}
    ]
})
profile = mip.load_profile("+15551234567")
if len(profile.conversation_summaries) == 2:
    # Most recent should be the one we just added
    if profile.conversation_summaries[-1]["turns"][-1]["user"] == "Third call test":
        print(f"  PASS (3 convos → 2 retained, oldest evicted)")
        passed += 1
    else:
        print(f"  FAIL (wrong conversation evicted)")
        failed += 1
else:
    print(f"  FAIL (expected 2, got {len(profile.conversation_summaries)})")
    failed += 1
print()

# ── TEST 8: Preference decay ──
print("[TEST 8] Preference decay check (>90 days)...")
from datetime import datetime, timedelta
# Manually set last_contact to 91 days ago
profile.last_contact = (datetime.utcnow() - timedelta(days=91)).isoformat()
mip.profiles["+15551234567"] = profile
mip._save_profiles()

# Reload and seed
mip2 = MerchantIdentityPersistence(db_path=tmp_db)
profile2 = mip2.load_profile("+15551234567")
ctx2 = mip2.seed_context_from_profile(profile2)
if "restored_preferences" not in ctx2:
    print(f"  PASS (preferences decayed after 91 days — fresh start)")
    passed += 1
else:
    print(f"  FAIL (preferences should have decayed but were restored)")
    failed += 1
print()

# ── TEST 9: do_not_store_profile flag ──
print("[TEST 9] do_not_store_profile flag respected...")
mip3 = MerchantIdentityPersistence(db_path=tempfile.mktemp(suffix=".json"))
p3 = mip3.load_profile("+15559999999")
p3.do_not_store_profile = True
mip3.profiles["+15559999999"] = p3
mip3.update_profile_from_call("+15559999999", {
    "call_memory": {"key_points": ["should not be stored"]},
    "preferences": {"pacing": "fast"},
})
p3_check = mip3.load_profile("+15559999999")
if len(p3_check.call_memories) == 0 and not p3_check.detected_preferences:
    print(f"  PASS (no data stored when do_not_store_profile=True)")
    passed += 1
else:
    print(f"  FAIL (data was stored despite flag)")
    failed += 1
print()

# ── TEST 10: Server still healthy ──
print("[TEST 10] Server health after all tests...")
try:
    r = urllib.request.urlopen("http://127.0.0.1:8777/health", timeout=3)
    if r.status == 200:
        print(f"  PASS (200 OK)")
        passed += 1
    else:
        print(f"  FAIL ({r.status})")
        failed += 1
except Exception as e:
    print(f"  FAIL ({e})")
    failed += 1
print()

# ── TEST 11: Disk persistence survives reload ──
print("[TEST 11] Disk persistence — survives MIP reload...")
mip_reload = MerchantIdentityPersistence(db_path=tmp_db)
profile_reload = mip_reload.load_profile("+15551234567")
if (len(profile_reload.call_memories) == 3
    and len(profile_reload.conversation_summaries) == 2
    and profile_reload.detected_preferences.get("pacing") is not None):
    print(f"  PASS (all data survived disk reload: {len(profile_reload.call_memories)} memories, {len(profile_reload.conversation_summaries)} convos, prefs intact)")
    passed += 1
else:
    print(f"  FAIL (data lost on reload)")
    failed += 1
print()

# Cleanup
try:
    os.unlink(tmp_db)
except:
    pass

# ── SUMMARY ──
print("=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} PASSED | {failed}/{total} FAILED")
if failed == 0:
    print("VERDICT: PERSISTENCE PILLAR VERIFIED — NOTHING IS LOST")
else:
    print(f"VERDICT: {failed} ISSUE(S) NEED ATTENTION")
print("=" * 60)
