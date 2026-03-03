import os
from twilio.rest import Client

def assign_trust_product():
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    # The phone number we found
    phone_number_sid = None
    phone_number_str = "+14067322659"
    
    # Find the SID for this number
    incoming = client.incoming_phone_numbers.list(phone_number=phone_number_str, limit=1)
    if incoming:
        phone_number_sid = incoming[0].sid
        print(f"Found Phone Number SID: {phone_number_sid} ({phone_number_str})")
    else:
        print(f"❌ Could not find phone number {phone_number_str}")
        return

    # The Approved Customer Profile SID
    customer_profile_sid = "BU9bd56890466024d033429b761ee53bc3"
    
    print(f"Attempting to assign number to Customer Profile {customer_profile_sid}...")
    
    try:
        assignment = client.trusthub.v1 \
            .customer_profiles(customer_profile_sid) \
            .customer_profiles_channel_endpoint_assignment \
            .create(
                channel_endpoint_type='phone-number',
                channel_endpoint_sid=phone_number_sid
            )
            
        print(f"✅ Successfully assigned number to Customer Profile!")
        print(f"   Assignment SID: {assignment.sid}")
        
    except Exception as e:
        print(f"❌ Assignment failed: {e}")

if __name__ == "__main__":
    assign_trust_product()
