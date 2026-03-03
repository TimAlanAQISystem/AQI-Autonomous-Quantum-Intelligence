#!/usr/bin/env python3
"""
AQI TWILIO TRUST HUB & COMPLIANCE CHECKER
==========================================
Check Twilio Trust Hub status and compliance requirements
"""

import os
import requests
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

def check_trust_hub_and_compliance():
    """
    Check Twilio Trust Hub status and compliance information
    """
    print("🔍 AQI TWILIO TRUST HUB & COMPLIANCE CHECK")
    print("=" * 60)

    # Get credentials from environment
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')

    if not all([account_sid, auth_token]):
        print("❌ Missing Twilio credentials in environment variables")
        return False

    print(f"📞 Account SID: {account_sid[:10]}...")
    print()

    try:
        # Initialize Twilio client
        client = Client(account_sid, auth_token)

        # Check Trust Hub status
        print("🏛️  TRUST HUB STATUS:")
        try:
            # Try to get customer profiles
            customer_profiles = client.trusthub.customer_profiles.list(limit=10)
            print(f"   Customer Profiles Found: {len(customer_profiles)}")

            for profile in customer_profiles:
                print(f"   📋 Profile SID: {profile.sid}")
                print(f"      Status: {profile.status}")
                print(f"      Friendly Name: {profile.friendly_name}")
                print(f"      Email: {profile.email}")
                print(f"      Type: {profile.customer_type}")

                # Check if it's the primary profile
                if hasattr(profile, 'primary_customer_profile_sid'):
                    print(f"      Primary Profile SID: {profile.primary_customer_profile_sid}")

                # Check regulatory bundle status
                try:
                    bundles = client.trusthub.customer_profiles(profile.sid).regulatory_compliance.bundle.list(limit=5)
                    print(f"      Regulatory Bundles: {len(bundles)}")
                    for bundle in bundles:
                        print(f"         - {bundle.friendly_name}: {bundle.status}")
                except Exception as e:
                    print(f"         ❌ Could not fetch bundles: {e}")

                print()

        except TwilioException as e:
            if "20003" in str(e):
                print("   ❌ Trust Hub not accessible (authentication issue)")
            else:
                print(f"   ❌ Trust Hub error: {e}")
        except Exception as e:
            print(f"   ❌ Could not check Trust Hub: {e}")

        print()

        # Check account compliance status
        print("📋 ACCOUNT COMPLIANCE STATUS:")
        try:
            account = client.api.accounts(account_sid).fetch()
            print(f"   Account Status: {account.status}")
            print(f"   Account Type: {account.type}")

            # Check for any compliance-related flags
            # This is limited by what the API exposes

        except Exception as e:
            print(f"   ❌ Could not check account compliance: {e}")

        print()

        # Check for any account restrictions or messages
        print("🚫 ACCOUNT RESTRICTIONS & MESSAGES:")
        try:
            # Try to get account notifications or alerts
            # This is limited by API capabilities
            print("   Checking for account alerts...")

            # Check if account can make calls (this will show the error)
            try:
                # This should fail with the voice calling error
                call = client.calls.create(
                    to="+15551234567",
                    from_=os.getenv('TWILIO_PHONE_NUMBER', '+18883277213'),
                    url="http://demo.twilio.com/docs/voice.xml"
                )
                print("   ✅ Voice calling is ENABLED")
                call.update(status="canceled")
            except TwilioException as e:
                error_code = str(e).split(' ')[0] if ' ' in str(e) else str(e)
                print(f"   ❌ Voice calling DISABLED - Error: {error_code}")
                print(f"      Full Error: {e}")

                # Analyze common error codes
                if "10005" in str(e):
                    print("      💡 Error 10005: Voice calling disabled for account")
                    print("      🔧 Likely requires Trust Hub approval or account upgrade")
                elif "20003" in str(e):
                    print("      💡 Error 20003: Authentication failed")
                elif "21212" in str(e):
                    print("      💡 Error 21212: Invalid phone number")

        except Exception as e:
            print(f"   ❌ Could not check restrictions: {e}")

        print()

        # Summary and recommendations
        print("📝 SUMMARY & RECOMMENDATIONS:")
        print("   1. Check Twilio Trust Hub: https://console.twilio.com/us1/develop/trust-hub")
        print("   2. Verify Primary Customer Profile is fully approved")
        print("   3. Check email for any compliance or security notifications")
        print("   4. Ensure all required documents are submitted")
        print("   5. Contact Twilio support if issues persist")

        print()
        print("🔗 IMPORTANT LINKS:")
        print("   Trust Hub: https://console.twilio.com/us1/develop/trust-hub")
        print("   Account Settings: https://console.twilio.com/us1/account/settings/billing/profile")
        print("   Support: https://support.twilio.com/hc/en-us")

        return True

    except TwilioException as e:
        print(f"❌ Twilio API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = check_trust_hub_and_compliance()
    if success:
        print("\n✅ Trust Hub and compliance check completed")
    else:
        print("\n❌ Trust Hub and compliance check failed")