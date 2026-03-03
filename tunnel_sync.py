#!/usr/bin/env python3
"""
TUNNEL SYNC — Automatic Tunnel URL Propagation
===============================================
When the Cloudflare tunnel restarts, this module:
1. Detects the new tunnel URL from active_tunnel_url.txt
2. Updates Twilio phone number voice webhooks
3. Updates .env PUBLIC_TUNNEL_URL
4. Logs the change

Can be used standalone or imported by control_api_fixed.py
"""

import os
import re
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("TUNNEL_SYNC")

BASE_DIR = Path(__file__).parent
TUNNEL_FILE = BASE_DIR / "active_tunnel_url.txt"
TUNNEL_FILE_FIXED = BASE_DIR / "active_tunnel_url_fixed.txt"
ENV_FILE = BASE_DIR / ".env"

_last_synced_url = None


def get_current_tunnel_url() -> str:
    """Read the current tunnel URL from active_tunnel_url.txt"""
    try:
        if TUNNEL_FILE.exists():
            content = TUNNEL_FILE.read_text().strip()
            # Normalize to https
            content = content.replace("wss://", "https://").replace("ws://", "https://")
            if not content.startswith("http"):
                content = f"https://{content}"
            return content
    except Exception as e:
        logger.error(f"Failed to read tunnel file: {e}")
    return ""


def update_twilio_webhooks(tunnel_url: str) -> bool:
    """Update all Twilio phone number voice webhooks to the new tunnel URL"""
    try:
        from twilio.rest import Client
        
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        
        if not account_sid or not auth_token:
            logger.error("[TUNNEL_SYNC] Twilio credentials not found in environment")
            return False
        
        client = Client(account_sid, auth_token)
        voice_url = f"{tunnel_url}/twilio/inbound"
        status_url = f"{tunnel_url}/twilio/events"
        
        numbers = client.incoming_phone_numbers.list()
        for num in numbers:
            num.update(
                voice_url=voice_url,
                voice_method="POST",
                status_callback=status_url,
                status_callback_method="POST"
            )
            logger.info(f"[TUNNEL_SYNC] Updated {num.phone_number} -> {voice_url}")
        
        return True
    except Exception as e:
        logger.error(f"[TUNNEL_SYNC] Failed to update Twilio webhooks: {e}")
        return False


def update_env_tunnel_url(tunnel_url: str) -> bool:
    """Update PUBLIC_TUNNEL_URL in .env file"""
    try:
        if not ENV_FILE.exists():
            return False
        
        content = ENV_FILE.read_text()
        
        # Replace existing PUBLIC_TUNNEL_URL line
        if "PUBLIC_TUNNEL_URL=" in content:
            content = re.sub(
                r'^PUBLIC_TUNNEL_URL=.*$',
                f'PUBLIC_TUNNEL_URL={tunnel_url}',
                content,
                flags=re.MULTILINE
            )
        else:
            content += f"\nPUBLIC_TUNNEL_URL={tunnel_url}\n"
        
        ENV_FILE.write_text(content)
        logger.info(f"[TUNNEL_SYNC] Updated .env PUBLIC_TUNNEL_URL -> {tunnel_url}")
        return True
    except Exception as e:
        logger.error(f"[TUNNEL_SYNC] Failed to update .env: {e}")
        return False


def sync_tunnel_files(tunnel_url: str):
    """Ensure both tunnel URL files match"""
    try:
        # Strip scheme for the file (code adds it back as needed)
        clean_url = tunnel_url.replace("https://", "").replace("http://", "")
        
        TUNNEL_FILE.write_text(clean_url)
        TUNNEL_FILE_FIXED.write_text(clean_url)
        logger.info(f"[TUNNEL_SYNC] Synced tunnel files -> {clean_url}")
    except Exception as e:
        logger.error(f"[TUNNEL_SYNC] Failed to sync tunnel files: {e}")


def full_sync(force: bool = False) -> dict:
    """
    Full tunnel synchronization:
    1. Read current tunnel URL
    2. Update Twilio webhooks
    3. Update .env
    4. Sync tunnel files
    
    Returns status dict.
    """
    global _last_synced_url
    
    tunnel_url = get_current_tunnel_url()
    if not tunnel_url:
        return {"status": "error", "message": "No tunnel URL found"}
    
    if tunnel_url == _last_synced_url and not force:
        return {"status": "no_change", "url": tunnel_url}
    
    logger.info(f"[TUNNEL_SYNC] Syncing tunnel URL: {tunnel_url}")
    
    results = {
        "status": "synced",
        "url": tunnel_url,
        "twilio_updated": update_twilio_webhooks(tunnel_url),
        "env_updated": update_env_tunnel_url(tunnel_url),
    }
    
    sync_tunnel_files(tunnel_url)
    _last_synced_url = tunnel_url
    
    logger.info(f"[TUNNEL_SYNC] Sync complete: {results}")
    return results


async def background_tunnel_monitor(check_interval: int = 60):
    """
    Background task that monitors for tunnel URL changes.
    Runs indefinitely, checking every `check_interval` seconds.
    """
    import asyncio
    
    logger.info(f"[TUNNEL_SYNC] Starting background monitor (every {check_interval}s)")
    
    while True:
        try:
            result = full_sync()
            if result["status"] == "synced":
                logger.info(f"[TUNNEL_SYNC] Auto-synced to: {result['url']}")
            
            # [CENTRAL HUB] Report tunnel state into supervisor
            try:
                from supervisor import AlanSupervisor
                sup = AlanSupervisor.get_instance()
                if sup:
                    sup.update_tunnel_state(
                        url=result.get("url"),
                        valid=result.get("status") in ("synced", "no_change"),
                        reachable="ok" if result.get("status") in ("synced", "no_change") else "unknown",
                    )
            except Exception:
                pass  # Supervisor not initialized yet — safe to skip
                
        except Exception as e:
            logger.error(f"[TUNNEL_SYNC] Monitor error: {e}")
        
        await asyncio.sleep(check_interval)


if __name__ == "__main__":
    # Standalone execution
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    print("=== TUNNEL SYNC ===")
    result = full_sync(force=True)
    print(f"Result: {result}")
