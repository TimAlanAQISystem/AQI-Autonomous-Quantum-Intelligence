#!/usr/bin/env python3
"""
AGENT X — VPS DEPLOYMENT PACKAGE BUILDER
==========================================
Creates a clean deployment archive with only the files needed
for production. Excludes archives, snapshots, logs, venvs, etc.

Usage: python deploy_package.py
Output: agentx-deploy-YYYYMMDD.tar.gz
"""

import os
import tarfile
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Files/dirs to INCLUDE in deployment
INCLUDE_PATTERNS = [
    # Core server
    "control_api_fixed.py",
    "aqi_conversation_relay_server.py",
    "aqi_stt_engine.py",
    "aqi_voice_module.py",
    "aqi_voice_governance.py",
    "aqi_voice_negproof_tests.py",
    "supervisor.py",
    "tunnel_sync.py",
    "lead_database.py",
    "start_alan.ps1",
    "dashboard.html",
    
    # AI Brain + Subsystems
    "agent_alan_business_ai.py",
    "system_coordinator.py",
    "post_generation_hallucination_scanner.py",
    "emergency_override_system.py",
    "merchant_identity_persistence.py",
    "multi_turn_strategic_planning.py",
    "bias_auditing_system.py",
    "human_override_api.py",
    "master_closer_layer.py",
    "behavior_adaptation.py",
    "cognitive_reasoning_governor.py",
    "predictive_intent.py",
    "outcome_detection.py",
    "evolution_engine.py",
    "call_outcome_confidence.py",
    "outcome_attribution.py",
    "review_aggregation.py",
    "preference_model.py",
    "adaptive_closing.py",
    "objection_library.py",
    
    # Supporting modules
    "session_memory.py",
    "session_persistence.py",
    "outbound_controller.py",
    "merchant_queue.py",
    
    # Config files
    ".env.example",
    "system_config.json",
    "adaptive_closing_strategy.json",
    "behavior_adaptation_config.json",
    "call_outcome_confidence_config.json",
    "outcome_detection_config.json",
    "outcome_attribution_config.json",
    "review_aggregation_config.json",
    "evolution_config.json",
    "rapport_layer.json",
    "predictive_intent_model.json",
    "crg_config.json",
    "master_closer_config.json",
    "agent_alan_config.json",
    
    # Data directory
    "data/",
    
    # Requirements
    "requirements.txt",
]

# Directories to EXCLUDE
EXCLUDE_DIRS = {
    "_ARCHIVE", "snapshots", "agentx-fresh", "agentx-production",
    ".venv", "venv", "__pycache__", ".git", "node_modules",
    "logs", "alan_brain", "alan_system", "telephony_adapter",
    "iqcores", "iqcore_from_app", "fluidic_arch", "aqi-talk",
    "aqi_delta", "aqi_crossrefs", "aqi_governance",
    "aqi_governance_intelligence", "Alan_Deployment", "dashboard",
    "agentx-snap-20251216-101906", ".vscode"
}


def build_package():
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_file = BASE_DIR / f"agentx-deploy-{timestamp}.tar.gz"
    
    included_files = []
    
    # Collect explicitly listed files
    for pattern in INCLUDE_PATTERNS:
        path = BASE_DIR / pattern
        if path.is_file():
            included_files.append(path)
        elif path.is_dir():
            for root, dirs, files in os.walk(path):
                # Skip excluded subdirs
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for f in files:
                    if not f.endswith(('.pyc', '.log', '.bak')):
                        included_files.append(Path(root) / f)
    
    # Also scan root for .py files that are imported but might not be in the list
    for f in BASE_DIR.glob("*.py"):
        if f not in included_files and f.name != "deploy_package.py":
            included_files.append(f)
    
    # Scan root for .json config files
    for f in BASE_DIR.glob("*.json"):
        if f not in included_files:
            included_files.append(f)
    
    # Build tarball
    with tarfile.open(output_file, "w:gz") as tar:
        for file_path in sorted(set(included_files)):
            arcname = file_path.relative_to(BASE_DIR)
            tar.add(file_path, arcname=str(arcname))
    
    print(f"\n=== DEPLOYMENT PACKAGE BUILT ===")
    print(f"Output: {output_file}")
    print(f"Files: {len(included_files)}")
    print(f"Size: {output_file.stat().st_size / 1024:.1f} KB")
    
    return output_file


# Also generate a setup script for the VPS
SETUP_SCRIPT = """#!/bin/bash
# AGENT X — VPS Setup Script
# Run this on a fresh Ubuntu 22.04+ VPS

set -e

echo "=== AGENT X VPS SETUP ==="

# System deps
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip ffmpeg

# Create app directory
mkdir -p /opt/agentx
cd /opt/agentx

# Extract deployment package (copy the tar.gz to the VPS first)
# tar -xzf agentx-deploy-*.tar.gz

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install Python deps
pip install --upgrade pip
pip install -r requirements.txt

# Copy .env.example to .env and fill in credentials
cp .env.example .env
echo ">>> EDIT .env WITH YOUR CREDENTIALS <<<"
echo ">>> nano .env <<<"

# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Create systemd service
cat > /etc/systemd/system/agentx.service << 'SYSTEMD'
[Unit]
Description=Agent X Voice AI Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/agentx
Environment=PATH=/opt/agentx/.venv/bin:/usr/local/bin:/usr/bin
ExecStart=/opt/agentx/.venv/bin/python -m hypercorn control_api_fixed:app --bind 0.0.0.0:8777
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD

# Create cloudflared tunnel service  
cat > /etc/systemd/system/agentx-tunnel.service << 'SYSTEMD'
[Unit]
Description=Agent X Cloudflare Tunnel
After=network.target
Before=agentx.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/agentx
ExecStart=/usr/local/bin/cloudflared tunnel --url http://127.0.0.1:8777
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD

# Enable services
sudo systemctl daemon-reload
sudo systemctl enable agentx agentx-tunnel
# sudo systemctl start agentx-tunnel agentx

echo ""
echo "=== SETUP COMPLETE ==="
echo "1. Edit /opt/agentx/.env with your API keys"
echo "2. Run: sudo systemctl start agentx-tunnel"
echo "3. Copy tunnel URL to active_tunnel_url.txt"
echo "4. Run: sudo systemctl start agentx"
echo "5. For permanent tunnel: cloudflared tunnel create agentx"
echo ""
"""


if __name__ == "__main__":
    # Write setup script
    setup_path = BASE_DIR / "vps_setup.sh"
    setup_path.write_text(SETUP_SCRIPT)
    print(f"VPS setup script: {setup_path}")
    
    # Build package
    build_package()
