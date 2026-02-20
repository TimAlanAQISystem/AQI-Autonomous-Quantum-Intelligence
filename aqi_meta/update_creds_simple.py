#!/usr/bin/env python3
import json
import os
from datetime import datetime
from cryptography.fernet import Fernet

# Load existing encryption key
key_file = "alan_encryption.key"
if not os.path.exists(key_file):
    print("Encryption key not found!")
    exit(1)

with open(key_file, 'rb') as f:
    encryption_key = f.read()

cipher = Fernet(encryption_key)

# Real PaymentsHub credentials
real_credentials = {
    "client_id": "agent-hub",
    "client_secret": "Baseball+1",
    "webhook_secret": "payments_hub_webhook_secret_2025",
    "base_url": "https://partner.paymentshub.com",
    "auth_url": "https://accounts.paymentshub.com/auth/realms/nab/protocol/openid-connect/auth",
    "username": "Signaturecardservicesdmc@msn.com",
    "obtained_at": datetime.now().isoformat(),
    "is_valid": True,
    "environment": "production",
    "api_version": "v1",
    "access_level": "full_access_granted"
}

# Encrypt and save
encrypted_data = cipher.encrypt(json.dumps(real_credentials).encode())

with open("alan_agent_portal_credentials.enc", "wb") as f:
    f.write(encrypted_data)

print("Real PaymentsHub credentials updated successfully!")
print("Client ID: agent-hub")
print("Username: Signaturecardservicesdmc@msn.com")
print("Base URL: https://partner.paymentshub.com")
print("Access Level: full_access_granted")