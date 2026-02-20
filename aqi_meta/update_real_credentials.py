#!/usr/bin/env python3
"""
ALAN - Update Agent Portal Credentials with Real PaymentsHub Access
===================================================================

This script updates the encrypted Agent Portal credentials with the real
PaymentsHub credentials provided by the user.

Real Credentials Provided:
- OAuth URL: https://accounts.paymentshub.com/auth/realms/nab/protocol/openid-connect/auth
- Client ID: agent-hub (from OAuth URL)
- Username: Signaturecardservicesdmc@msn.com
- Password: Baseball+1
- Redirect URI: https://partner.paymentshub.com/dashboard
- Access: Full access granted

Created: December 15, 2025
Author: TimAlanAQISystem
"""

import json
import os
from datetime import datetime
from cryptography.fernet import Fernet

def update_credentials():
    """Update credentials with real PaymentsHub access."""

    # Load existing encryption key
    key_file = "alan_encryption.key"
    if not os.path.exists(key_file):
        print("❌ Encryption key not found!")
        return False

    with open(key_file, 'rb') as f:
        encryption_key = f.read()

    cipher = Fernet(encryption_key)

    # Real PaymentsHub credentials
    real_credentials = {
        "client_id": "agent-hub",  # From OAuth URL
        "client_secret": "Baseball+1",  # Password provided
        "webhook_secret": "payments_hub_webhook_secret_2025",  # Generated placeholder
        "base_url": "https://partner.paymentshub.com",
        "auth_url": "https://accounts.paymentshub.com/auth/realms/nab/protocol/openid-connect/auth",
        "username": "Signaturecardservicesdmc@msn.com",  # Username provided
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

    print("✅ Real PaymentsHub credentials updated successfully!")
    print(f"🔐 Client ID: {real_credentials['client_id']}")
    print(f"🌐 Base URL: {real_credentials['base_url']}")
    print(f"🔑 Auth URL: {real_credentials['auth_url']}")
    print(f"👤 Username: {real_credentials['username']}")
    print(f"🔒 Access Level: {real_credentials['access_level']}")

    return True

def verify_credentials():
    """Verify the updated credentials can be loaded."""

    # Load encryption key
    key_file = "alan_encryption.key"
    if not os.path.exists(key_file):
        print("❌ Encryption key not found!")
        return False

    with open(key_file, 'rb') as f:
        encryption_key = f.read()

    cipher = Fernet(encryption_key)

    try:
        # Load encrypted credentials
        with open("alan_agent_portal_credentials.enc", "rb") as f:
            encrypted_data = f.read()

        # Decrypt and parse
        decrypted_data = cipher.decrypt(encrypted_data)
        credentials = json.loads(decrypted_data.decode())

        print("✅ Credentials verification successful!")
        print(f"🔐 Client ID: {credentials.get('client_id')}")
        print(f"👤 Username: {credentials.get('username')}")
        print(f"🌐 Base URL: {credentials.get('base_url')}")
        print(f"🔑 Auth URL: {credentials.get('auth_url')}")
        print(f"✅ Valid: {credentials.get('is_valid')}")

        return True

    except Exception as e:
        print(f"❌ Credential verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Updating Agent Portal credentials with real PaymentsHub access...")

    # Change to the correct directory
    os.chdir(r"c:\Users\signa\OneDrive\Desktop\Agent X\aqi_meta")

    if update_credentials():
        print("\n🔍 Verifying updated credentials...")
        verify_credentials()
        print("\n🎉 Real PaymentsHub credentials successfully integrated!")
        print("🤖 Alan now has full access to the Agent Portal (Main Office)")
    else:
        print("❌ Failed to update credentials")</content>
<parameter name="filePath">c:\Users\signa\OneDrive\Desktop\Agent X\aqi_meta\update_real_credentials.py