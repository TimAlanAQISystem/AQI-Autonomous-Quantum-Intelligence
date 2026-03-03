#!/usr/bin/env python3
"""
AQI TWILIO COMPREHENSIVE STATUS CHECKER
========================================
Detailed Twilio account status and voice capabilities analysis
"""

import os
import requests
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

def comprehensive_twilio_check():
    """
    Comprehensive check of Twilio account status and capabilities
    """
    print("🔍 AQI COMPREHENSIVE TWILIO STATUS CHECK")
    print("=" * 60)

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
        print(f"   Date Created: {account.date_created}")
        print(f"   Auth Token: {'Set' if auth_token else 'Not Set'}")
        print()

        # Check account balance
        try:
            balance = client.api.balance.fetch()
            print("💰 ACCOUNT BALANCE:")
            print(f"   Current Balance: ${balance.balance}")
            print(f"   Currency: {balance.currency}")
        except Exception as e:
            print(f"⚠️  Could not fetch balance: {e}")

        print()

        # Check available phone numbers
        try:
            incoming_numbers = client.incoming_phone_numbers.list(limit=5)
            print("📱 PHONE NUMBERS:")
            print(f"   Total Numbers: {len(incoming_numbers)}")
            for number in incoming_numbers:
                print(f"   - {number.phone_number}")
                print(f"     Friendly Name: {number.friendly_name}")
                print(f"     Capabilities: Voice={number.capabilities.get('voice', 'N/A')}, SMS={number.capabilities.get('sms', 'N/A')}")
                print(f"     Status: {number.status}")
            print()
        except Exception as e:
            print(f"❌ Error fetching phone numbers: {e}")
            print()

        # Check account usage and limits
        try:
            usage = client.api.usage.records.today.list(limit=5)
            print("📈 USAGE INFORMATION:")
            for record in usage:
                print(f"   {record.category}: {record.count} ({record.description})")
            print()
        except Exception as e:
            print(f"⚠️  Could not fetch usage: {e}")
            print()

        # Check voice capabilities with different approaches
        print("🎤 VOICE CAPABILITIES ANALYSIS:")
        print("   Method 1: Direct API call test")

        # Method 1: Try to create a call
        try:
            call = client.calls.create(
                to="+15551234567",  # Test number that should fail gracefully
                from_=phone_number,
                url="http://demo.twilio.com/docs/voice.xml",
                method="GET"
            )
            print("   ✅ Voice calling appears to be ENABLED")
            print(f"   Test Call SID: {call.sid}")
            # Cancel the test call immediately
            call.update(status="canceled")
        except TwilioException as e:
            if "10005" in str(e):
                print("   ❌ Voice calling is DISABLED (Error 10005)")
                print("   💡 This indicates voice services are not enabled")
            elif "21212" in str(e):
                print("   ⚠️  Invalid phone number (expected for test)")
                print("   ✅ Voice calling appears to be ENABLED (API accessible)")
            else:
                print(f"   ❌ Voice error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")

        print()
        print("   Method 2: Account capabilities check")
        try:
            # Check account capabilities
            capabilities = client.api.accounts(account_sid).fetch()
            print(f"   Account Status: {capabilities.status}")
            print(f"   Account Type: {capabilities.type}")
        except Exception as e:
            print(f"   ❌ Could not check capabilities: {e}")

        print()
        print("🔧 TROUBLESHOOTING STEPS:")
        print("   1. Verify billing information is complete")
        print("   2. Check if account is in trial mode")
        print("   3. Ensure PCI Mode is properly enabled")
        print("   4. Verify phone number capabilities")
        print("   5. Check geographic restrictions")
        print("   6. Contact Twilio support if needed")

        print()
        print("🔗 IMPORTANT LINKS:")
        print("   Twilio Console: https://console.twilio.com")
        print("   Account Settings: https://console.twilio.com/us1/account/settings/billing/profile")
        print("   Voice Settings: https://console.twilio.com/us1/develop/voice/settings")
        print("   Phone Numbers: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming")
        print("   Support: https://support.twilio.com/hc/en-us")

        return True

    except TwilioException as e:
        print(f"❌ Twilio API Error: {e}")
        print("💡 This might indicate authentication or account issues")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = comprehensive_twilio_check()
    if success:
        print("\n✅ Comprehensive status check completed")
    else:
        print("\n❌ Comprehensive status check failed")