# aqi_core/logging.py

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AQI_Media")

def log_event(event):
    logger.info(event)