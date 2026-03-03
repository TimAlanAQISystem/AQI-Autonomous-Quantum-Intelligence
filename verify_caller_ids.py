#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════
  TWILIO VERIFIED CALLER ID MANAGER — AT SCALE
  Agent X — Number Verification Utility (Twilio SDK)
══════════════════════════════════════════════════════════════════════════

Manages the full lifecycle of Twilio Verified Caller IDs using the
official Twilio Python SDK (twilio>=9.0).

  1. ADD      — Initiate OTP verification (Twilio calls from +14157234000)
  2. LIST     — Show all currently verified caller IDs on the account
  3. REMOVE   — Delete a verified caller ID
  4. CHECK    — Check if a specific number is verified
  5. BULK     — Verify a batch of numbers from a file (one per line)
  6. STATUS   — Check pending verification status from tracker
  7. SYNC     — Sync verified numbers into data/number_pool.json for CRO

HOW VERIFICATION WORKS (from Twilio docs):
  1. You call the API (or run `add`) with a phone number
  2. Twilio SYNCHRONOUSLY returns a 6-digit validation code
  3. Twilio calls that number on PSTN from +14157234000 (English only)
  4. The person answers and enters the 6-digit code on the keypad
  5. Twilio confirms → number is now a verified caller ID
  6. A status callback (if configured) reports success/failure

AT SCALE:
  - Use `bulk` to initiate many verifications in sequence
  - Each verification returns a code synchronously — display & record
  - A local tracker (data/verification_tracker.json) logs all pending
  - Use `status` to see which verifications are confirmed vs pending
  - Use `sync` to push confirmed numbers into CRO number pool

WHY THIS MATTERS:
  Twilio requires that any non-Twilio number used as a caller ID on
  outbound calls be verified first via OTP. Without verification,
  calls using that number as caller ID will FAIL.

USAGE:
  python verify_caller_ids.py list
  python verify_caller_ids.py add +13055551234
  python verify_caller_ids.py add +13055551234 --friendly "Miami Line 1"
  python verify_caller_ids.py remove +13055551234
  python verify_caller_ids.py check +13055551234
  python verify_caller_ids.py bulk data/numbers_to_verify.txt
  python verify_caller_ids.py bulk data/numbers_to_verify.txt --delay 45
  python verify_caller_ids.py status
  python verify_caller_ids.py sync

══════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent / ".env")

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
NUMBER_POOL_FILE = Path(__file__).parent / "data" / "number_pool.json"
TRACKER_FILE = Path(__file__).parent / "data" / "verification_tracker.json"

# Twilio SDK client (lazy init)
_twilio_client = None

def _get_client():
    """Lazy-init Twilio REST client."""
    global _twilio_client
    if _twilio_client is None:
        from twilio.rest import Client
        _twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
    return _twilio_client


# ──────────────────────────────────────────────────────────────────────
#  COLORS / FORMATTING
# ──────────────────────────────────────────────────────────────────────

class C:
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

OK   = f"{C.GREEN}✓{C.RESET}"
WARN = f"{C.YELLOW}⚠{C.RESET}"
FAIL = f"{C.RED}✗{C.RESET}"
INFO = f"{C.CYAN}ℹ{C.RESET}"


def _validate_creds():
    """Ensure Twilio credentials are available."""
    if not TWILIO_SID or not TWILIO_TOKEN:
        print(f"\n  {FAIL} Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN in .env")
        print(f"     Set them in your .env file and retry.\n")
        sys.exit(1)


def _normalize_phone(phone: str) -> str:
    """Normalize phone to E.164 format."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        digits = '1' + digits
    if not digits.startswith('1'):
        digits = '1' + digits
    return f'+{digits}'


def _extract_area_code(phone: str) -> str:
    """Extract area code from E.164 number."""
    clean = re.sub(r'\D', '', phone)
    if clean.startswith('1') and len(clean) == 11:
        return clean[1:4]
    elif len(clean) == 10:
        return clean[:3]
    return "???"


# ══════════════════════════════════════════════════════════════════════
#  VERIFICATION TRACKER — persistent state for at-scale operations
# ══════════════════════════════════════════════════════════════════════

def _load_tracker() -> Dict:
    """Load verification tracker from disk."""
    if TRACKER_FILE.exists():
        try:
            with open(TRACKER_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"pending": {}, "verified": {}, "failed": {}}


def _save_tracker(tracker: Dict):
    """Save verification tracker to disk."""
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2)


def _track_initiated(phone: str, validation_code: str, call_sid: str, friendly_name: str):
    """Record a newly initiated verification."""
    tracker = _load_tracker()
    tracker["pending"][phone] = {
        "validation_code": validation_code,
        "call_sid": call_sid,
        "friendly_name": friendly_name,
        "initiated_at": datetime.now().isoformat(),
    }
    # Remove from failed if retrying
    tracker["failed"].pop(phone, None)
    _save_tracker(tracker)


def _track_verified(phone: str, sid: str):
    """Move a number from pending to verified."""
    tracker = _load_tracker()
    pending_info = tracker["pending"].pop(phone, {})
    tracker["verified"][phone] = {
        "sid": sid,
        "friendly_name": pending_info.get("friendly_name", ""),
        "verified_at": datetime.now().isoformat(),
        "initiated_at": pending_info.get("initiated_at", ""),
    }
    _save_tracker(tracker)


def _track_failed(phone: str, reason: str):
    """Move a number from pending to failed."""
    tracker = _load_tracker()
    pending_info = tracker["pending"].pop(phone, {})
    tracker["failed"][phone] = {
        "reason": reason,
        "failed_at": datetime.now().isoformat(),
        "initiated_at": pending_info.get("initiated_at", ""),
    }
    _save_tracker(tracker)


# ══════════════════════════════════════════════════════════════════════
#  CORE OPERATIONS — Twilio SDK
# ══════════════════════════════════════════════════════════════════════


def list_verified_caller_ids() -> List[Dict]:
    """
    List all verified caller IDs on the Twilio account.
    
    Uses: client.outgoing_caller_ids.list()
    """
    _validate_creds()
    client = _get_client()
    
    all_ids = []
    try:
        caller_ids = client.outgoing_caller_ids.list()
        for cid in caller_ids:
            all_ids.append({
                "sid": cid.sid,
                "phone_number": cid.phone_number,
                "friendly_name": cid.friendly_name,
                "date_created": str(cid.date_created) if cid.date_created else "",
                "date_updated": str(cid.date_updated) if cid.date_updated else "",
            })
    except Exception as e:
        print(f"\n  {FAIL} Twilio API error: {e}\n")
        return []
    
    return all_ids


def add_caller_id(phone: str, friendly_name: str = "",
                  extension: str = "", call_delay: int = 0,
                  status_callback: str = "") -> Dict:
    """
    Initiate verification of a phone number as a caller ID.
    
    Uses: client.validation_requests.create()
    
    Twilio synchronously returns the 6-digit validation_code, then calls
    the number from +14157234000 (English only). The person answers and
    enters the code on the keypad.
    
    Args:
        phone:           The phone number to verify (E.164)
        friendly_name:   Label for this number (e.g., "Miami Line 1")
        extension:       Extension to dial before delivering OTP
        call_delay:      Seconds to wait before sending validation code
        status_callback: URL for Twilio to POST verification status
    
    Returns:
        Dict with validation_code and call_sid
    """
    _validate_creds()
    client = _get_client()
    
    phone = _normalize_phone(phone)
    area = _extract_area_code(phone)
    
    if not friendly_name:
        friendly_name = f"AgentX-{area}-{phone[-4:]}"
    
    # Build kwargs for validation_requests.create()
    kwargs = {
        "phone_number": phone,
        "friendly_name": friendly_name,
    }
    
    if extension:
        kwargs["extension"] = extension
    
    if call_delay > 0:
        kwargs["call_delay"] = call_delay
    
    if status_callback:
        kwargs["status_callback"] = status_callback
    
    try:
        validation = client.validation_requests.create(**kwargs)
        
        # Track this initiation
        _track_initiated(
            phone=phone,
            validation_code=validation.validation_code,
            call_sid=validation.call_sid,
            friendly_name=friendly_name,
        )
        
        return {
            "success": True,
            "phone": phone,
            "validation_code": validation.validation_code,
            "call_sid": validation.call_sid,
            "friendly_name": friendly_name,
            "message": f"Twilio is calling {phone} from +14157234000. Enter code: {validation.validation_code}"
        }
    except Exception as e:
        error_code = getattr(e, 'code', None)
        error_msg = str(e)
        
        _track_failed(phone, error_msg[:200])
        
        return {
            "success": False,
            "phone": phone,
            "error_code": error_code,
            "error_message": error_msg[:300],
        }


def remove_caller_id(phone: str) -> Dict:
    """
    Remove a verified caller ID from the account.
    
    Uses: client.outgoing_caller_ids(sid).delete()
    """
    _validate_creds()
    client = _get_client()
    
    phone = _normalize_phone(phone)
    
    # Find the SID for this number
    verified = list_verified_caller_ids()
    target = None
    for v in verified:
        if v["phone_number"] == phone:
            target = v
            break
    
    if not target:
        return {
            "success": False,
            "phone": phone,
            "error": f"Number {phone} not found in verified caller IDs"
        }
    
    sid = target["sid"]
    try:
        client.outgoing_caller_ids(sid).delete()
        return {
            "success": True,
            "phone": phone,
            "sid": sid,
            "message": f"Removed {phone} (SID: {sid}) from verified caller IDs"
        }
    except Exception as e:
        return {
            "success": False,
            "phone": phone,
            "error": str(e)[:300]
        }


def check_caller_id(phone: str) -> Dict:
    """
    Check if a specific number is verified on the account.
    Also reconciles with the local tracker.
    """
    _validate_creds()
    
    phone = _normalize_phone(phone)
    verified = list_verified_caller_ids()
    
    for v in verified:
        if v["phone_number"] == phone:
            # Reconcile tracker
            _track_verified(phone, v["sid"])
            return {
                "verified": True,
                "phone": phone,
                "friendly_name": v["friendly_name"],
                "sid": v["sid"],
                "date_created": v["date_created"],
            }
    
    return {
        "verified": False,
        "phone": phone,
        "message": f"{phone} is NOT verified on this Twilio account"
    }


def bulk_verify(file_path: str, delay_between: float = 30.0,
                status_callback: str = "") -> List[Dict]:
    """
    Verify a batch of numbers from a text file (one number per line).
    
    Each line can be:
      +13055551234
      +13055551234|Miami Line 1     (with friendly name after pipe)
      3055551234                     (auto-normalized to E.164)
    
    Twilio calls each number from +14157234000 with the OTP.
    This function prints the code for each number synchronously.
    
    Between each verification, waits delay_between seconds so the 
    person being verified can answer and enter the code.
    """
    _validate_creds()
    
    if not os.path.exists(file_path):
        print(f"\n  {FAIL} File not found: {file_path}\n")
        return []
    
    lines = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    
    if not lines:
        print(f"\n  {WARN} No phone numbers found in {file_path}\n")
        return []
    
    # Check which are already verified to skip them
    print(f"\n  {INFO} Pre-checking already-verified numbers...")
    already_verified = {v["phone_number"] for v in list_verified_caller_ids()}
    
    results = []
    total = len(lines)
    skipped = 0
    
    print(f"\n  {C.BOLD}BULK VERIFICATION: {total} numbers{C.RESET}")
    print(f"  Twilio calls each from +14157234000 (English)")
    print(f"  Delay between verifications: {delay_between}s")
    print(f"  {'='*60}\n")
    
    for i, line in enumerate(lines, 1):
        parts = line.split("|")
        phone = _normalize_phone(parts[0].strip())
        friendly = parts[1].strip() if len(parts) > 1 else ""
        
        # Skip already verified
        if phone in already_verified:
            print(f"  [{i}/{total}] {phone} — {OK} already verified, skipping")
            skipped += 1
            continue
        
        print(f"  [{i}/{total}] {phone}...", end=" ", flush=True)
        
        result = add_caller_id(phone, friendly_name=friendly, status_callback=status_callback)
        results.append(result)
        
        if result["success"]:
            code = result['validation_code']
            print(f"{OK} CODE: {C.BOLD}{C.YELLOW}{code}{C.RESET}")
            print(f"         → Twilio is calling from +14157234000")
            print(f"         → Answer and enter {code} on the keypad")
        else:
            print(f"{FAIL} {result.get('error_message', 'Unknown error')[:80]}")
        
        if i < total:
            remaining = total - i
            print(f"         Waiting {delay_between}s... ({remaining} remaining)\n")
            time.sleep(delay_between)
    
    # Summary
    initiated = sum(1 for r in results if r.get("success"))
    failed = sum(1 for r in results if not r.get("success"))
    
    print(f"\n  {'='*60}")
    print(f"  {C.BOLD}SUMMARY{C.RESET}")
    print(f"  {OK} Initiated:        {initiated}")
    print(f"  {INFO} Already verified: {skipped}")
    print(f"  {FAIL} Failed:           {failed}")
    print(f"  Total:              {total}")
    print(f"\n  {WARN} Numbers are verified ONLY after OTP code is entered.")
    print(f"  Run 'python verify_caller_ids.py status' to check progress.\n")
    
    return results


def reconcile_status():
    """
    Reconcile local tracker with Twilio's actual verified list.
    
    Checks each pending number to see if it's now verified on Twilio.
    Updates the tracker accordingly.
    """
    _validate_creds()
    
    tracker = _load_tracker()
    verified_on_twilio = {v["phone_number"]: v for v in list_verified_caller_ids()}
    
    newly_verified = []
    still_pending = []
    
    for phone, info in list(tracker.get("pending", {}).items()):
        if phone in verified_on_twilio:
            _track_verified(phone, verified_on_twilio[phone]["sid"])
            newly_verified.append(phone)
        else:
            still_pending.append(phone)
    
    return {
        "verified_on_twilio": len(verified_on_twilio),
        "newly_verified": newly_verified,
        "still_pending": still_pending,
        "previously_verified": len(tracker.get("verified", {})),
        "failed": len(tracker.get("failed", {})),
    }


def sync_to_number_pool():
    """
    Sync verified caller IDs into data/number_pool.json for use
    by the CRO LocalPresenceManager.
    
    Merges verified numbers with existing pool — won't overwrite
    existing stats or flags.
    """
    _validate_creds()
    
    verified = list_verified_caller_ids()
    if not verified:
        print(f"\n  {WARN} No verified caller IDs found on Twilio account.\n")
        return
    
    # Load existing pool
    pool = {"numbers": [], "config": {
        "max_calls_per_number_per_day": 80,
        "retire_after_total_calls": 600,
        "rotation_strategy": "area_code_match_first"
    }}
    
    if NUMBER_POOL_FILE.exists():
        try:
            with open(NUMBER_POOL_FILE, "r") as f:
                pool = json.load(f)
        except Exception:
            pass
    
    existing_numbers = {n["number"] for n in pool.get("numbers", [])}
    
    added = 0
    skipped = 0
    
    for v in verified:
        phone = v["phone_number"]
        if phone in existing_numbers:
            skipped += 1
            continue
        
        area = _extract_area_code(phone)
        pool["numbers"].append({
            "number": phone,
            "area_code": area,
            "region": v.get("friendly_name", f"Verified-{area}"),
            "calls_today": 0,
            "total_calls": 0,
            "flagged": False,
            "active": True,
            "verified": True,
            "twilio_sid": v.get("sid"),
            "added_at": datetime.now().isoformat(),
        })
        added += 1
    
    # Save
    NUMBER_POOL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NUMBER_POOL_FILE, "w") as f:
        json.dump(pool, f, indent=2)
    
    print(f"\n  {OK} Synced to {NUMBER_POOL_FILE}")
    print(f"     Added:   {added} new numbers")
    print(f"     Skipped: {skipped} (already in pool)")
    print(f"     Total:   {len(pool['numbers'])} numbers in pool\n")


# ══════════════════════════════════════════════════════════════════════
#  CLI INTERFACE
# ══════════════════════════════════════════════════════════════════════


def cmd_list(args):
    """List all verified caller IDs."""
    verified = list_verified_caller_ids()
    
    if not verified:
        print(f"\n  {WARN} No verified caller IDs on this account.\n")
        return
    
    print(f"\n  {C.BOLD}VERIFIED CALLER IDs ({len(verified)}){C.RESET}")
    print(f"  {'='*70}")
    print(f"  {'Phone':<18} {'Area':<6} {'Friendly Name':<25} {'Created'}")
    print(f"  {'-'*70}")
    
    for v in verified:
        phone = v["phone_number"]
        area = _extract_area_code(phone)
        name = (v["friendly_name"] or "")[:25]
        created = (v["date_created"] or "")[:20]
        print(f"  {phone:<18} {area:<6} {name:<25} {created}")
    
    print(f"  {'='*70}\n")


def cmd_add(args):
    """Add a phone number for verification."""
    phone = args.phone
    friendly = args.friendly or ""
    
    print(f"\n  {INFO} Initiating verification for {phone}...")
    print(f"     Twilio will call from +14157234000 (English)\n")
    
    # Build status callback if tunnel is available
    status_cb = ""
    tunnel_file = Path(__file__).parent / "active_tunnel_url.txt"
    if tunnel_file.exists():
        tunnel_url = tunnel_file.read_text().strip()
        if tunnel_url:
            # Ensure HTTPS
            tunnel_url = tunnel_url.replace("wss://", "https://").replace("ws://", "https://")
            if not tunnel_url.startswith("http"):
                tunnel_url = f"https://{tunnel_url}"
            status_cb = f"{tunnel_url}/verify-callback"
            print(f"  {INFO} Status callback: {status_cb}")
    
    result = add_caller_id(phone, friendly_name=friendly, status_callback=status_cb)
    
    if result["success"]:
        print(f"\n  {OK} Verification initiated!")
        print(f"     Phone:     {result['phone']}")
        print(f"     Name:      {result['friendly_name']}")
        print(f"     {C.BOLD}{C.YELLOW}CODE:      {result['validation_code']}{C.RESET}")
        print(f"     Call SID:  {result['call_sid']}")
        print(f"\n  {WARN} Twilio is calling {phone} NOW from +14157234000.")
        print(f"     Answer and enter the code above on the keypad.")
        print(f"     Then run: python verify_caller_ids.py check {phone}\n")
    else:
        print(f"\n  {FAIL} Verification failed!")
        print(f"     Phone:  {result['phone']}")
        print(f"     Error:  {result.get('error_message', 'Unknown')}")
        print(f"     Code:   {result.get('error_code', 'N/A')}\n")


def cmd_remove(args):
    """Remove a verified caller ID."""
    phone = args.phone
    
    print(f"\n  {INFO} Removing {phone} from verified caller IDs...")
    
    result = remove_caller_id(phone)
    
    if result["success"]:
        print(f"  {OK} {result['message']}\n")
    else:
        print(f"  {FAIL} {result.get('error', 'Unknown error')}\n")


def cmd_check(args):
    """Check if a number is verified."""
    phone = args.phone
    
    result = check_caller_id(phone)
    
    if result["verified"]:
        print(f"\n  {OK} {result['phone']} is VERIFIED")
        print(f"     Name:    {result['friendly_name']}")
        print(f"     SID:     {result['sid']}")
        print(f"     Since:   {result['date_created']}\n")
    else:
        print(f"\n  {FAIL} {result['phone']} is NOT verified on this account.\n")


def cmd_bulk(args):
    """Bulk verify numbers from a file."""
    file_path = args.file
    delay = args.delay or 30.0  # 30s default so person can answer each call
    
    # Build status callback if tunnel is available
    status_cb = ""
    tunnel_file = Path(__file__).parent / "active_tunnel_url.txt"
    if tunnel_file.exists():
        tunnel_url = tunnel_file.read_text().strip()
        if tunnel_url:
            tunnel_url = tunnel_url.replace("wss://", "https://").replace("ws://", "https://")
            if not tunnel_url.startswith("http"):
                tunnel_url = f"https://{tunnel_url}"
            status_cb = f"{tunnel_url}/verify-callback"
    
    bulk_verify(file_path, delay_between=delay, status_callback=status_cb)


def cmd_status(args):
    """Check verification status — reconcile tracker with Twilio."""
    print(f"\n  {INFO} Reconciling verification status with Twilio...\n")
    
    result = reconcile_status()
    tracker = _load_tracker()
    
    print(f"  {C.BOLD}VERIFICATION STATUS{C.RESET}")
    print(f"  {'='*60}")
    print(f"  Verified on Twilio:  {result['verified_on_twilio']}")
    print(f"  Newly confirmed:     {len(result['newly_verified'])}")
    print(f"  Still pending:       {len(result['still_pending'])}")
    print(f"  Previously tracked:  {result['previously_verified']}")
    print(f"  Failed:              {result['failed']}")
    
    if result['newly_verified']:
        print(f"\n  {OK} {C.BOLD}NEWLY VERIFIED:{C.RESET}")
        for phone in result['newly_verified']:
            print(f"     {OK} {phone}")
    
    if result['still_pending']:
        print(f"\n  {WARN} {C.BOLD}STILL PENDING (OTP not entered yet):{C.RESET}")
        for phone in result['still_pending']:
            info = tracker.get("pending", {}).get(phone, {})
            code = info.get("validation_code", "???")
            initiated = info.get("initiated_at", "")[:19]
            print(f"     {WARN} {phone}  CODE: {C.YELLOW}{code}{C.RESET}  (initiated: {initiated})")
        print(f"\n     To re-verify, run: python verify_caller_ids.py add <phone>")
    
    if tracker.get("failed"):
        print(f"\n  {FAIL} {C.BOLD}FAILED:{C.RESET}")
        for phone, info in tracker["failed"].items():
            reason = info.get("reason", "unknown")[:60]
            print(f"     {FAIL} {phone} — {reason}")
    
    print(f"  {'='*60}\n")


def cmd_sync(args):
    """Sync verified caller IDs to CRO number pool."""
    sync_to_number_pool()


def main():
    parser = argparse.ArgumentParser(
        description="Twilio Verified Caller ID Manager for Agent X (SDK-based, at-scale)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
How Verification Works:
  1. Run 'add' or 'bulk' — Twilio returns a 6-digit code synchronously
  2. Twilio calls the number from +14157234000 (English only)
  3. Answer the call, enter the 6-digit code on the keypad
  4. Number becomes a verified caller ID on your account
  5. Run 'sync' to push verified numbers to CRO local presence pool

Examples:
  python verify_caller_ids.py list
  python verify_caller_ids.py add +13055551234
  python verify_caller_ids.py add +13055551234 --friendly "Miami 1"
  python verify_caller_ids.py check +13055551234
  python verify_caller_ids.py remove +13055551234
  python verify_caller_ids.py bulk data/numbers_to_verify.txt --delay 45
  python verify_caller_ids.py status
  python verify_caller_ids.py sync
        """)
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # LIST
    list_parser = subparsers.add_parser("list", help="List all verified caller IDs")
    list_parser.set_defaults(func=cmd_list)
    
    # ADD
    add_parser = subparsers.add_parser("add", help="Add a phone number for verification")
    add_parser.add_argument("phone", help="Phone number to verify (E.164 or 10-digit)")
    add_parser.add_argument("--friendly", "-f", help="Friendly name label")
    add_parser.set_defaults(func=cmd_add)
    
    # REMOVE
    remove_parser = subparsers.add_parser("remove", help="Remove a verified caller ID")
    remove_parser.add_argument("phone", help="Phone number to remove")
    remove_parser.set_defaults(func=cmd_remove)
    
    # CHECK
    check_parser = subparsers.add_parser("check", help="Check if a number is verified")
    check_parser.add_argument("phone", help="Phone number to check")
    check_parser.set_defaults(func=cmd_check)
    
    # BULK
    bulk_parser = subparsers.add_parser("bulk", help="Bulk verify from file (one number per line)")
    bulk_parser.add_argument("file", help="Text file with one number per line (optionally: number|friendly_name)")
    bulk_parser.add_argument("--delay", "-d", type=float, default=30.0,
                            help="Seconds between verifications (default: 30 — enough time to answer)")
    bulk_parser.set_defaults(func=cmd_bulk)
    
    # STATUS
    status_parser = subparsers.add_parser("status", help="Check pending verification status")
    status_parser.set_defaults(func=cmd_status)
    
    # SYNC
    sync_parser = subparsers.add_parser("sync", help="Sync verified IDs to CRO number pool")
    sync_parser.set_defaults(func=cmd_sync)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)


if __name__ == "__main__":
    main()
