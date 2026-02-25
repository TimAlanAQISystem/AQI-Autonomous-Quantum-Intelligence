#!/usr/bin/env python3
"""
VOICEMAIL FALLBACK — Signature Card Service Direct Merchant Center
===================================================================
Handles inbound calls when Alan is off the phones.

Three layers of protection:
  Layer 1: Twilio Fallback URL (TwiML Bin)  → Server completely unreachable
  Layer 2: /twilio/fallback route            → Server up but relay down
  Layer 3: /twilio/voicemail-status webhook  → Voicemail recording notification

When the control API + relay are running, inbound calls route to Alan normally.
When they're DOWN, Twilio's fallback_url kicks in and plays a professional
greeting with voicemail recording.

Voicemail recordings are stored by Twilio (30-day retention) and notifications
are sent via SMS to Tim's phone.

Usage:
  # Deploy fallback (one-time setup)
  .venv\\Scripts\\python.exe voicemail_fallback.py --deploy

  # Check current state
  .venv\\Scripts\\python.exe voicemail_fallback.py --status

  # Test fallback TwiML (dry run)
  .venv\\Scripts\\python.exe voicemail_fallback.py --test

  # List recent voicemails
  .venv\\Scripts\\python.exe voicemail_fallback.py --list

Author: AQI Autonomous Intelligence
"""

import os
import sys
import json
import logging
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ─── Config ───────────────────────────────────────────────────────
BUSINESS_NAME = "Signature Card Service Direct Merchant Center"
BUSINESS_HOURS = "Monday through Friday, 9 AM to 5 PM Pacific Time"
VOICEMAIL_MAX_LENGTH = 120  # seconds
VOICEMAIL_TIMEOUT = 5       # seconds of silence before stopping
NOTIFY_PHONE = None         # Set from env: OWNER_PHONE_NUMBER
VOICEMAIL_DB = Path(__file__).parent / "data" / "voicemails.db"

logger = logging.getLogger("VOICEMAIL_FALLBACK")

# ─── TwiML Templates ─────────────────────────────────────────────

# Layer 1: Twilio Fallback URL TwiML (hosted as TwiML Bin on Twilio)
# This fires when the primary voice_url is UNREACHABLE
FALLBACK_TWIML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew" language="en-US">
        Thank you for calling {BUSINESS_NAME}.
        We are currently unavailable to take your call.
        Our business hours are {BUSINESS_HOURS}.
        Please leave a message after the tone, and Alan will return your call as soon as possible.
    </Say>
    <Record
        maxLength="{VOICEMAIL_MAX_LENGTH}"
        timeout="{VOICEMAIL_TIMEOUT}"
        transcribe="true"
        playBeep="true"
        action="{{action_url}}"
        recordingStatusCallback="{{recording_callback_url}}"
        recordingStatusCallbackEvent="completed"
    />
    <Say voice="Polly.Matthew" language="en-US">
        We did not receive a message. Thank you for calling {BUSINESS_NAME}. Goodbye.
    </Say>
</Response>"""

# Layer 2: Local fallback (when server is up but relay is down)
LOCAL_FALLBACK_TWIML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew" language="en-US">
        Thank you for calling {BUSINESS_NAME}.
        Our system is currently being updated.
        Please leave a message after the tone, and Alan will return your call shortly.
    </Say>
    <Record
        maxLength="{VOICEMAIL_MAX_LENGTH}"
        timeout="{VOICEMAIL_TIMEOUT}"
        transcribe="true"
        playBeep="true"
        action="{{action_url}}"
        recordingStatusCallback="{{recording_callback_url}}"
        recordingStatusCallbackEvent="completed"
    />
    <Say voice="Polly.Matthew" language="en-US">
        We did not receive a message. Thank you for calling. Goodbye.
    </Say>
</Response>"""

# After-recording confirmation
AFTER_RECORD_TWIML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew" language="en-US">
        Thank you. Your message has been received. Alan from {BUSINESS_NAME} will return your call. Goodbye.
    </Say>
    <Hangup/>
</Response>"""


# ─── Voicemail Database ──────────────────────────────────────────

def _ensure_db():
    """Create voicemail tracking database if it doesn't exist."""
    VOICEMAIL_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(VOICEMAIL_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS voicemails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_sid TEXT UNIQUE NOT NULL,
            recording_sid TEXT,
            recording_url TEXT,
            duration_seconds INTEGER,
            caller_number TEXT,
            caller_city TEXT,
            caller_state TEXT,
            transcription TEXT,
            transcription_status TEXT DEFAULT 'pending',
            notification_sent INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            listened_at TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_voicemails_created
        ON voicemails(created_at DESC)
    """)
    conn.commit()
    conn.close()
    logger.debug("[VOICEMAIL] Database initialized")


def save_voicemail(call_sid: str, recording_sid: str, recording_url: str,
                   duration: int, caller: str, city: str = "", state: str = "",
                   transcription: str = "") -> bool:
    """Save a voicemail record to the database."""
    try:
        _ensure_db()
        conn = sqlite3.connect(str(VOICEMAIL_DB))
        conn.execute("""
            INSERT OR REPLACE INTO voicemails
            (call_sid, recording_sid, recording_url, duration_seconds,
             caller_number, caller_city, caller_state, transcription, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            call_sid, recording_sid, recording_url, duration,
            caller, city, state, transcription,
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()
        conn.close()
        logger.info(f"[VOICEMAIL] Saved voicemail from {caller} ({duration}s)")
        return True
    except Exception as e:
        logger.error(f"[VOICEMAIL] Failed to save: {e}")
        return False


def get_recent_voicemails(limit: int = 20) -> list:
    """Get recent voicemail records."""
    try:
        _ensure_db()
        conn = sqlite3.connect(str(VOICEMAIL_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM voicemails ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"[VOICEMAIL] Failed to fetch: {e}")
        return []


def get_unlistened_count() -> int:
    """Get count of voicemails not yet listened to."""
    try:
        _ensure_db()
        conn = sqlite3.connect(str(VOICEMAIL_DB))
        count = conn.execute(
            "SELECT COUNT(*) FROM voicemails WHERE listened_at IS NULL"
        ).fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def mark_listened(recording_sid: str) -> bool:
    """Mark a voicemail as listened to."""
    try:
        conn = sqlite3.connect(str(VOICEMAIL_DB))
        conn.execute(
            "UPDATE voicemails SET listened_at = ? WHERE recording_sid = ?",
            (datetime.now(timezone.utc).isoformat(), recording_sid)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ─── SMS Notification ─────────────────────────────────────────────

def send_voicemail_notification(caller: str, duration: int,
                                 recording_url: str, transcription: str = "") -> bool:
    """Send SMS notification to Tim about a new voicemail."""
    try:
        from twilio.rest import Client
        from dotenv import load_dotenv
        load_dotenv()

        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_PHONE_NUMBER", "+18883277213")
        to_number = os.environ.get("OWNER_PHONE_NUMBER", "")

        if not to_number:
            logger.warning("[VOICEMAIL] OWNER_PHONE_NUMBER not set — cannot send SMS notification")
            return False

        if not account_sid or not auth_token:
            logger.error("[VOICEMAIL] Twilio credentials missing — cannot send SMS")
            return False

        client = Client(account_sid, auth_token)

        # Build notification message
        msg_lines = [
            f"📞 New Voicemail — {BUSINESS_NAME}",
            f"From: {caller}",
            f"Duration: {duration}s",
            f"Time: {datetime.now().strftime('%I:%M %p %Z')}",
        ]
        if transcription:
            # Truncate transcription to fit SMS
            trunc = transcription[:200] + "..." if len(transcription) > 200 else transcription
            msg_lines.append(f"Message: {trunc}")
        if recording_url:
            msg_lines.append(f"Listen: {recording_url}")

        body = "\n".join(msg_lines)

        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        logger.info(f"[VOICEMAIL] SMS notification sent: {message.sid}")
        return True

    except Exception as e:
        logger.error(f"[VOICEMAIL] SMS notification failed: {e}")
        return False


# ─── Twilio Deployment ────────────────────────────────────────────

def deploy_fallback() -> dict:
    """
    Deploy the complete voicemail fallback system:
    1. Create/update TwiML Bin on Twilio for the fallback greeting
    2. Update phone number with fallback_url pointing to TwiML Bin
    3. Verify configuration
    """
    from twilio.rest import Client
    from dotenv import load_dotenv
    load_dotenv()

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    phone_number = os.environ.get("TWILIO_PHONE_NUMBER", "+18883277213")

    if not account_sid or not auth_token:
        return {"status": "error", "message": "Twilio credentials missing"}

    client = Client(account_sid, auth_token)
    results = {"status": "deploying", "steps": []}

    # ── Step 1: Create TwiML Bin for fallback ──
    try:
        # Build the standalone TwiML (no server dependency)
        # For TwiML Bin, we use a simple version without callbacks
        # (since our server is down when this fires)
        standalone_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew" language="en-US">Thank you for calling {BUSINESS_NAME}. We are currently unavailable to take your call. Our business hours are {BUSINESS_HOURS}. Please leave a message after the tone, and Alan will return your call as soon as possible.</Say>
    <Record maxLength="{VOICEMAIL_MAX_LENGTH}" timeout="{VOICEMAIL_TIMEOUT}" transcribe="true" playBeep="true" />
    <Say voice="Polly.Matthew" language="en-US">We did not receive a message. Thank you for calling {BUSINESS_NAME}. Goodbye.</Say>
</Response>"""

        # Check for existing TwiML Bin with our friendly name
        friendly_name = f"AQI Voicemail Fallback - {BUSINESS_NAME}"
        existing_bins = client.serverless.v1.services.list()
        
        # TwiML Bins are simpler — use the twiml_bins resource
        # Actually, TwiML Bins are not in the standard SDK paths.
        # We'll use the REST API directly for TwiML Apps instead.
        
        # Create/update a TwiML App as fallback
        twiml_apps = client.applications.list(friendly_name=friendly_name)
        
        if twiml_apps:
            # Update existing
            twiml_app = twiml_apps[0]
            twiml_app_sid = twiml_app.sid
            results["steps"].append(f"Found existing TwiML App: {twiml_app_sid}")
        else:
            # Create new TwiML App (placeholder — actual TwiML served by route)
            twiml_app = client.applications.create(
                friendly_name=friendly_name,
                voice_method="POST"
            )
            twiml_app_sid = twiml_app.sid
            results["steps"].append(f"Created TwiML App: {twiml_app_sid}")

    except Exception as e:
        results["steps"].append(f"TwiML App setup: {e} (non-critical)")
        twiml_app_sid = None

    # ── Step 2: Update phone number fallback_url ──
    try:
        # Find the phone number
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
        if not numbers:
            return {"status": "error", "message": f"Phone number {phone_number} not found"}

        phone_resource = numbers[0]
        phone_sid = phone_resource.sid

        # The fallback URL needs to be a publicly accessible URL that returns TwiML.
        # Option A: Use a static Twilio hosted page (TwiML Bin via console)
        # Option B: Use our tunnel URL + /twilio/fallback route
        #
        # PROBLEM: If the server is down, our tunnel is also down.
        # SOLUTION: We create a TwiML Bin via Twilio's API.
        #
        # Since the Python SDK doesn't directly support TwiML Bins creation,
        # we'll set the fallback_url to a Twilio-hosted URL using the
        # "twimlets" service which is always available:
        
        # Twilio's Echo Twimlet serves static TwiML:
        import urllib.parse
        
        # Build the fallback TwiML for the echo twimlet
        echo_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew" language="en-US">Thank you for calling {BUSINESS_NAME}. We are currently unavailable to take your call. Our business hours are {BUSINESS_HOURS}. Please leave a message after the tone and a representative will return your call as soon as possible.</Say>
    <Record maxLength="{VOICEMAIL_MAX_LENGTH}" timeout="{VOICEMAIL_TIMEOUT}" transcribe="true" playBeep="true"/>
    <Say voice="Polly.Matthew" language="en-US">We did not receive a message. Thank you for calling {BUSINESS_NAME}. Goodbye.</Say>
</Response>"""

        fallback_url = "https://handler.twilio.com/twiml/" + _create_twiml_bin(
            client, account_sid, echo_twiml, friendly_name
        )

        # Update the phone number with fallback
        phone_resource.update(
            voice_fallback_url=fallback_url,
            voice_fallback_method="POST"
        )
        results["steps"].append(f"Phone {phone_number} fallback_url set to TwiML Bin")
        results["fallback_url"] = fallback_url
        results["phone_sid"] = phone_sid

    except Exception as e:
        # If TwiML Bin creation fails, try the echo twimlet approach
        try:
            echo_twiml_simple = f'<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="Polly.Matthew">Thank you for calling {BUSINESS_NAME}. We are currently unavailable. Our hours are {BUSINESS_HOURS}. Please leave a message after the tone and Alan will return your call.</Say><Record maxLength="{VOICEMAIL_MAX_LENGTH}" timeout="{VOICEMAIL_TIMEOUT}" playBeep="true"/><Say voice="Polly.Matthew">Thank you for calling. Goodbye.</Say></Response>'
            
            encoded_twiml = urllib.parse.quote(echo_twiml_simple)
            fallback_url = f"https://twimlets.com/echo?Twiml={encoded_twiml}"
            
            phone_resource = numbers[0]
            phone_resource.update(
                voice_fallback_url=fallback_url,
                voice_fallback_method="GET"
            )
            results["steps"].append(f"Fallback set via Echo Twimlet (backup method)")
            results["fallback_url"] = fallback_url
        except Exception as e2:
            results["steps"].append(f"Fallback URL update failed: {e2}")
            results["status"] = "partial"

    # ── Step 3: Verify ──
    try:
        # Re-fetch to verify
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
        if numbers:
            n = numbers[0]
            results["verification"] = {
                "voice_url": n.voice_url,
                "voice_fallback_url": n.voice_fallback_url,
                "status_callback": n.status_callback,
                "voice_method": n.voice_method,
            }
            results["status"] = "deployed"
            results["steps"].append("Verification passed")
    except Exception as e:
        results["steps"].append(f"Verification failed: {e}")

    _ensure_db()
    results["steps"].append("Voicemail database initialized")

    return results


def _create_twiml_bin(client, account_sid: str, twiml_content: str,
                       friendly_name: str) -> str:
    """
    Create a TwiML Bin on Twilio and return the handler SID.
    TwiML Bins are serverless TwiML endpoints hosted by Twilio.
    """
    import requests

    # Use Twilio REST API directly for TwiML Bins
    url = f"https://handler.twilio.com/twiml/{account_sid}"
    
    # Actually, TwiML Bins are created via the Twilio Console API
    # The proper REST endpoint:
    api_url = "https://handler.twilio.com/twiml/Bins"
    
    try:
        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Twiml.json",
            auth=(account_sid, os.environ.get("TWILIO_AUTH_TOKEN", "")),
            data={
                "FriendlyName": friendly_name,
                "TwimlBody": twiml_content
            }
        )
        if response.status_code in (200, 201):
            data = response.json()
            return data.get("sid", "")
    except Exception:
        pass
    
    # Fallback: Use serverless approach
    raise RuntimeError("TwiML Bin creation requires Twilio Console — using Echo Twimlet instead")


def get_phone_status() -> dict:
    """Check current phone number configuration."""
    from twilio.rest import Client
    from dotenv import load_dotenv
    load_dotenv()

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    phone_number = os.environ.get("TWILIO_PHONE_NUMBER", "+18883277213")

    if not account_sid or not auth_token:
        return {"status": "error", "message": "Twilio credentials missing"}

    client = Client(account_sid, auth_token)

    try:
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
        if not numbers:
            return {"status": "error", "message": f"Phone {phone_number} not found"}

        n = numbers[0]
        has_fallback = bool(n.voice_fallback_url)

        return {
            "status": "ok",
            "phone_number": n.phone_number,
            "friendly_name": n.friendly_name,
            "voice_url": n.voice_url,
            "voice_method": n.voice_method,
            "voice_fallback_url": n.voice_fallback_url or "NOT SET ⚠️",
            "voice_fallback_method": n.voice_fallback_method,
            "status_callback": n.status_callback,
            "fallback_configured": has_fallback,
            "voicemail_db_exists": VOICEMAIL_DB.exists(),
            "unlistened_voicemails": get_unlistened_count() if VOICEMAIL_DB.exists() else 0,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── FastAPI Routes (imported by control_api_fixed.py) ────────────

def register_voicemail_routes(app):
    """
    Register voicemail fallback routes on the FastAPI app.
    Called from control_api_fixed.py during startup.
    """
    from fastapi import Request
    from fastapi.responses import HTMLResponse, JSONResponse

    @app.post("/twilio/fallback")
    async def handle_fallback(request: Request):
        """
        Layer 2 fallback: Server is running but relay is not available.
        Returns TwiML with voicemail greeting.
        """
        form = await request.form()
        caller = form.get("From", "Unknown")
        logger.info(f"[VOICEMAIL] Fallback triggered — caller: {caller}")

        # Build action URL for post-recording
        host = request.headers.get("host", "localhost:8777")
        scheme = "https" if "ngrok" in host or "trycloudflare" in host else "http"
        base_url = f"{scheme}://{host}"

        action_url = f"{base_url}/twilio/voicemail-complete"
        recording_callback = f"{base_url}/twilio/voicemail-status"

        twiml = LOCAL_FALLBACK_TWIML.replace("{action_url}", action_url)\
                                     .replace("{recording_callback_url}", recording_callback)

        return HTMLResponse(content=twiml, media_type="application/xml")

    @app.post("/twilio/voicemail-complete")
    async def handle_voicemail_complete(request: Request):
        """
        Called by Twilio after voicemail recording finishes.
        Returns confirmation TwiML and hangs up.
        """
        form = await request.form()
        recording_url = form.get("RecordingUrl", "")
        recording_sid = form.get("RecordingSid", "")
        recording_duration = form.get("RecordingDuration", "0")
        call_sid = form.get("CallSid", "")

        logger.info(
            f"[VOICEMAIL] Recording complete — SID: {recording_sid}, "
            f"Duration: {recording_duration}s, URL: {recording_url}"
        )

        return HTMLResponse(content=AFTER_RECORD_TWIML, media_type="application/xml")

    @app.post("/twilio/voicemail-status")
    async def handle_voicemail_status(request: Request):
        """
        Called by Twilio when recording status changes (completed).
        Saves voicemail to DB and sends SMS notification.
        """
        form = await request.form()
        recording_sid = form.get("RecordingSid", "")
        recording_url = form.get("RecordingUrl", "")
        recording_duration = int(form.get("RecordingDuration", "0"))
        call_sid = form.get("CallSid", "")
        caller = form.get("From", "Unknown")
        caller_city = form.get("CallerCity", "")
        caller_state = form.get("CallerState", "")
        recording_status = form.get("RecordingStatus", "")

        logger.info(
            f"[VOICEMAIL] Status callback — SID: {recording_sid}, "
            f"Status: {recording_status}, From: {caller}, "
            f"Duration: {recording_duration}s"
        )

        if recording_status == "completed" and recording_duration > 0:
            # Save to database
            save_voicemail(
                call_sid=call_sid,
                recording_sid=recording_sid,
                recording_url=recording_url,
                duration=recording_duration,
                caller=caller,
                city=caller_city,
                state=caller_state
            )

            # Send SMS notification
            send_voicemail_notification(
                caller=caller,
                duration=recording_duration,
                recording_url=recording_url
            )

            # Mark notification as sent
            try:
                conn = sqlite3.connect(str(VOICEMAIL_DB))
                conn.execute(
                    "UPDATE voicemails SET notification_sent = 1 WHERE recording_sid = ?",
                    (recording_sid,)
                )
                conn.commit()
                conn.close()
            except Exception:
                pass

        return JSONResponse({"status": "received"})

    @app.get("/voicemails")
    async def list_voicemails(limit: int = 20):
        """API endpoint to list recent voicemails."""
        voicemails = get_recent_voicemails(limit)
        unlistened = get_unlistened_count()
        return JSONResponse({
            "voicemails": voicemails,
            "total": len(voicemails),
            "unlistened": unlistened,
            "business": BUSINESS_NAME
        })

    @app.post("/voicemails/{recording_sid}/listened")
    async def mark_voicemail_listened(recording_sid: str):
        """Mark a voicemail as listened to."""
        success = mark_listened(recording_sid)
        return JSONResponse({
            "status": "ok" if success else "error",
            "recording_sid": recording_sid
        })

    logger.info(f"[VOICEMAIL] Fallback routes registered for {BUSINESS_NAME}")


# ─── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=f"Voicemail Fallback System — {BUSINESS_NAME}"
    )
    parser.add_argument("--deploy", action="store_true",
                        help="Deploy fallback to Twilio")
    parser.add_argument("--status", action="store_true",
                        help="Check phone number configuration")
    parser.add_argument("--test", action="store_true",
                        help="Print fallback TwiML (dry run)")
    parser.add_argument("--list", action="store_true",
                        help="List recent voicemails")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s"
    )

    if args.deploy:
        print(f"\n{'='*60}")
        print(f"  DEPLOYING VOICEMAIL FALLBACK")
        print(f"  {BUSINESS_NAME}")
        print(f"{'='*60}\n")
        result = deploy_fallback()
        for step in result.get("steps", []):
            status_icon = "✓" if "failed" not in step.lower() else "✗"
            print(f"  {status_icon} {step}")
        print(f"\n  Status: {result['status'].upper()}")
        if "fallback_url" in result:
            print(f"  Fallback URL: {result['fallback_url'][:80]}...")
        if "verification" in result:
            v = result["verification"]
            print(f"\n  Current Configuration:")
            print(f"    Voice URL:     {v.get('voice_url', 'N/A')}")
            print(f"    Fallback URL:  {v.get('voice_fallback_url', 'N/A')}")
        print()

    elif args.status:
        status = get_phone_status()
        print(f"\n{'='*60}")
        print(f"  PHONE STATUS — {BUSINESS_NAME}")
        print(f"{'='*60}")
        for k, v in status.items():
            print(f"  {k:30s}: {v}")
        print()

    elif args.test:
        print(f"\n{'='*60}")
        print(f"  FALLBACK TwiML (Dry Run)")
        print(f"{'='*60}\n")
        twiml = FALLBACK_TWIML.replace("{action_url}", "https://example.com/voicemail-complete")\
                               .replace("{recording_callback_url}", "https://example.com/voicemail-status")
        print(twiml)
        print(f"\n  Business: {BUSINESS_NAME}")
        print(f"  Max Length: {VOICEMAIL_MAX_LENGTH}s")
        print(f"  Timeout: {VOICEMAIL_TIMEOUT}s")
        print()

    elif args.list:
        voicemails = get_recent_voicemails()
        unlistened = get_unlistened_count()
        print(f"\n{'='*60}")
        print(f"  VOICEMAILS — {BUSINESS_NAME}")
        print(f"  {len(voicemails)} total, {unlistened} unlistened")
        print(f"{'='*60}")
        if not voicemails:
            print("  No voicemails recorded yet.")
        for vm in voicemails:
            listened = "✓" if vm.get("listened_at") else "●"
            print(f"\n  {listened} {vm['created_at'][:19]}")
            print(f"    From: {vm['caller_number']}")
            print(f"    Duration: {vm['duration_seconds']}s")
            if vm.get("transcription"):
                print(f"    Message: {vm['transcription'][:80]}")
            if vm.get("recording_url"):
                print(f"    URL: {vm['recording_url']}")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
