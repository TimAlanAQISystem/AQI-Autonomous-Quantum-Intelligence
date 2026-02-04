#!/usr/bin/env python3
"""
ALAN AGENT X - CONTROL API (FIXED VERSION)
Voice-enabled conversational AI with Twilio integration
"""

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from enum import Enum
import uvicorn

# Configure enhanced logging with rotation
from logging.handlers import RotatingFileHandler

# Setup logging with rotation (10MB max, 5 backups)
log_formatter = logging.Formatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File handler with rotation
file_handler = RotatingFileHandler(
    'control_api.log', 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agent X Control API",
    description="Voice-enabled conversational AI with Twilio integration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS Middleware to allow WebSocket connections from Twilio (and everywhere for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to hold the agent instance
agent = None

@app.get("/health")
async def health_check():
    """Minimal health check for debugging"""
    return {"status": "ok", "agent": "minimal"}

# Mount AQI Voice Module router
voice_functions_available = False
# VOICE MODULE: Re-enabled for final pipeline test
disable_voice_module_for_testing = False

if not disable_voice_module_for_testing:
    try:
        from aqi_voice_module import router as voice_router, register_stt_callback, send_text_to_voice, register_connect_callback, voice_sessions, cancel_speech, preload_text_to_voice, preload_text_to_cache, play_from_cache, VoiceSession
        from aqi_voice_module import GLOBAL_AUDIO_CACHE # [DIRECTIVE 60] Access to pre-loaded pivot
        app.include_router(voice_router)
        voice_functions_available = True
        logging.info("AQI Voice Module router enabled")
        
        # Pipeline Step 4: Register STT callback for reasoning engine
        def process_voice_transcript(text: str, session_id: str):
            """
            Step 4: Reasoning Engine - Convert user text to Alan's response
            This is where Alan's brain processes what the user said
            """
            if not text.strip():
                return
            
            logger.info(f"[ASR] User said: '{text}' in session {session_id}")
            
            # Step 4: Alan's reasoning engine
            # TODO: Replace this stub with actual Alan reasoning
            if "hello" in text.lower():
                response_text = "Hi there! This is Alan. How can I help you today?"
            elif "rates" in text.lower() or "fee" in text.lower():
                response_text = "Great question about rates. We typically beat most competitors by significant margins. What's your current rate?"
            else:
                response_text = "I understand. Can you tell me more about what you're looking for?"
            
            logger.info(f"[ALAN] Reasoned response: '{response_text}'")
            
            # Step 5 & 6: Send response to TTS and stream back to caller
            asyncio.create_task(send_text_to_voice(response_text, session_id))
        
        # Register the STT callback to connect ASR to Reasoning pipeline
        register_stt_callback(process_voice_transcript)
        logger.info("STT callback registered - ASR to Reasoning pipeline connected")
        
    except ImportError as e:
        logging.warning(f"AQI Voice Module unavailable: {e}")

# Create stub functions to prevent startup crashes
async def preload_text_to_voice(text, session_id):
    logging.info(f"[STUB] Would preload: '{text}' for session {session_id}")

async def preload_text_to_cache(key, text):
    logging.info(f"[STUB] Would cache '{key}': '{text}'")

# Startup Events: Temporarily disabled to isolate HTTP request issue
# @app.on_event("startup")
# async def startup_event_1():
#     """Warm up the agent on startup"""
#     logger.info("[STARTUP] Starting Agent X warmup...")
#     
#     async def _run_warmup():
#         logger.info("[WARMUP] Background Task Started.")
#         # [DIRECTIVE 37] Part 1 of Zero-Entropy Nudge
#         await preload_text_to_voice("Hello? This is Alan.", "GLOBAL_WARMUP")
#         logger.info("[WARMUP] Background Task Complete.")
# 
#     # Fire and forget (don't await this wrapper)
#     asyncio.create_task(_run_warmup())
    
# @app.on_event("startup")
# async def startup_event_2():
#     """Populate audio cache with common phrases"""
#     logger.info("[STARTUP] Starting Event 2 - Audio cache population...")
#     
#     async def _populate_cache():
#         # [TESTING] Disable actual cache population to test if that's causing shutdown
#         logger.info("[CACHE] Skipping actual cache population for testing")
#         # stealth_greeting = "Hey, it's Alan with SCSDM out in Chicago. I'm looking at the Rate Hikes Visa just pushed through. You got thirty seconds?"
#         # await preload_text_to_cache("GREETING_FULL", stealth_greeting)
#         
#         # await preload_text_to_cache("rates_pitch", "Great question. We look at your current statement, and if we can't beat your rates, usually around 1.5%, we give you $500.")
#         # await preload_text_to_cache("competitor_pitch", "I hear that a lot. They are popular, but usually come with high transaction fees. We can typically beat their rates by a significant margin.")
#         # await preload_text_to_cache("pivot", "Okay, let's jump right in.")
#         logging.info("[CACHE] Audio cache population complete (testing mode).")
# 
#     # Fire and forget (don't await this wrapper)
#     asyncio.create_task(_populate_cache())
# 
# @app.on_event("startup")
# async def startup_event_3():
#     """Initialize business logic components"""
#     logger.info("[STARTUP] Starting Event 3 - Business logic initialization...")
#     
#     async def _init_business_logic():
#         # Initialize any additional business components here
#         logging.info("[BUSINESS] Business logic initialization complete.")
#         
#     # Fire and forget (don't await this wrapper)
#     asyncio.create_task(_init_business_logic())
# 
#     # Fire and forget (don't await this wrapper)
#     asyncio.create_task(_init_business_logic())

# Basic Twilio webhook endpoint
@app.post("/twilio/voice")
async def handle_twilio_voice():
    """Handle incoming Twilio voice calls"""
    twiml_response = '''<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say>Hello! Agent X Control API is working. This call is being handled successfully.</Say>
    </Response>'''
    
    return HTMLResponse(content=twiml_response, media_type="application/xml")

if __name__ == "__main__":
    try:
        logging.info("Starting Agent X Control API on port 8777...")
        uvicorn.run(app, host="0.0.0.0", port=8777)
    except Exception as e:
        logging.error(f"Failed to start server: {e}")