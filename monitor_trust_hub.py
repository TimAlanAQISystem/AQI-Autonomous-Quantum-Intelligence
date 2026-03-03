import os
import time
import datetime
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Configuration
CHECK_INTERVAL_HOURS = 4
CHECK_INTERVAL_SECONDS = CHECK_INTERVAL_HOURS * 3600
# Updated SID based on actual account listing
BUNDLE_SID = "BU6f81ca2c5ddf34a2ad3ead04d2163c4d" # My Starter Profile (Currently in-review)

def check_status():
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')

    if not account_sid or not auth_token:
        print("❌ Error: TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not set.")
        return False

    client = Client(account_sid, auth_token)

    print(f"🔍 Checking Trust Hub Bundle Status for {BUNDLE_SID}...")
    try:
        # Fetch the bundle
        # Note: Depending on the exact type, this might be a customer_profile or just a bundle.
        # Trying customer_profiles first as per documentation context.
        try:
            # Corrected attribute name from trust_hub to trusthub based on introspection
            bundle = client.trusthub.v1.customer_profiles(BUNDLE_SID).fetch()
        except TwilioRestException:
            # Fallback to generic bundle fetch if customer_profiles fails (though BU usually implies Bundle)
            # But the library might expose it differently. 
            # Let's try to just print the error if it fails, but usually BU is a Bundle.
            # Actually, for Trust Hub, it's often client.trust_hub.v1.customer_profiles(sid)
            raise

        status = bundle.status
        friendly_name = bundle.friendly_name
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"[{timestamp}] Bundle: {friendly_name}")
        print(f"[{timestamp}] Status: {status}")
        
        if status == 'twilio-approved':
            print("✅ SUCCESS: Account is APPROVED and ACTIVE!")
            # Create a flag file
            with open("TWILIO_ACTIVATION_SUCCESS.txt", "w") as f:
                f.write(f"Twilio Trust Hub Bundle {BUNDLE_SID} was approved at {timestamp}.\n")
            return True
        elif status == 'in-review':
            print("⏳ Status is still 'in-review'. Waiting...")
        elif status == 'draft':
            print("⚠️ Status is 'draft'. Submission might be required.")
        elif status == 'twilio-rejected':
            print("❌ Status is 'twilio-rejected'. Action required!")
        else:
            print(f"ℹ️ Current Status: {status}")
            
    except TwilioRestException as e:
        print(f"❌ Twilio Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        
    return False

def main():
    print(f"🚀 Starting Twilio Activation Monitor.")
    print(f"⏱️  Check Interval: {CHECK_INTERVAL_HOURS} hours.")
    
    # Run immediately once
    is_active = check_status()
    if is_active:
        print("🎉 Activation detected! Exiting monitor.")
        return

    while True:
        print(f"💤 Sleeping for {CHECK_INTERVAL_HOURS} hours...")
        time.sleep(CHECK_INTERVAL_SECONDS)
        
        is_active = check_status()
        if is_active:
            print("🎉 Activation detected! Exiting monitor.")
            break

if __name__ == "__main__":
    main()
