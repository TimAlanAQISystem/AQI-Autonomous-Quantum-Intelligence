"""
TTS Access Control Layer
Author: Claude + User
Purpose: Import-level enforcement to prevent architectural violations
         Only authorized modules can access TTS synthesis

This module wraps the actual TTS implementation with access control.
"""

import os
import logging
import inspect
from typing import AsyncGenerator, Optional
from aqi_voice_governance import get_voice_governor, SpeakerRole, governed_speech

logger = logging.getLogger("AQI_TTS_CONTROL")

# Authorized callers for TTS access
AUTHORIZED_CALLERS = {
    "aqi_voice_module",
    "agent_alan_business_ai", 
    "aqi_conversation_relay_server",
    "control_api",
    "emergency_fix_deployment",
    "ALAN_REVENUE_FIXES"
}

# Emergency bypass modules (for safety-critical messages)
EMERGENCY_MODULES = {
    "emergency_fix_deployment",
    "ALAN_REVENUE_FIXES", 
    "alan_call_monitor_integration"
}

class TTSAccessViolation(Exception):
    """Raised when unauthorized module tries to access TTS"""
    pass

def _get_caller_module() -> str:
    """Get the module name of the calling code"""
    frame = inspect.currentframe()
    try:
        # Go up the stack to find the actual caller
        for _ in range(10):  # Look up to 10 frames
            frame = frame.f_back
            if frame is None:
                break
            
            module_name = frame.f_globals.get('__name__', '')
            if module_name and not module_name.startswith('aqi_tts_'):
                return module_name.split('.')[-1]  # Get just the filename
        
        return "unknown"
    finally:
        del frame

def _check_access_permission(caller_module: str) -> tuple[bool, SpeakerRole]:
    """
    Check if caller module has TTS access permission.
    
    Returns: (is_authorized, speaker_role)
    """
    # Safety override always allowed
    if caller_module in EMERGENCY_MODULES:
        return True, SpeakerRole.EMERGENCY_SYSTEM
    
    # Check authorized callers
    if caller_module in AUTHORIZED_CALLERS:
        return True, SpeakerRole.CONVERSATIONAL_CORE
    
    # Check if it's a conversational core module
    if "alan" in caller_module.lower() or "aqi" in caller_module.lower():
        return True, SpeakerRole.CONVERSATIONAL_CORE
    
    return False, SpeakerRole.NONE

async def governed_tts_synthesis(text: str, **kwargs) -> AsyncGenerator[bytes, None]:
    """
    TTS synthesis with governance enforcement.
    
    This is the only function that should be used for TTS synthesis.
    It enforces architectural governance and prevents unauthorized access.
    """
    caller_module = _get_caller_module()
    
    # Check access permission
    is_authorized, role = _check_access_permission(caller_module)
    
    if not is_authorized:
        error_msg = f"TTS access denied for unauthorized module: {caller_module}"
        logger.error(f"[TTS_CONTROL] {error_msg}")
        raise TTSAccessViolation(error_msg)
    
    # Determine if this is an emergency request
    is_emergency = caller_module in EMERGENCY_MODULES
    
    # Request governance permission
    try:
        permission_granted = await governed_speech(
            text=text,
            caller_id=caller_module,
            role=role,
            emergency=is_emergency
        )
        
        if not permission_granted:
            logger.warning(f"[TTS_CONTROL] Speech governance denied for {caller_module}")
            return
        
        logger.debug(f"[TTS_CONTROL] TTS authorized for {caller_module} (role: {role.value})")
        
        # Import actual TTS implementation
        from aqi_tts_engine import _elevenlabs_tts
        
        # Signal core is healthy if this is the conversational core
        if role == SpeakerRole.CONVERSATIONAL_CORE:
            get_voice_governor().heartbeat()
        
        # Execute TTS synthesis
        async for chunk in _elevenlabs_tts(text, **kwargs):
            yield chunk
    
    except Exception as e:
        logger.error(f"[TTS_CONTROL] TTS synthesis error for {caller_module}: {e}")
        
        # If this was an emergency request, try fallback
        if is_emergency:
            logger.warning("[TTS_CONTROL] Emergency TTS fallback")
            try:
                from aqi_tts_engine import _elevenlabs_tts
                async for chunk in _elevenlabs_tts(text, **kwargs):
                    yield chunk
            except Exception as fallback_error:
                logger.error(f"[TTS_CONTROL] Emergency TTS fallback failed: {fallback_error}")
                raise

def create_mock_tts():
    """Create a mock TTS function that raises violations"""
    def mock_tts(*args, **kwargs):
        caller_module = _get_caller_module()
        raise TTSAccessViolation(f"Direct TTS access not allowed for {caller_module}. Use governed_tts_synthesis()")
    return mock_tts