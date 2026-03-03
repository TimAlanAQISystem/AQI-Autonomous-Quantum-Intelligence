"""
Inbound Call Filter
===================
Filters inbound spam calls — particularly the "there" callbacks that pollute
CDC metrics and waste system resources.

The "there" pattern: When Alan calls a merchant and the merchant's caller ID
shows the Twilio number, some merchants call back. The /call endpoint defaults
merchant_name to "there" for unknown callers. These inbound callbacks generate
0-turn hangups that inflate the failure rate.

Today's data: 11 inbound "there" calls out of 98 total — 11% pure noise.

Wired into the relay server at WebSocket connect time to auto-abort
inbound spam before any processing occurs.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Known inbound spam patterns
INBOUND_SPAM_NAMES = {
    "there",        # Default merchant_name for unknown inbound
    "",             # Empty name
}

# Minimum name length to consider valid (filters garbage like "a", "x")
MIN_VALID_NAME_LENGTH = 3


def is_inbound_spam(call_context: dict) -> bool:
    """
    Check if an incoming call is likely inbound spam.
    
    Args:
        call_context: Dictionary with at least 'merchant_name' and optionally 'direction'
        
    Returns:
        True if this looks like inbound spam that should be auto-aborted
    """
    name = (call_context.get('merchant_name') or '').strip().lower()
    
    # Direction check (if available)
    direction = call_context.get('direction', '').lower()
    inbound = direction == 'inbound' or call_context.get('is_inbound', False)
    
    # "there" is only spam when inbound — outbound calls to "there" are a data issue
    if inbound and name in INBOUND_SPAM_NAMES:
        logger.warning(f"[INBOUND FILTER] Spam detected: merchant_name='{name}', direction={direction}")
        return True
    
    # Very short names on inbound = likely garbage
    if inbound and len(name) < MIN_VALID_NAME_LENGTH and name not in ('', 'there'):
        logger.info(f"[INBOUND FILTER] Suspicious short name on inbound: '{name}'")
        return True
    
    return False


def classify_inbound(call_context: dict) -> Optional[str]:
    """
    Classify an inbound call for CDC logging.
    
    Returns:
        None if not spam, or a classification string like "there_inbound"
    """
    name = (call_context.get('merchant_name') or '').strip().lower()
    direction = call_context.get('direction', '').lower()
    inbound = direction == 'inbound' or call_context.get('is_inbound', False)
    
    if not inbound:
        return None
    
    if name == 'there' or name == '':
        return 'there_inbound'
    
    if len(name) < MIN_VALID_NAME_LENGTH:
        return 'short_name_inbound'
    
    return None
