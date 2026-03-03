import os
from twilio.rest import Client

def list_resources():
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    print("--- Customer Profiles ---")
    try:
        profiles = client.trusthub.v1.customer_profiles.list(limit=5)
        for p in profiles:
            print(f"SID: {p.sid}, Friendly Name: {p.friendly_name}, Status: {p.status}")
    except Exception as e:
        print(f"Error listing profiles: {e}")

    print("\n--- Trust Products ---")
    try:
        products = client.trusthub.v1.trust_products.list(limit=5)
        for p in products:
            print(f"SID: {p.sid}, Friendly Name: {p.friendly_name}, Status: {p.status}")
    except Exception as e:
        print(f"Error listing products: {e}")

    print("\n--- End Users ---")
    try:
        users = client.trusthub.v1.end_users.list(limit=5)
        for u in users:
            print(f"SID: {u.sid}, Friendly Name: {u.friendly_name}, Type: {u.type}")
    except Exception as e:
        print(f"Error listing end users: {e}")

if __name__ == "__main__":
    list_resources()
