#!/usr/bin/env python3
"""
OPERATIONAL MAINTENANCE MODULE
==============================
Periodic health checks, memory management, log rotation, and cache cleanup.

Tim's Directive: "We need to know if there needs to be a cache dump, memory 
cleaning or anything at certain times to maintain operations throughout the day."

Usage:
    # Wire into server as background task
    from operational_maintenance import MaintenanceScheduler
    scheduler = MaintenanceScheduler()
    asyncio.create_task(scheduler.run())

    # Or run standalone health check
    python operational_maintenance.py
"""

import asyncio
import gc
import logging
import os
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ======================================================================
#  CONSTANTS
# ======================================================================

# Memory thresholds (percentage)
MEMORY_WARNING_PCT = 75      # Log warning
MEMORY_CRITICAL_PCT = 85     # Trigger aggressive cleanup
MEMORY_EMERGENCY_PCT = 92    # Emergency: force GC + clear caches

# Maintenance intervals (seconds)
GC_INTERVAL = 300            # Garbage collection every 5 minutes
HEALTH_CHECK_INTERVAL = 60   # Health check every 60 seconds
LOG_ROTATION_INTERVAL = 3600 # Check log sizes every hour
MEMORY_REPORT_INTERVAL = 300 # Memory stats every 5 minutes

# Log file size limits
MAX_LOG_FILE_SIZE_MB = 50    # Rotate logs larger than 50MB
MAX_LOG_FILES = 5            # Keep 5 rotated copies

# Stale data thresholds
MAX_EVOLUTION_LOG_LINES = 500      # Trim evolution_log.jsonl beyond this
MAX_CALL_TIMING_LOG_SIZE_MB = 25   # Rotate call_timing.log


def get_memory_usage() -> dict:
    """Get current process and system memory usage."""
    result = {"process_mb": 0, "system_pct": 0, "system_available_mb": 0}
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        mem_info = proc.memory_info()
        result["process_mb"] = round(mem_info.rss / (1024 * 1024), 1)
        
        sys_mem = psutil.virtual_memory()
        result["system_pct"] = sys_mem.percent
        result["system_available_mb"] = round(sys_mem.available / (1024 * 1024), 1)
        result["system_total_mb"] = round(sys_mem.total / (1024 * 1024), 1)
    except ImportError:
        # psutil not available — use gc stats only
        result["gc_note"] = "psutil not installed — limited memory info"
    return result


def run_garbage_collection() -> dict:
    """Force garbage collection and return stats."""
    gc.collect()
    gen0, gen1, gen2 = gc.get_count()
    return {
        "collected": True,
        "gen0": gen0,
        "gen1": gen1, 
        "gen2": gen2,
        "tracked_objects": len(gc.get_objects()),
        "timestamp": datetime.now().isoformat(),
    }


def rotate_log_file(filepath: str, max_size_mb: float = MAX_LOG_FILE_SIZE_MB, max_copies: int = MAX_LOG_FILES) -> bool:
    """Rotate a log file if it exceeds max_size_mb. Returns True if rotated."""
    path = Path(filepath)
    if not path.exists():
        return False
    
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb < max_size_mb:
        return False
    
    # Rotate: .log -> .log.1 -> .log.2 -> .log.3 -> .log.4 -> delete
    for i in range(max_copies, 1, -1):
        older = Path(f"{filepath}.{i-1}")
        newer = Path(f"{filepath}.{i}")
        if older.exists():
            if newer.exists():
                newer.unlink()
            older.rename(newer)
    
    # Current -> .1
    backup = Path(f"{filepath}.1")
    if backup.exists():
        backup.unlink()
    path.rename(backup)
    
    # Create fresh empty file
    path.touch()
    
    logger.info(f"[MAINTENANCE] Rotated log file: {filepath} ({size_mb:.1f}MB -> fresh)")
    return True


def trim_jsonl_file(filepath: str, max_lines: int = MAX_EVOLUTION_LOG_LINES) -> bool:
    """Trim a JSONL file to keep only the last max_lines entries."""
    path = Path(filepath)
    if not path.exists():
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) <= max_lines:
            return False
        
        # Keep only the last max_lines
        trimmed = lines[-max_lines:]
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(trimmed)
        
        removed = len(lines) - max_lines
        logger.info(f"[MAINTENANCE] Trimmed {filepath}: removed {removed} old entries, kept {max_lines}")
        return True
    except Exception as e:
        logger.warning(f"[MAINTENANCE] Failed to trim {filepath}: {e}")
        return False


class MaintenanceScheduler:
    """
    Background maintenance scheduler for continuous server operation.
    
    Schedule:
    - Every 60s:  Health check (memory, active calls, error rate)
    - Every 5min: Garbage collection + memory report
    - Every 1hr:  Log rotation + data file trimming
    
    Wired into the server as a background asyncio task.
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.start_time = datetime.now()
        self._last_gc = 0.0
        self._last_health = 0.0
        self._last_log_rotation = 0.0
        self._last_memory_report = 0.0
        self._gc_count = 0
        self._rotation_count = 0
        self._emergency_gc_count = 0
        self._server_ref = None  # Set externally to access active_conversations
        self.running = True
        logger.info("[MAINTENANCE] Scheduler initialized")
    
    def set_server_ref(self, server):
        """Set reference to the server instance for monitoring active calls."""
        self._server_ref = server
    
    async def run(self):
        """Main maintenance loop. Run as asyncio.create_task(scheduler.run())."""
        logger.info("[MAINTENANCE] Background scheduler STARTED")
        await asyncio.sleep(30.0)  # Let server fully start before first check
        
        while self.running:
            try:
                now = time.time()
                
                # ---------- Health Check (every 60s) ----------
                if now - self._last_health >= HEALTH_CHECK_INTERVAL:
                    self._last_health = now
                    await self._health_check()
                
                # ---------- GC + Memory Report (every 5min) ----------
                if now - self._last_gc >= GC_INTERVAL:
                    self._last_gc = now
                    self._run_gc_cycle()
                
                # ---------- Log Rotation (every 1hr) ----------
                if now - self._last_log_rotation >= LOG_ROTATION_INTERVAL:
                    self._last_log_rotation = now
                    self._rotate_logs()
                
                await asyncio.sleep(15.0)  # Check conditions every 15s
                
            except asyncio.CancelledError:
                logger.info("[MAINTENANCE] Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"[MAINTENANCE] Scheduler error: {e}")
                await asyncio.sleep(60.0)  # Back off on error
        
        logger.info("[MAINTENANCE] Scheduler STOPPED")
    
    async def _health_check(self):
        """Periodic health check."""
        mem = get_memory_usage()
        
        active_calls = 0
        if self._server_ref and hasattr(self._server_ref, 'active_conversations'):
            active_calls = len(self._server_ref.active_conversations)
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        uptime_str = str(timedelta(seconds=int(uptime)))
        
        sys_pct = mem.get("system_pct", 0)
        
        # Emergency memory handling
        if sys_pct >= MEMORY_EMERGENCY_PCT:
            self._emergency_gc_count += 1
            logger.warning(
                f"[MAINTENANCE] EMERGENCY — System memory {sys_pct}% (>{MEMORY_EMERGENCY_PCT}%). "
                f"Process: {mem.get('process_mb', '?')}MB. "
                f"Emergency GC #{self._emergency_gc_count}. Active calls: {active_calls}"
            )
            # Aggressive GC
            gc.collect(2)
            gc.collect(1)
            gc.collect(0)
        elif sys_pct >= MEMORY_CRITICAL_PCT:
            logger.warning(
                f"[MAINTENANCE] CRITICAL — System memory {sys_pct}% (>{MEMORY_CRITICAL_PCT}%). "
                f"Process: {mem.get('process_mb', '?')}MB. Active calls: {active_calls}"
            )
            gc.collect()
        elif sys_pct >= MEMORY_WARNING_PCT:
            logger.info(
                f"[MAINTENANCE] WARNING — System memory {sys_pct}%. "
                f"Process: {mem.get('process_mb', '?')}MB. Active calls: {active_calls}"
            )
        else:
            # Normal — log at DEBUG level only
            logger.debug(
                f"[MAINTENANCE] OK — Memory: {sys_pct}%, Process: {mem.get('process_mb', '?')}MB, "
                f"Active calls: {active_calls}, Uptime: {uptime_str}"
            )
    
    def _run_gc_cycle(self):
        """Run scheduled garbage collection."""
        self._gc_count += 1
        stats = run_garbage_collection()
        
        if self._gc_count % 12 == 0:  # Log every hour (12 * 5min = 60min)
            mem = get_memory_usage()
            logger.info(
                f"[MAINTENANCE] GC cycle #{self._gc_count} — "
                f"Memory: {mem.get('system_pct', '?')}%, "
                f"Process: {mem.get('process_mb', '?')}MB, "
                f"Tracked objects: {stats['tracked_objects']}"
            )
    
    def _rotate_logs(self):
        """Check and rotate log files."""
        log_dir = os.path.join(self.base_dir, "logs")
        
        # Rotate call_timing.log
        call_log = os.path.join(log_dir, "call_timing.log")
        if rotate_log_file(call_log, MAX_CALL_TIMING_LOG_SIZE_MB):
            self._rotation_count += 1
        
        # Rotate any other large log files in the logs directory
        if os.path.isdir(log_dir):
            for fname in os.listdir(log_dir):
                fpath = os.path.join(log_dir, fname)
                if fname.endswith('.log') and os.path.isfile(fpath):
                    if rotate_log_file(fpath, MAX_LOG_FILE_SIZE_MB):
                        self._rotation_count += 1
        
        # Trim evolution_log.jsonl
        evo_log = os.path.join(self.base_dir, "evolution_log.jsonl")
        trim_jsonl_file(evo_log, MAX_EVOLUTION_LOG_LINES)
    
    def get_status(self) -> dict:
        """Get maintenance scheduler status for health endpoints."""
        mem = get_memory_usage()
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            "running": self.running,
            "uptime": str(timedelta(seconds=int(uptime))),
            "gc_cycles": self._gc_count,
            "log_rotations": self._rotation_count,
            "emergency_gcs": self._emergency_gc_count,
            "memory": mem,
            "gc_stats": {
                "gen0": gc.get_count()[0],
                "gen1": gc.get_count()[1],
                "gen2": gc.get_count()[2],
            }
        }
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False


# ======================================================================
#  STANDALONE HEALTH CHECK
# ======================================================================

def run_health_check():
    """Run a one-time health check and print results."""
    print("=" * 60)
    print("  ALAN OPERATIONAL HEALTH CHECK")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Memory
    print("\n[1] MEMORY STATUS")
    mem = get_memory_usage()
    sys_pct = mem.get("system_pct", 0)
    status = "OK" if sys_pct < MEMORY_WARNING_PCT else "WARNING" if sys_pct < MEMORY_CRITICAL_PCT else "CRITICAL"
    print(f"  System: {sys_pct}% used ({status})")
    print(f"  Available: {mem.get('system_available_mb', '?')}MB / {mem.get('system_total_mb', '?')}MB")
    print(f"  This process: {mem.get('process_mb', '?')}MB RSS")
    
    # 2. GC Stats
    print("\n[2] GARBAGE COLLECTOR")
    gc_stats = run_garbage_collection()
    print(f"  Tracked objects: {gc_stats['tracked_objects']}")
    print(f"  Generations: {gc_stats['gen0']} / {gc_stats['gen1']} / {gc_stats['gen2']}")
    
    # 3. Log File Sizes
    print("\n[3] LOG FILES")
    log_dir = os.path.join(base_dir, "logs")
    if os.path.isdir(log_dir):
        for fname in sorted(os.listdir(log_dir)):
            fpath = os.path.join(log_dir, fname)
            if os.path.isfile(fpath):
                size_mb = os.path.getsize(fpath) / (1024 * 1024)
                flag = " [NEEDS ROTATION]" if size_mb > MAX_LOG_FILE_SIZE_MB else ""
                print(f"  {fname}: {size_mb:.1f}MB{flag}")
    else:
        print("  No logs directory found")
    
    # 4. Data Files
    print("\n[4] DATA FILES")
    evo_log = os.path.join(base_dir, "evolution_log.jsonl")
    if os.path.exists(evo_log):
        with open(evo_log, 'r') as f:
            lines = f.readlines()
        print(f"  evolution_log.jsonl: {len(lines)} entries ({os.path.getsize(evo_log) / 1024:.1f}KB)")
        if len(lines) > MAX_EVOLUTION_LOG_LINES:
            print(f"    [NEEDS TRIMMING] — max {MAX_EVOLUTION_LOG_LINES}")
    
    leads_db = os.path.join(base_dir, "data", "leads.db")
    if os.path.exists(leads_db):
        size_kb = os.path.getsize(leads_db) / 1024
        print(f"  leads.db: {size_kb:.1f}KB")
    
    cdc_db = os.path.join(base_dir, "data", "call_capture.db")
    if os.path.exists(cdc_db):
        size_kb = os.path.getsize(cdc_db) / 1024
        print(f"  call_capture.db: {size_kb:.1f}KB")
    
    # 5. Port Check
    print("\n[5] PORT STATUS")
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8777))
        sock.close()
        if result == 0:
            print("  Port 8777: OCCUPIED (server running)")
        else:
            print("  Port 8777: FREE (no server)")
    except Exception as e:
        print(f"  Port check failed: {e}")
    
    # 6. Merchant Queue Guard
    print("\n[6] MERCHANT QUEUE GUARD")
    mq = os.path.join(base_dir, "merchant_queue.json")
    mq_backup = os.path.join(base_dir, "_merchant_queue_GARBAGE_BACKUP.json")
    if os.path.exists(mq):
        print("  WARNING: merchant_queue.json EXISTS — will auto-repopulate DB on empty!")
    else:
        print("  OK: merchant_queue.json NOT present (auto-repopulation blocked)")
    if os.path.exists(mq_backup):
        print(f"  Backup exists: _merchant_queue_GARBAGE_BACKUP.json ({os.path.getsize(mq_backup) / 1024:.0f}KB)")
    
    print("\n" + "=" * 60)
    print("  HEALTH CHECK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_health_check()
