"""
time_awareness.py - Time and date plugin for Agent X
Provides temporal awareness and scheduling capabilities
"""
import datetime

def run(*args, **kwargs):
    """Get current time information"""
    now = datetime.datetime.now()
    
    if args and args[0] == 'full':
        return {
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "timestamp": now.timestamp()
        }
    
    return f"Current time: {now.strftime('%I:%M %p on %A, %B %d, %Y')}"

def get_info():
    return {
        "name": "Time Awareness",
        "version": "1.0",
        "description": "Temporal awareness and time-based operations"
    }
