"""
ALAN CALL MONITORING INTEGRATION
=================================
Hooks the live call monitor into control_api.py at all critical points.

Integration Points:
1. Call start (Stream Start)
2. Greeting sent
3. Agent wired
4. Merchant speech
5. Alan responses
6. Errors
7. Call end

Usage: Import these functions in control_api.py and call at appropriate points.
"""

import logging
from datetime import datetime
from typing import Optional

try:
    import alan_live_call_monitor as monitor
    MONITOR_AVAILABLE = True
    logging.info("[INTEGRATION] ✅ Call monitoring system loaded")
except ImportError as e:
    MONITOR_AVAILABLE = False
    logging.warning(f"[INTEGRATION] ⚠️ Call monitoring unavailable: {e}")
    # Create stub functions
    monitor = None

def safe_monitor_call(func, *args, **kwargs):
    """Safely call monitoring function with error handling"""
    if not MONITOR_AVAILABLE or not monitor:
        return None
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"[MONITOR] Error in monitoring: {e}", exc_info=True)
        return None

# =============================================================================
# INTEGRATION FUNCTIONS - Call these from control_api.py
# =============================================================================

def monitor_call_start(call_sid: str, session_id: str, merchant_phone: str = ""):
    """
    Hook 1: Call START
    Call this when Stream Start event is received
    
    Example location in control_api.py:
        if event_type == 'start':
            stream_sid = data.get('streamSid')
            call_sid = data.get('start', {}).get('callSid', 'unknown')
            monitor_call_start(call_sid, client_id, merchant_phone)
    """
    if not MONITOR_AVAILABLE:
        return
    
    logging.info(f"[MONITOR HOOK] 🎬 Call started: {call_sid[:12]}...")
    safe_monitor_call(monitor.start_monitoring, call_sid, session_id, merchant_phone)

def monitor_greeting_sent(call_sid: str, greeting_text: str = ""):
    """
    Hook 2: GREETING SENT
    Call this immediately after greeting TTS is sent
    
    Example location in control_api.py:
        await send_text_to_voice(greeting_text, session_id)
        monitor_greeting_sent(call_sid, greeting_text)
    """
    if not MONITOR_AVAILABLE:
        return
    
    logging.info(f"[MONITOR HOOK] 💬 Greeting sent: {call_sid[:12]}...")
    safe_monitor_call(monitor.log_greeting, call_sid)
    
    # Also log Alan's greeting as a response
    if greeting_text:
        safe_monitor_call(monitor.log_alan, call_sid, greeting_text, 0.0)

def monitor_agent_wired(call_sid: str):
    """
    Hook 3: AGENT WIRED
    Call this after agent is successfully initialized and wired
    
    Example location in control_api.py:
        capacitor.attach_agent(agent)
        monitor_agent_wired(call_sid)
    """
    if not MONITOR_AVAILABLE:
        return
    
    logging.info(f"[MONITOR HOOK] ⚡ Agent wired: {call_sid[:12]}...")
    safe_monitor_call(monitor.log_agent_ready, call_sid)

def monitor_merchant_speech(call_sid: str, text: str, response_time: float = 0.0):
    """
    Hook 4: MERCHANT SPEECH
    Call this when merchant speech is transcribed
    
    Example location in control_api.py:
        transcribed_text = await session.stt_engine.finalize_and_clear(session_key)
        monitor_merchant_speech(call_sid, transcribed_text)
    """
    if not MONITOR_AVAILABLE:
        return
    
    logging.debug(f"[MONITOR HOOK] 🎤 Merchant speech: {call_sid[:12]}... '{text[:30]}...'")
    safe_monitor_call(monitor.log_merchant, call_sid, text, response_time)

def monitor_alan_response(call_sid: str, text: str, response_time: float = 0.0):
    """
    Hook 5: ALAN RESPONSE
    Call this when Alan generates a response
    
    Example location in control_api.py:
        speech_text = agent.generate_response(context)
        monitor_alan_response(call_sid, speech_text, elapsed_time)
    """
    if not MONITOR_AVAILABLE:
        return
    
    logging.debug(f"[MONITOR HOOK] 💭 Alan response: {call_sid[:12]}... '{text[:30]}...'")
    safe_monitor_call(monitor.log_alan, call_sid, text, response_time)

def monitor_call_error(call_sid: str, error_type: str, error_message: str):
    """
    Hook 6: ERROR
    Call this when any error occurs during the call
    
    Example location in control_api.py:
        except Exception as e:
            monitor_call_error(call_sid, "STT_ERROR", str(e))
    """
    if not MONITOR_AVAILABLE:
        return
    
    logging.error(f"[MONITOR HOOK] ❌ Error: {call_sid[:12]}... {error_type}: {error_message}")
    safe_monitor_call(monitor.log_call_error, call_sid, error_type, error_message)

def monitor_call_warning(call_sid: str, warning: str):
    """
    Hook 7: WARNING
    Call this for warnings (slow response, short response, etc.)
    
    Example location in control_api.py:
        if response_time > 8.0:
            monitor_call_warning(call_sid, f"Slow response: {response_time:.2f}s")
    """
    if not MONITOR_AVAILABLE:
        return
    
    logging.warning(f"[MONITOR HOOK] ⚠️ Warning: {call_sid[:12]}... {warning}")
    safe_monitor_call(monitor.log_call_warning, call_sid, warning)

def monitor_call_end(call_sid: str):
    """
    Hook 8: CALL END
    Call this when call disconnects or completes
    
    Example location in control_api.py:
        except WebSocketDisconnect:
            monitor_call_end(call_sid)
    """
    if not MONITOR_AVAILABLE:
        return
    
    logging.info(f"[MONITOR HOOK] 🏁 Call ended: {call_sid[:12]}...")
    safe_monitor_call(monitor.end_monitoring, call_sid)

# =============================================================================
# QUERY FUNCTIONS - Access monitoring data
# =============================================================================

def get_active_calls():
    """Get all currently active calls"""
    if not MONITOR_AVAILABLE:
        return []
    return safe_monitor_call(monitor.get_active_calls) or []

def get_call_status(call_sid: str):
    """Get status of a specific call"""
    if not MONITOR_AVAILABLE:
        return None
    return safe_monitor_call(monitor.get_call_status, call_sid)

def get_call_transcript(call_sid: str):
    """Get transcript of a specific call"""
    if not MONITOR_AVAILABLE:
        return []
    return safe_monitor_call(monitor.get_call_transcript, call_sid) or []

def get_recent_alerts(count: int = 20):
    """Get recent alerts and warnings"""
    if not MONITOR_AVAILABLE:
        return []
    return safe_monitor_call(monitor.get_alerts, count) or []

# =============================================================================
# FASTAPI ENDPOINTS - Add these to control_api.py app
# =============================================================================

def register_monitoring_endpoints(app):
    """
    Register monitoring endpoints with FastAPI app
    Call this in control_api.py after app = FastAPI()
    
    Example:
        from alan_call_monitor_integration import register_monitoring_endpoints
        register_monitoring_endpoints(app)
    """
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    @app.get("/monitor/active-calls")
    async def api_active_calls():
        """Get all active calls"""
        return JSONResponse(content=get_active_calls())
    
    @app.get("/monitor/call/{call_sid}")
    async def api_call_status(call_sid: str):
        """Get status of a specific call"""
        status = get_call_status(call_sid)
        if status is None:
            return JSONResponse(content={"error": "Call not found"}, status_code=404)
        return JSONResponse(content=status)
    
    @app.get("/monitor/transcript/{call_sid}")
    async def api_call_transcript(call_sid: str):
        """Get transcript of a specific call"""
        transcript = get_call_transcript(call_sid)
        return JSONResponse(content={"transcript": transcript})
    
    @app.get("/monitor/alerts")
    async def api_recent_alerts(count: int = 20):
        """Get recent alerts"""
        alerts = get_recent_alerts(count)
        return JSONResponse(content={"alerts": alerts})
    
    @app.get("/monitor/dashboard")
    async def api_dashboard():
        """Get monitoring dashboard data"""
        return JSONResponse(content={
            "active_calls": get_active_calls(),
            "recent_alerts": get_recent_alerts(10),
            "timestamp": datetime.now().isoformat()
        })
    
    logging.info("[MONITOR] ✅ Monitoring API endpoints registered")

# =============================================================================
# INTEGRATION GUIDE
# =============================================================================

INTEGRATION_GUIDE = """
ALAN CALL MONITORING - INTEGRATION GUIDE
=========================================

Step 1: Import at top of control_api.py
---------------------------------------
from alan_call_monitor_integration import (
    monitor_call_start,
    monitor_greeting_sent,
    monitor_agent_wired,
    monitor_merchant_speech,
    monitor_alan_response,
    monitor_call_error,
    monitor_call_warning,
    monitor_call_end,
    register_monitoring_endpoints
)

Step 2: Register endpoints (after app = FastAPI())
---------------------------------------------------
register_monitoring_endpoints(app)

Step 3: Add hooks at key integration points
--------------------------------------------

3.1 Call Start (Stream Start event):
    if event_type == 'start':
        stream_sid = data.get('streamSid')
        call_sid = data.get('start', {}).get('callSid', 'unknown')
        monitor_call_start(call_sid, client_id, merchant_phone)

3.2 Greeting Sent:
    await send_text_to_voice(greeting_text, session_id)
    monitor_greeting_sent(call_sid, greeting_text)

3.3 Agent Wired:
    capacitor.attach_agent(agent)
    monitor_agent_wired(call_sid)

3.4 Merchant Speech:
    transcribed_text = await session.stt_engine.finalize_and_clear(session_key)
    if transcribed_text:
        monitor_merchant_speech(call_sid, transcribed_text)

3.5 Alan Response:
    speech_text = agent.generate_response(context)
    monitor_alan_response(call_sid, speech_text, response_time)

3.6 Errors:
    except Exception as e:
        monitor_call_error(call_sid, "ERROR_TYPE", str(e))

3.7 Call End:
    except WebSocketDisconnect:
        monitor_call_end(call_sid)
    finally:
        monitor_call_end(call_sid)

Step 4: Access monitoring data
-------------------------------
Via API endpoints:
- GET /monitor/active-calls
- GET /monitor/call/{call_sid}
- GET /monitor/transcript/{call_sid}
- GET /monitor/alerts
- GET /monitor/dashboard

Step 5: Test
------------
1. Start service: python control_api.py
2. Place test call: python trigger_call.py
3. Check dashboard: curl http://localhost:8777/monitor/dashboard
4. View transcript: curl http://localhost:8777/monitor/transcript/{CALL_SID}

Done! 🎯
"""

if __name__ == "__main__":
    print(INTEGRATION_GUIDE)
