# Minimal control_api.py for testing
# import sys
# import os
# from pathlib import Path

# # Ensure src is in path
# ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# SRC_DIR = os.path.join(ROOT_DIR, 'src')
# if SRC_DIR not in sys.path:
#     sys.path.insert(0, SRC_DIR)

from fastapi import FastAPI
# from fastapi.staticfiles import StaticFiles
# from pydantic import BaseModel
# import logging

print("DEBUG: minimal control_api.py loaded")

app = FastAPI()

# # Mount static directory for audio files
# STATIC_DIR = Path(__file__).resolve().parent.joinpath("static")
# STATIC_DIR.mkdir(parents=True, exist_ok=True)
# app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# class ReasonRequest(BaseModel):
#     message: str

# # Initialize the AQI Agent
# agent = None
# # try:
# #     from aqi_agent_x import AQIAgentX
# #     agent = AQIAgentX()
# #     logging.info("✅ AQI Agent X initialized successfully")
# #     logging.info(f"Agent status: {agent.get_status()}")
# # except Exception as e:
# #     logging.error(f"❌ Failed to initialize AQI Agent X: {e}")
# #     agent = None

@app.get("/status")
def status():
    # if agent is None:
    #     raise HTTPException(status_code=503, detail="Agent not initialized")
    return {"ok": True, "agent": "none"}

# @app.post("/reason")
# def reason(req: ReasonRequest):
#     if agent is None:
#         raise HTTPException(status_code=503, detail="Agent not initialized")
#     try:
#         print(f"[REASON] Processing request: {req.message[:100]}...")
#         resp = agent.reason(req.message)
#         print(f"[REASON] Response generated successfully")
#         return {"ok": True, "response": resp}
#     except Exception as e:
#         print(f"[REASON ERROR] {str(e)}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Reasoning failed: {str(e)}")