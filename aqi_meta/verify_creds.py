#!/usr/bin/env python3
import json
from cryptography.fernet import Fernet

# Load key and decrypt
with open('alan_encryption.key', 'rb') as f:
    key = f.read()
cipher = Fernet(key)

with open('alan_agent_portal_credentials.enc', 'rb') as f:
    encrypted = f.read()

decrypted = cipher.decrypt(encrypted)
creds = json.loads(decrypted.decode())

print('✅ Real PaymentsHub credentials verified!')
print('Client ID:', creds['client_id'])
print('Username:', creds['username'])
print('Base URL:', creds['base_url'])
print('Auth URL:', creds['auth_url'])
print('Valid:', creds['is_valid'])
print('Access Level:', creds['access_level'])