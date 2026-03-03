import os
from twilio.rest import Client

def inspect():
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)
    
    sid = "BUa76439f064660f7b41de5a854ac2be2b"
    tp = client.trusthub.v1.trust_products(sid)
    
    print(f"Inspecting Trust Product Context: {sid}")
    print(dir(tp))

if __name__ == "__main__":
    inspect()
