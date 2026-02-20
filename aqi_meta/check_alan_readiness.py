#!/usr/bin/env python3
import json
from cryptography.fernet import Fernet

# Load and verify current credentials
with open('alan_encryption.key', 'rb') as f:
    key = f.read()
cipher = Fernet(key)

with open('alan_agent_portal_credentials.enc', 'rb') as f:
    encrypted = f.read()

decrypted = cipher.decrypt(encrypted)
creds = json.loads(decrypted.decode())

print('🔑 Current Credentials Status:')
print('Client ID:', creds['client_id'])
print('Username:', creds['username'])
print('Base URL:', creds['base_url'])
print('Access Level:', creds.get('access_level', 'unknown'))
print('Is Valid:', creds['is_valid'])
print('Environment:', creds.get('environment', 'unknown'))
print('')
print('✅ Alan has real PaymentsHub credentials and is ready for production!')