import os
import requests
from requests.auth import HTTPBasicAuth

# Twilio credentials from environment variables
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')

# Target phone number (replace with the actual number you want to call)
target_number = '+14062102346'  # Example: the number from your conversation

# TwiML for the call (simple greeting)
twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Hello! This is Alan from Agent X calling to connect with you.</Say>
    <Pause length="1"/>
    <Say voice="alice">I hope you're having a great day. Let's chat!</Say>
</Response>'''

def make_voice_call():
    """
    Make a voice call using Twilio's REST API directly.
    This creates a Call resource via POST request to the Calls endpoint.
    """
    if not all([account_sid, auth_token, twilio_phone_number]):
        print("Error: Missing Twilio credentials. Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER environment variables.")
        return

    url = f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json'

    data = {
        'From': twilio_phone_number,
        'To': target_number,
        'Twiml': twiml
    }

    try:
        response = requests.post(url, data=data, auth=HTTPBasicAuth(account_sid, auth_token))

        if response.status_code == 201:
            call_data = response.json()
            print(f"Call initiated successfully!")
            print(f"Call SID: {call_data['sid']}")
            print(f"Status: {call_data['status']}")
            print(f"From: {call_data['from']}")
            print(f"To: {call_data['to']}")

            # Optionally check call status
            check_call_status(call_data['sid'])
        else:
            print(f"Error creating call: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"Exception occurred: {str(e)}")

def check_call_status(call_sid):
    """
    Check the status of the call using the Call SID.
    """
    url = f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json'

    try:
        response = requests.get(url, auth=HTTPBasicAuth(account_sid, auth_token))

        if response.status_code == 200:
            call_data = response.json()
            print(f"Call Status: {call_data['status']}")
            if 'duration' in call_data and call_data['duration']:
                print(f"Duration: {call_data['duration']} seconds")
            if 'price' in call_data and call_data['price']:
                print(f"Price: {call_data['price']} {call_data['price_unit']}")
        else:
            print(f"Error fetching call status: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"Exception occurred while checking status: {str(e)}")

if __name__ == "__main__":
    print("Initiating voice call using Twilio REST API...")
    make_voice_call()