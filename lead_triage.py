"""
Lead Quality Triage Pipeline — Phase 3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pre-filters leads.json with heuristics before feeding to campaigns.
Assigns lead_quality_score (0.0-1.0) and only allows high-intent leads through.

Usage:
    python lead_triage.py                    # Analyze and score all leads
    python lead_triage.py --apply            # Actually mark low-quality leads as DNC
    python lead_triage.py --threshold 0.5    # Custom quality threshold
"""
import json
import re
import sqlite3
import sys
from datetime import datetime

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HARD REJECT PATTERNS — definitive non-business leads
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARD_REJECT_NAME_PATTERNS = [
    r'\bcalendar\b', r'\bevents?\s+(?:listing|schedule|guide)\b',
    r'\bpress\s+release\b', r'\bnews\s+(?:article|story|update)\b',
    r'\bopening\s+soon\b', r'\bdevelopment\b', r'\bannouncement\b',
    r'\b(?:new|notable)\s+(?:developments|openings|restaurants)\b',
    r'\bminneapolis\b.*\bopening\b', r'\brestaurant\s+opening\b',
    r'\b(?:top|best)\s+\d+\b',  # "Top 10 restaurants" — listicle
    r'\bguide\s+to\b', r'\bround-?up\b',
    r'\bformer\b.*\b(?:location|space|site)\b',  # "Motek to open at former Le Fig"
    r'\bprofile\s*:\b', r'\binterview\b',
    r'\bcity\s+(?:council|government|hall)\b',
    r'\bdepartment\s+of\b', r'\bcounty\s+(?:office|clerk|court)\b',
    r'\bstate\s+(?:agency|board|commission|department)\b',
    r'\bhospital\b', r'\bmedical\s+center\b', r'\bclinic\b',
    r'\bschool\b', r'\buniversity\b', r'\bcollege\b',
    r'\bchurch\b', r'\btemple\b', r'\bmosque\b',
    r'\bfire\s+(?:department|station)\b', r'\bpolice\b',
    r'\bnon-?profit\b', r'\bfoundation\b',
]

# Phone patterns that indicate non-callable numbers
PHONE_REJECT_PATTERNS = [
    r'^1?800',         # Toll-free 800
    r'^1?888',         # Toll-free 888
    r'^1?877',         # Toll-free 877
    r'^1?866',         # Toll-free 866
    r'^1?855',         # Toll-free 855
    r'^1?844',         # Toll-free 844
    r'^1?833',         # Toll-free 833
    r'^1?900',         # Premium rate
]

# URL patterns indicating non-business content
URL_SOFT_REJECT_PATTERNS = [
    r'/news/', r'/blog/', r'/press/', r'/events/',
    r'/article/', r'/story/', r'/listicle/',
    r'yelp\.com', r'tripadvisor\.com', r'google\.com/maps',
]

# Strong positive indicators for real, callable businesses
POSITIVE_INDICATORS = [
    r'\b(?:restaurant|cafe|bar|grill|pizz|bakery|deli|diner|bistro|kitchen)\b',
    r'\b(?:salon|barber|spa|beauty|nails|hair)\b',
    r'\b(?:auto|mechanic|tire|body\s+shop|repair)\b',
    r'\b(?:florist|flower|garden|nursery)\b',
    r'\b(?:retail|store|shop|boutique|market)\b',
    r'\b(?:gym|fitness|yoga|martial\s+arts)\b',
    r'\b(?:pet|vet|veterinar|grooming)\b',
    r'\b(?:hotel|motel|inn|lodge|resort)\b',
    r'\b(?:cleaners|laundry|dry\s+clean)\b',
    r'\b(?:dentist|dental|optometrist|chiropractic)\b',
]

# Compile all patterns
_hard_reject_compiled = [re.compile(p, re.I) for p in HARD_REJECT_NAME_PATTERNS]
_phone_reject_compiled = [re.compile(p) for p in PHONE_REJECT_PATTERNS]
_url_reject_compiled = [re.compile(p, re.I) for p in URL_SOFT_REJECT_PATTERNS]
_positive_compiled = [re.compile(p, re.I) for p in POSITIVE_INDICATORS]


def score_lead(lead: dict) -> dict:
    """
    Score a single lead for quality.
    
    Returns:
        {
            'lead_quality_score': float (0.0-1.0),
            'lead_type': str ('business', 'event_listing', 'news_article', 'directory', 'government', 'other'),
            'reject_reason': str or None,
            'callability': str ('high', 'medium', 'low'),
        }
    """
    name = str(lead.get('name', '') or lead.get('company', '') or '').strip()
    phone = str(lead.get('phone', '') or lead.get('phone_number', '') or '').strip()
    url = str(lead.get('url', '') or '').strip()
    category = str(lead.get('category', '') or lead.get('industry', '') or '').strip()
    source = str(lead.get('lead_source', '') or lead.get('source', '') or '').strip()
    
    score = 0.5  # Start neutral
    lead_type = 'other'
    reject_reason = None
    
    # ── HARD REJECTS ──
    
    # No phone number
    if not phone or len(phone) < 7:
        return {
            'lead_quality_score': 0.0,
            'lead_type': 'invalid',
            'reject_reason': 'no_phone_number',
            'callability': 'low',
        }
    
    # Toll-free / premium numbers
    clean_phone = re.sub(r'[^\d]', '', phone)
    for pat in _phone_reject_compiled:
        if pat.search(clean_phone):
            return {
                'lead_quality_score': 0.05,
                'lead_type': 'other',
                'reject_reason': f'toll_free_or_premium: {phone}',
                'callability': 'low',
            }
    
    # Name-based hard rejects
    for pat in _hard_reject_compiled:
        if pat.search(name):
            return {
                'lead_quality_score': 0.1,
                'lead_type': 'non_business',
                'reject_reason': f'name_pattern: {pat.pattern}',
                'callability': 'low',
            }
    
    # ── SOFT SCORING ──
    
    # URL quality check
    if url:
        for pat in _url_reject_compiled:
            if pat.search(url):
                score -= 0.2
                lead_type = 'directory'
                break
    
    # Positive business name indicators
    positive_match = False
    for pat in _positive_compiled:
        if pat.search(name) or pat.search(category):
            score += 0.25
            lead_type = 'business'
            positive_match = True
            break
    
    # Name length heuristic — very short names (e.g. "ABC") are often bad
    if len(name) < 3:
        score -= 0.15
    elif len(name) > 50:
        # Very long names are often articles/listings
        score -= 0.1
    
    # Has category/industry? Good signal
    if category and category not in ('Unknown', 'unknown', ''):
        score += 0.1
    
    # Has monthly volume? Great signal — likely a real business lead
    if lead.get('monthly_volume'):
        try:
            vol = float(lead['monthly_volume'])
            if vol > 0:
                score += 0.15
                lead_type = 'business'
        except (ValueError, TypeError):
            pass
    
    # Source quality
    high_quality_sources = {'manual', 'referral', 'gemini', 'intent', 'google_maps'}
    low_quality_sources = {'scraped', 'crawled', 'bulk', 'unknown'}
    if source.lower() in high_quality_sources:
        score += 0.1
    elif source.lower() in low_quality_sources:
        score -= 0.1
    
    # Clamp
    score = max(0.0, min(1.0, score))
    
    # Callability classification
    if score >= 0.7:
        callability = 'high'
    elif score >= 0.4:
        callability = 'medium'
    else:
        callability = 'low'
    
    return {
        'lead_quality_score': round(score, 3),
        'lead_type': lead_type,
        'reject_reason': reject_reason,
        'callability': callability,
    }


def triage_database(db_path='data/leads.db', threshold=0.4, apply=False):
    """
    Score all leads in the database and optionally mark low-quality as do_not_call.
    
    Args:
        db_path: Path to leads SQLite database
        threshold: Minimum quality score to keep (default 0.4)
        apply: If True, actually update the database
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    leads = conn.execute('''SELECT id, phone_number, name, business_type, lead_source, 
                            monthly_volume, do_not_call, outcome, attempts
                            FROM leads''').fetchall()
    
    results = {
        'total': len(leads),
        'high': 0,
        'medium': 0, 
        'low': 0,
        'rejected': [],
        'kept': 0,
    }
    
    for lead in leads:
        lead_dict = {
            'name': lead['name'],
            'phone_number': lead['phone_number'],
            'industry': lead['business_type'],
            'lead_source': lead['lead_source'],
            'monthly_volume': lead['monthly_volume'],
        }
        
        score_result = score_lead(lead_dict)
        quality = score_result['lead_quality_score']
        
        if quality < threshold and lead['do_not_call'] == 0:
            results['rejected'].append({
                'name': lead['name'],
                'phone': lead['phone_number'],
                'score': quality,
                'reason': score_result['reject_reason'] or score_result['lead_type'],
                'attempts': lead['attempts'],
                'outcome': lead['outcome'],
            })
            results['low'] += 1
            
            if apply:
                conn.execute(
                    'UPDATE leads SET do_not_call = 1, notes = ? WHERE id = ?',
                    (json.dumps([f'triage_rejected: score={quality:.3f}, reason={score_result["reject_reason"] or score_result["lead_type"]}']), lead['id'])
                )
        elif quality >= 0.7:
            results['high'] += 1
            results['kept'] += 1
        else:
            results['medium'] += 1
            results['kept'] += 1
    
    if apply:
        conn.commit()
    
    conn.close()
    return results


def triage_json(json_path='data/leads.json', threshold=0.4):
    """Score all leads in a JSON file and return filtered results."""
    with open(json_path) as f:
        leads = json.load(f)
    
    scored = []
    for lead in leads:
        result = score_lead(lead)
        lead['_quality_score'] = result['lead_quality_score']
        lead['_lead_type'] = result['lead_type']
        lead['_callability'] = result['callability']
        lead['_reject_reason'] = result['reject_reason']
        scored.append(lead)
    
    high = [l for l in scored if l['_quality_score'] >= 0.7]
    medium = [l for l in scored if 0.4 <= l['_quality_score'] < 0.7]
    low = [l for l in scored if l['_quality_score'] < threshold]
    
    return {
        'total': len(scored),
        'high_quality': len(high),
        'medium_quality': len(medium),
        'low_quality': len(low),
        'threshold': threshold,
        'scored_leads': scored,
    }


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    threshold = 0.4
    for i, arg in enumerate(sys.argv):
        if arg == '--threshold' and i + 1 < len(sys.argv):
            threshold = float(sys.argv[i + 1])
    
    print("=" * 60)
    print("LEAD QUALITY TRIAGE PIPELINE")
    print(f"Threshold: {threshold}  |  Mode: {'APPLY' if apply else 'DRY RUN'}")
    print("=" * 60)
    
    # Triage database
    print("\n--- Database Leads (data/leads.db) ---")
    db_results = triage_database(threshold=threshold, apply=apply)
    print(f"Total: {db_results['total']}")
    print(f"High quality (≥0.7): {db_results['high']}")
    print(f"Medium quality (0.4-0.7): {db_results['medium']}")
    print(f"Low quality (<{threshold}): {db_results['low']}")
    print(f"Kept: {db_results['kept']}")
    
    if db_results['rejected']:
        print(f"\nRejected leads ({len(db_results['rejected'])}):")
        for r in db_results['rejected'][:20]:
            print(f"  {r['score']:.2f} | {r['name'][:35]:35s} | {r['reason']}")
        if len(db_results['rejected']) > 20:
            print(f"  ... and {len(db_results['rejected']) - 20} more")
    
    if apply:
        print(f"\n✓ {db_results['low']} leads marked as do_not_call in database")
    else:
        print(f"\nDry run complete. Use --apply to mark {db_results['low']} leads as do_not_call")
    
    # Also triage JSON if it exists
    try:
        print("\n--- JSON Leads (data/leads.json) ---")
        json_results = triage_json(threshold=threshold)
        print(f"Total: {json_results['total']}")
        print(f"High quality: {json_results['high_quality']}")
        print(f"Medium quality: {json_results['medium_quality']}")
        print(f"Low quality: {json_results['low_quality']}")
    except FileNotFoundError:
        print("data/leads.json not found — skipping")
    
    print("\n" + "=" * 60)
    print("TRIAGE COMPLETE")
    print("=" * 60)
