import os
from twilio.rest import Client

def check_activation():
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    approved_bundle_sid = "BU9bd56890466024d033429b761ee53bc3"
    
    print(f"🔍 Checking Approved Bundle: {approved_bundle_sid}")
    try:
        bundle = client.trusthub.v1.customer_profiles(approved_bundle_sid).fetch()
        print(f"   Friendly Name: {bundle.friendly_name}")
        print(f"   Status: {bundle.status}")
        print(f"   Email: {bundle.email}")
    except Exception as e:
        print(f"   ❌ Error fetching bundle: {e}")

    print("\n🔍 Checking Phone Numbers & Compliance Association")
    try:
        numbers = client.incoming_phone_numbers.list(limit=5)
        for number in numbers:
            print(f"   Number: {number.phone_number}")
            print(f"   Friendly Name: {number.friendly_name}")
            print(f"   Bundle SID: {number.bundle_sid}")
            print(f"   Address SID: {number.address_sid}")
            print(f"   Identity SID: {number.identity_sid}")
            
            if number.bundle_sid == approved_bundle_sid:
                print("   ✅ This number is linked to the APPROVED bundle!")
            else:
                print("   ⚠️ This number is NOT linked to the approved bundle.")
                
    except Exception as e:
        print(f"   ❌ Error fetching numbers: {e}")

if __name__ == "__main__":
    check_activation()
