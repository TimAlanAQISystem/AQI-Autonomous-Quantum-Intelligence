import json
import os
import logging
from datetime import date
from voice_box import config

STATS_FILE = "data/daily_stats.json"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

def get_today_key():
    return date.today().isoformat()

def get_daily_stats():
    """Load stats for today, resetting if date changed."""
    today = get_today_key()
    default_stats = {
        "date": today,
        "new_leads_dialed": 0,
        "retry_leads_dialed": 0,
        "unique_leads_touched": 0,
        "transcripts_captured": 0,
        "contact_efficiency": None
    }

    if not os.path.exists(STATS_FILE):
        return default_stats

    try:
        with open(STATS_FILE, 'r') as f:
            stats = json.load(f)
        
        # Reset if date doesn't match
        if stats.get("date") != today:
            return default_stats
            
        return stats
    except Exception as e:
        logging.error(f"Failed to load stats: {e}")
        return default_stats

def save_daily_stats(stats):
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save stats: {e}")

def compute_cem(stats):
    leads = stats.get("unique_leads_touched", 0)
    transcripts = stats.get("transcripts_captured", 0)
    if transcripts == 0:
        return float("inf")
    return round(leads / transcripts, 2)

def increment_stat(field: str, amount: int = 1):
    stats = get_daily_stats()
    stats[field] = stats.get(field, 0) + amount
    
    # Auto-update CEM on relevant changes
    if field in ["unique_leads_touched", "transcripts_captured"]:
        stats["contact_efficiency"] = compute_cem(stats)
        
    save_daily_stats(stats)
    return stats

def has_budget_for_new_leads() -> bool:
    stats = get_daily_stats()
    return stats.get("new_leads_dialed", 0) < config.NEW_LEAD_DAILY_BUDGET

def has_budget_for_retry_leads() -> bool:
    stats = get_daily_stats()
    return stats.get("retry_leads_dialed", 0) < config.RETRY_LEAD_DAILY_BUDGET

def has_overall_budget() -> bool:
    stats = get_daily_stats()
    return stats.get("unique_leads_touched", 0) < config.DAILY_LEAD_BUDGET
