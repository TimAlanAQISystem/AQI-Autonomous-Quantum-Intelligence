"""
Performance Monitoring Utilities for Agent X
Created: February 5, 2026
Phase 1A: Session Persistence Performance Tracking

This module provides decorators and utilities for monitoring
performance of critical operations, especially persistence.
"""

import time
import logging
from functools import wraps
from typing import Callable, Dict, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Performance metrics storage
performance_metrics = {
    "session_saves": [],
    "session_loads": [],
    "session_recoveries": [],
    "conversation_saves": []
}

def timing_decorator(operation_name: str, warn_threshold_ms: float = 100):
    """
    Decorator to measure execution time of functions.
    
    Args:
        operation_name: Name of the operation being timed
        warn_threshold_ms: Log warning if execution exceeds this (milliseconds)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                
                # Log performance
                log_performance(operation_name, duration_ms, success, error)
                
                # Warn if slow
                if duration_ms > warn_threshold_ms:
                    logger.warning(
                        f"[PERFORMANCE] {operation_name} took {duration_ms:.2f}ms "
                        f"(threshold: {warn_threshold_ms}ms)"
                    )
            
            return result
        
        return wrapper
    return decorator

def log_performance(operation: str, duration_ms: float, success: bool, error: str = None):
    """
    Log performance metric.
    
    Args:
        operation: Operation name
        duration_ms: Duration in milliseconds
        success: Whether operation succeeded
        error: Error message if failed
    """
    metric = {
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "success": success,
        "timestamp": datetime.now().isoformat()
    }
    
    if error:
        metric["error"] = error
    
    # Store in appropriate bucket
    if "save_session" in operation:
        performance_metrics["session_saves"].append(metric)
        # Keep only last 100
        if len(performance_metrics["session_saves"]) > 100:
            performance_metrics["session_saves"].pop(0)
    
    elif "load_session" in operation:
        performance_metrics["session_loads"].append(metric)
        if len(performance_metrics["session_loads"]) > 100:
            performance_metrics["session_loads"].pop(0)
    
    elif "recover" in operation:
        performance_metrics["session_recoveries"].append(metric)
        if len(performance_metrics["session_recoveries"]) > 100:
            performance_metrics["session_recoveries"].pop(0)
    
    elif "conversation" in operation:
        performance_metrics["conversation_saves"].append(metric)
        if len(performance_metrics["conversation_saves"]) > 100:
            performance_metrics["conversation_saves"].pop(0)
    
    # Log to console for immediate visibility
    status = "✓" if success else "✗"
    logger.info(f"[PERF] {status} {operation}: {duration_ms:.2f}ms")

def get_performance_stats() -> Dict[str, Any]:
    """
    Get aggregated performance statistics.
    
    Returns:
        Dictionary with performance metrics
    """
    stats = {}
    
    for metric_type, metrics in performance_metrics.items():
        if not metrics:
            stats[metric_type] = {
                "count": 0,
                "avg_ms": 0,
                "min_ms": 0,
                "max_ms": 0,
                "success_rate": 0
            }
            continue
        
        durations = [m["duration_ms"] for m in metrics]
        successes = [m["success"] for m in metrics]
        
        stats[metric_type] = {
            "count": len(metrics),
            "avg_ms": round(sum(durations) / len(durations), 2),
            "min_ms": round(min(durations), 2),
            "max_ms": round(max(durations), 2),
            "success_rate": round(sum(successes) / len(successes) * 100, 2),
            "recent": metrics[-10:]  # Last 10 operations
        }
    
    return stats

def clear_performance_metrics():
    """Clear all performance metrics"""
    for key in performance_metrics:
        performance_metrics[key] = []
    logger.info("[PERF] Performance metrics cleared")

def export_performance_report(filepath: str = "performance_report.json"):
    """
    Export performance metrics to JSON file.
    
    Args:
        filepath: Path to save report
    """
    try:
        stats = get_performance_stats()
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"[PERF] Performance report exported to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to export performance report: {e}")
        return False

# Convenience decorators for common operations
def monitor_session_save(func: Callable) -> Callable:
    """Decorator specifically for session save operations"""
    return timing_decorator("save_session", warn_threshold_ms=50)(func)

def monitor_session_load(func: Callable) -> Callable:
    """Decorator specifically for session load operations"""
    return timing_decorator("load_session", warn_threshold_ms=50)(func)

def monitor_session_recovery(func: Callable) -> Callable:
    """Decorator specifically for session recovery operations"""
    return timing_decorator("recover_sessions", warn_threshold_ms=1000)(func)

def monitor_conversation_save(func: Callable) -> Callable:
    """Decorator specifically for conversation turn saves"""
    return timing_decorator("save_conversation_turn", warn_threshold_ms=30)(func)
