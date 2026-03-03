#!/usr/bin/env python3
"""
AQI TWILIO ACCOUNT STATUS CHECKER
==================================
Check Twilio account status, balance, and capabilities
"""

import os
import requests
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

def check_twilio_account_status():
    """
    Check the current Twilio account status and capabilities
    """
    print("🔍 AQI TWILIO ACCOUNT STATUS CHECK")
    print("=" * 50)

    # Get credentials from environment
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    phone_number = os.getenv('TWILIO_PHONE_NUMBER')

    if not all([account_sid, auth_token, phone_number]):
        print("❌ Missing Twilio credentials in environment variables")
        return False

    print(f"📞 Account SID: {account_sid[:10]}...")
    print(f"📱 Phone Number: {phone_number}")
    print()

    try:
        # Initialize Twilio client
        client = Client(account_sid, auth_token)

        # Get account information
        account = client.api.accounts(account_sid).fetch()

        print("📊 ACCOUNT INFORMATION:")
        print(f"   Status: {account.status}")
        print(f"   Type: {account.type}")
        print(f"   Friendly Name: {account.friendly_name}")
        print()

        # Check account balance
        balance = client.api.balance.fetch()
        print("💰 ACCOUNT BALANCE:")
        print(f"   Current Balance: ${balance.balance}")
        print(f"   Currency: {balance.currency}")
        print()

        # Check available phone numbers
        try:
            incoming_numbers = client.incoming_phone_numbers.list(limit=5)
            print("📱 PHONE NUMBERS:")
            print(f"   Total Numbers: {len(incoming_numbers)}")
            for number in incoming_numbers:
                print(f"   - {number.phone_number} ({number.friendly_name})")
            print()
        except Exception as e:
            print(f"❌ Error fetching phone numbers: {e}")
            print()

        # Check voice capabilities
        print("🎤 VOICE CAPABILITIES:")
        try:
            # Try to make a test call to check if voice is enabled
            call = client.calls.create(
                to="+15551234567",  # Test number
                from_=phone_number,
                url="http://demo.twilio.com/docs/voice.xml",
                method="GET"
            )
            print("   ✅ Voice calling appears to be enabled")
            print(f"   Test Call SID: {call.sid}")
            # Cancel the test call immediately
            call.update(status="canceled")
        except TwilioException as e:
            if "10005" in str(e):
                print("   ❌ Voice calling is DISABLED for this account")
                print("   💡 This is common with trial accounts")
                print("   🔧 Solutions:")
                print("      1. Upgrade to a paid Twilio account")
                print("      2. Verify your account with billing information")
                print("      3. Enable voice calling in your Twilio Console")
            else:
                print(f"   ❌ Voice error: {e}")
        except Exception as e:
            print(f"   ⚠️  Could not test voice capabilities: {e}")

        print()
        print("🔗 USEFUL LINKS:")
        print("   Twilio Console: https://console.twilio.com")
        print("   Account Settings: https://console.twilio.com/us1/account/settings/billing/profile")
        print("   Phone Numbers: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming")
        print("   Voice Settings: https://console.twilio.com/us1/develop/voice/settings")

        return True

    except TwilioException as e:
        print(f"❌ Twilio API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = check_twilio_account_status()
    if success:
        print("\n✅ Account status check completed")
    else:
        print("\n❌ Account status check failed")