import budget_tracker
import logging

def get_cem() -> float:
    """
    Get Contact Efficiency Metric (Leads / Transcripts).
    Lower is better (fewer leads needed for one conversation).
    Returns float("inf") if no transcripts.
    """
    stats = budget_tracker.get_daily_stats()
    return budget_tracker.compute_cem(stats)

def get_cem_score() -> int:
    """
    Normalized CEM score (0-5). 
    Higher is better.
    Derived from CEM.
    """
    cem = get_cem()
    if cem == float("inf"):
        return 0
    if cem > 50: return 1
    if cem > 30: return 2
    if cem > 20: return 3
    if cem > 10: return 4
    return 5

def get_surplus_score() -> float:
    """
    Unified intelligence score (0-35).
    Currently a placeholder computation based on transcripts and efficiency.
    """
    stats = budget_tracker.get_daily_stats()
    transcripts = stats.get("transcripts_captured", 0)
    cem_score = get_cem_score()
    
    # Simple formula: Transcript Count + (CEM Score * 2)
    # This rewards both volume and efficiency.
    score = transcripts + (cem_score * 2)
    return min(score, 35)

def get_transcript_count() -> int:
    stats = budget_tracker.get_daily_stats()
    return stats.get("transcripts_captured", 0)

def get_hangup_density(window: int = 50) -> float:
    """
    Calculate hangups / calls over the last N calls.
    For now, returns a safe default or reads from a hypothetical stats file.
    In a real implementation, this would parse recent call outcomes.
    """
    # TODO: Implement log parsing or specific tracking for short-term hangup density.
    # For now, returning a low density to allow operation.
    return 0.1
