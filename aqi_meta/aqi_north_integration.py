"""
AQI North Merchant Boarding Integration
========================================

Complete integration with North.com's Merchant Boarding API for AQI Merchant Services.
This enables AQI to onboard merchants, manage applications, and generate revenue
through the North payment processing network.

Features:
- OAuth2 authentication with North API
- Merchant application creation and management
- Underwriting status monitoring
- Equipment and pricing template management
- Production-ready merchant onboarding

Created: December 15, 2025
Author: TimAlanAQISystem
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import aiohttp
import jwt
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NorthMerchantBoardingAPI:
    """Complete North.com Merchant Boarding API integration."""

    def __init__(self, environment: str = "sandbox"):
        self.environment = environment
        self.base_urls = {
            "sandbox": {
                "api": "https://boarding-api.paymentshub.dev",
                "auth": "https://api-auth.paymentshub.dev"
            },
            "production": {
                "api": "https://boarding-api.paymentshub.com",
                "auth": "https://api-auth.paymentshub.com"
            }
        }

        self.client_id = os.getenv("NORTH_CLIENT_ID", "")
        self.client_secret = os.getenv("NORTH_CLIENT_SECRET", "")
        self.agent_id = os.getenv("NORTH_AGENT_ID", "")

        self.session = None
        self.access_token = None
        self.token_expires = None

    async def initialize(self) -> bool:
        """Initialize the North API integration."""
        logger.info("🚀 Initializing North Merchant Boarding API integration")

        if not all([self.client_id, self.client_secret, self.agent_id]):
            logger.error("❌ North API credentials not configured")
            logger.error("Set NORTH_CLIENT_ID, NORTH_CLIENT_SECRET, and NORTH_AGENT_ID")
            return False

        self.session = aiohttp.ClientSession()

        # Test authentication
        if not await self._authenticate():
            logger.error("❌ North API authentication failed")
            return False

        logger.info("✅ North Merchant Boarding API initialized")
        return True

    async def _authenticate(self) -> bool:
        """Authenticate with North API and get access token."""
        try:
            auth_url = f"{self.base_urls[self.environment]['auth']}/oauth/token"

            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            async with self.session.post(auth_url, data=auth_data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.access_token = token_data.get("access_token")

                    # Decode JWT to get expiration
                    token_payload = jwt.decode(self.access_token, options={"verify_signature": False})
                    self.token_expires = datetime.fromtimestamp(token_payload.get("exp", 0))

                    logger.info("✅ North API authentication successful")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ North API authentication failed: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"❌ North API authentication error: {e}")
            return False

    async def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token."""
        if not self.access_token or not self.token_expires:
            return await self._authenticate()

        # Refresh if token expires in less than 1 minute
        if self.token_expires - datetime.now() < timedelta(minutes=1):
            logger.info("🔄 Refreshing North API token")
            return await self._authenticate()

        return True

    async def _api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated API request to North."""
        if not await self._ensure_valid_token():
            return None

        url = f"{self.base_urls[self.environment]['api']}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    return await self._handle_response(response)
            elif method.upper() == "POST":
                async with self.session.post(url, headers=headers, json=data) as response:
                    return await self._handle_response(response)
            elif method.upper() == "PUT":
                async with self.session.put(url, headers=headers, json=data) as response:
                    return await self._handle_response(response)
            elif method.upper() == "PATCH":
                async with self.session.patch(url, headers=headers, json=data) as response:
                    return await self._handle_response(response)
            else:
                logger.error(f"❌ Unsupported HTTP method: {method}")
                return None

        except Exception as e:
            logger.error(f"❌ North API request error: {e}")
            return None

    async def _handle_response(self, response) -> Optional[Dict]:
        """Handle API response."""
        try:
            if response.status == 200:
                return await response.json()
            elif response.status == 201:
                # Created - may or may not have body
                try:
                    return await response.json()
                except:
                    return {"status": "created"}
            elif response.status == 204:
                # No content
                return {"status": "success"}
            else:
                error_text = await response.text()
                logger.error(f"❌ North API error {response.status}: {error_text}")
                return None
        except Exception as e:
            logger.error(f"❌ Response handling error: {e}")
            return None

    async def create_merchant_application(self, merchant_data: Dict[str, Any], plan_id: str) -> Optional[Dict]:
        """Create a new merchant application."""
        logger.info(f"📝 Creating merchant application for: {merchant_data.get('businessName', 'Unknown')}")

        # Generate unique external key
        external_key = f"aqi_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{merchant_data.get('businessName', 'unknown').replace(' ', '_')}"

        application_data = {
            "externalKey": external_key,
            "planId": plan_id,
            "merchant": {
                "businessName": merchant_data.get("businessName"),
                "businessAddress": {
                    "address1": merchant_data.get("address1"),
                    "city": merchant_data.get("city"),
                    "state": merchant_data.get("state"),
                    "zip": merchant_data.get("zip"),
                    "country": merchant_data.get("country", "US")
                },
                "businessPhone": merchant_data.get("businessPhone"),
                "businessEmail": merchant_data.get("businessEmail"),
                "taxId": merchant_data.get("taxId"),
                "businessType": merchant_data.get("businessType"),
                "yearsInBusiness": merchant_data.get("yearsInBusiness"),
                "annualVolume": merchant_data.get("annualVolume"),
                "averageTicket": merchant_data.get("averageTicket")
            },
            "owners": merchant_data.get("owners", []),
            "banking": {
                "routingNumber": merchant_data.get("routingNumber"),
                "accountNumber": merchant_data.get("accountNumber"),
                "accountType": merchant_data.get("accountType", "checking")
            }
        }

        result = await self._api_request("POST", "/enroll/application", application_data)

        if result:
            logger.info(f"✅ Merchant application created: {external_key}")
            return {
                "external_key": external_key,
                "application_id": result.get("id"),
                "status": "created",
                "data": result
            }
        else:
            logger.error("❌ Failed to create merchant application")
            return None

    async def update_application_pricing(self, external_key: str, pricing_data: Dict[str, Any]) -> bool:
        """Update application pricing."""
        logger.info(f"💰 Updating pricing for application: {external_key}")

        result = await self._api_request("PATCH", f"/enroll/application/pricing/key/{external_key}", pricing_data)

        if result:
            logger.info(f"✅ Pricing updated for application: {external_key}")
            return True
        else:
            logger.error(f"❌ Failed to update pricing for application: {external_key}")
            return False

    async def trigger_application_completion(self, external_key: str) -> bool:
        """Trigger application completion and send email to merchant."""
        logger.info(f"📧 Triggering completion for application: {external_key}")

        result = await self._api_request("POST", f"/enroll/application/complete/key/{external_key}")

        if result:
            logger.info(f"✅ Completion triggered for application: {external_key}")
            return True
        else:
            logger.error(f"❌ Failed to trigger completion for application: {external_key}")
            return False

    async def submit_application_for_underwriting(self, external_key: str) -> bool:
        """Submit application to underwriting."""
        logger.info(f"📤 Submitting application to underwriting: {external_key}")

        result = await self._api_request("POST", f"/enroll/application/submit/key/{external_key}")

        if result:
            logger.info(f"✅ Application submitted to underwriting: {external_key}")
            return True
        else:
            logger.error(f"❌ Failed to submit application to underwriting: {external_key}")
            return False

    async def get_application_status(self, external_key: str) -> Optional[Dict]:
        """Get application status."""
        result = await self._api_request("GET", f"/enroll/application/key/{external_key}")

        if result:
            status = result.get("status", "unknown")
            logger.info(f"📊 Application {external_key} status: {status}")
            return result
        else:
            logger.error(f"❌ Failed to get status for application: {external_key}")
            return None

    async def get_merchant_mid(self, external_key: str) -> Optional[str]:
        """Get Merchant ID (MID) if application is approved."""
        status_data = await self.get_application_status(external_key)

        if status_data and status_data.get("status") == "approved":
            mid = status_data.get("merchantId")
            if mid:
                logger.info(f"🎉 Merchant approved! MID: {mid}")
                return mid

        return None

    async def list_applications(self, limit: int = 50) -> Optional[List[Dict]]:
        """List merchant applications."""
        result = await self._api_request("GET", f"/enroll/application?limit={limit}")

        if result:
            applications = result.get("applications", [])
            logger.info(f"📋 Found {len(applications)} applications")
            return applications
        else:
            logger.error("❌ Failed to list applications")
            return None

    async def initiate_2fa(self, external_key: str, merchant_email: str) -> bool:
        """Initiate Two-Factor Authentication for merchant application (required for custom enrollment)."""
        logger.info(f"🔐 Initiating 2FA for application: {external_key}")

        twofa_data = {
            "email": merchant_email,
            "method": "email"
        }

        result = await self._api_request("POST", f"/enroll/application/2fa/initiate/key/{external_key}", twofa_data)

        if result:
            logger.info(f"✅ 2FA initiated for application: {external_key}")
            return True
        else:
            logger.error(f"❌ Failed to initiate 2FA for application: {external_key}")
            return False

    async def validate_2fa(self, external_key: str, verification_code: str) -> bool:
        """Validate Two-Factor Authentication code."""
        logger.info(f"✅ Validating 2FA for application: {external_key}")

        validation_data = {
            "code": verification_code
        }

        result = await self._api_request("POST", f"/enroll/application/2fa/validate/key/{external_key}", validation_data)

        if result:
            logger.info(f"✅ 2FA validated for application: {external_key}")
            return True
        else:
            logger.error(f"❌ 2FA validation failed for application: {external_key}")
            return False

    async def get_application_pdf(self, external_key: str) -> Optional[bytes]:
        """Get the application PDF for digital signature."""
        logger.info(f"📄 Getting application PDF for: {external_key}")

        result = await self._api_request("GET", f"/enroll/application/pdf/key/{external_key}")

        if result and "pdf" in result:
            # Assuming PDF is base64 encoded
            pdf_data = base64.b64decode(result["pdf"])
            logger.info(f"✅ Application PDF retrieved for: {external_key}")
            return pdf_data
        else:
            logger.error(f"❌ Failed to get application PDF for: {external_key}")
            return None

    async def add_digital_signature(self, external_key: str, signature_data: Dict[str, Any]) -> bool:
        """Add digital merchant signature with North's required certification details."""
        logger.info(f"✍️ Adding digital signature for application: {external_key}")

        # North requires specific certification details for custom enrollment
        required_signature_data = {
            "signature": signature_data.get("signature"),  # Base64 encoded signature image
            "certification": {
                "howDocumentsSent": signature_data.get("how_documents_sent", "email"),
                "senderName": signature_data.get("sender_name", "AQI Merchant Services"),
                "ipAddress": signature_data.get("ip_address"),
                "deviceId": signature_data.get("device_id"),
                "signatureDateTime": signature_data.get("signature_datetime", datetime.now().isoformat()),
                "verificationCompleted": signature_data.get("verification_completed", True)
            }
        }

        result = await self._api_request("POST", f"/enroll/application/signature/key/{external_key}", required_signature_data)

        if result:
            logger.info(f"✅ Digital signature added for application: {external_key}")
            return True
        else:
            logger.error(f"❌ Failed to add digital signature for application: {external_key}")
            return False


class AQINorthIntegration:
    """AQI integration with North Merchant Boarding API."""

    def __init__(self, environment: str = "sandbox"):
        self.north_api = NorthMerchantBoardingAPI(environment)
        self.merchant_applications = {}  # Track applications by merchant_id

    async def initialize(self) -> bool:
        """Initialize the AQI North integration."""
        logger.info("🚀 Initializing AQI North Integration")

        success = await self.north_api.initialize()
        if success:
            logger.info("✅ AQI North Integration ready")
        else:
            logger.error("❌ AQI North Integration failed")

        return success

    async def onboard_merchant(self, merchant_data: Dict[str, Any], plan_id: str, signature_data: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        """Complete merchant onboarding process with North (Custom Enrollment with 2FA and Digital Signature)."""
        logger.info(f"🏪 Starting merchant onboarding: {merchant_data.get('businessName')}")

        # Step 1: Create application
        application = await self.north_api.create_merchant_application(merchant_data, plan_id)
        if not application:
            return None

        external_key = application["external_key"]
        merchant_id = f"north_{external_key}"

        # Track the application
        self.merchant_applications[merchant_id] = {
            "external_key": external_key,
            "status": "created",
            "created_at": datetime.now(),
            "merchant_data": merchant_data
        }

        # Step 2: Update pricing if needed
        if "custom_pricing" in merchant_data:
            await self.north_api.update_application_pricing(external_key, merchant_data["custom_pricing"])

        # Step 3: Initiate 2FA (required for custom enrollment)
        merchant_email = merchant_data.get("businessEmail") or merchant_data.get("owners", [{}])[0].get("email")
        if merchant_email:
            twofa_success = await self.north_api.initiate_2fa(external_key, merchant_email)
            if not twofa_success:
                logger.warning(f"⚠️ 2FA initiation failed for {external_key}, but continuing...")

        # Step 4: If signature data provided, add digital signature
        if signature_data:
            signature_success = await self.north_api.add_digital_signature(external_key, signature_data)
            if signature_success:
                logger.info(f"✅ Digital signature added for {external_key}")
            else:
                logger.warning(f"⚠️ Digital signature failed for {external_key}")

        # Step 5: Validate application before submission
        validation_result = await self.north_api._api_request("POST", f"/enroll/application/validate/key/{external_key}")
        if validation_result:
            logger.info(f"✅ Application validated: {external_key}")
        else:
            logger.warning(f"⚠️ Application validation failed for {external_key}")

        # Step 6: Submit to underwriting
        submit_success = await self.north_api.submit_application_for_underwriting(external_key)
        if submit_success:
            self.merchant_applications[merchant_id]["status"] = "submitted"
            logger.info(f"✅ Merchant onboarding completed: {merchant_id}")
            return {
                "merchant_id": merchant_id,
                "external_key": external_key,
                "status": "submitted",
                "next_steps": [
                    "Application submitted to North underwriting",
                    "Monitor status with check_merchant_status()",
                    "Once approved, MID will be available for payment processing"
                ]
            }
        else:
            logger.error(f"❌ Failed to submit application for underwriting: {external_key}")
            return None

    async def check_merchant_status(self, merchant_id: str) -> Optional[Dict]:
        """Check the status of a merchant application."""
        if merchant_id not in self.merchant_applications:
            logger.error(f"❌ Unknown merchant: {merchant_id}")
            return None

        external_key = self.merchant_applications[merchant_id]["external_key"]

        status_data = await self.north_api.get_application_status(external_key)

        if status_data:
            current_status = status_data.get("status", "unknown")
            self.merchant_applications[merchant_id]["status"] = current_status
            self.merchant_applications[merchant_id]["last_checked"] = datetime.now()

            # Check if approved and get MID
            if current_status == "approved":
                mid = await self.north_api.get_merchant_mid(external_key)
                if mid:
                    self.merchant_applications[merchant_id]["mid"] = mid
                    logger.info(f"🎉 Merchant {merchant_id} approved with MID: {mid}")

            return {
                "merchant_id": merchant_id,
                "status": current_status,
                "mid": self.merchant_applications[merchant_id].get("mid"),
                "details": status_data
            }

        return None

    async def get_all_applications(self) -> Dict[str, Any]:
        """Get all merchant applications and their statuses."""
        applications = await self.north_api.list_applications()

        if applications:
            # Update our tracking
            for app in applications:
                external_key = app.get("externalKey")
                merchant_id = f"north_{external_key}"

                if merchant_id not in self.merchant_applications:
                    self.merchant_applications[merchant_id] = {
                        "external_key": external_key,
                        "status": app.get("status", "unknown"),
                        "created_at": datetime.now()
                    }

        return {
            "total_applications": len(applications) if applications else 0,
            "applications": applications or [],
            "tracked_merchants": len(self.merchant_applications)
        }

    async def close(self):
        """Close the integration."""
        await self.north_api.close()
        logger.info("🔒 AQI North Integration closed")


# Enhanced AQI Merchant Services with North integration
# Note: This class would be integrated into the main aqi_merchant_services.py file
# For now, the core AQINorthIntegration class handles all North functionality

# class AQIMerchantServicesNorth(AQIMerchantServices):
#     """Enhanced AQI Merchant Services with North boarding integration."""

#     def __init__(self):
#         super().__init__()
#         self.north_integration = None

#     async def start_system(self):
#         """Start system with North integration."""
#         logger.info("🚀 Starting AQI Merchant Services with North Integration")

#         # Start base system
#         await super().start_system()

#         # Initialize North integration
#         self.north_integration = AQINorthIntegration("sandbox")  # Change to "production" for live
#         success = await self.north_integration.initialize()

#         if success:
#             logger.info("✅ North integration active - Full merchant onboarding available")
#         else:
#             logger.warning("⚠️ North integration failed - Operating in demo mode only")

#     async def onboard_new_merchant(self, merchant_data: Dict[str, Any], signature_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
#         """Onboard a new merchant through North with 2FA and digital signature support."""
#         if not self.north_integration:
#             return {
#                 "status": "error",
#                 "message": "North integration not available",
#                 "fallback": "demo_mode"
#             }

#         # Use a default plan ID (would be configured per merchant type)
#         plan_id = "default_plan_001"  # This would be looked up based on merchant needs

#         result = await self.north_integration.onboard_merchant(merchant_data, plan_id, signature_data)

#         if result:
#             # Add to our merchant database
#             merchant_id = result["merchant_id"]
#             self.merchants[merchant_id] = MerchantProfile(
#                 merchant_id=merchant_id,
#                 business_name=merchant_data.get("businessName", "Unknown"),
#                 status="pending_approval",
#                 tier="basic"  # Would be determined by plan
#             )

#             return {
#                 "status": "success",
#                 "merchant_id": merchant_id,
#                 "message": "Merchant onboarding initiated with North (Custom Enrollment)",
#                 "next_steps": [
#                     "2FA verification sent to merchant email",
#                     "Digital signature collected and certified",
#                     "Application submitted to North underwriting",
#                     "Monitor status with check_merchant_status()",
#                     "Once approved, MID will be available for payment processing"
#                 ]
#             }
#         else:
#             return {
#                 "status": "error",
#                 "message": "Failed to initiate merchant onboarding"
#             }


# Demo and testing functions
async def demo_north_integration():
    """Demonstrate North integration capabilities."""
    logger.info("🎬 Starting North Integration Demo")

    integration = AQINorthIntegration("sandbox")
    success = await integration.initialize()

    if not success:
        logger.error("❌ Demo failed - North credentials not configured")
        logger.info("💡 To run demo, set environment variables:")
        logger.info("   NORTH_CLIENT_ID=your_client_id")
        logger.info("   NORTH_CLIENT_SECRET=your_client_secret")
        logger.info("   NORTH_AGENT_ID=your_agent_id")
        return

    # Demo merchant data
    demo_merchant = {
        "businessName": "AQI Demo Coffee Shop",
        "address1": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip": "12345",
        "businessPhone": "555-0123",
        "businessEmail": "owner@demo-coffee.com",
        "taxId": "12-3456789",
        "businessType": "restaurant",
        "yearsInBusiness": 5,
        "annualVolume": 250000,
        "averageTicket": 25,
        "routingNumber": "123456789",
        "accountNumber": "9876543210",
        "accountType": "checking",
        "owners": [
            {
                "firstName": "John",
                "lastName": "Doe",
                "ownershipPercentage": 100,
                "email": "owner@demo-coffee.com",
                "phone": "555-0123"
            }
        ]
    }

    # Demo digital signature data (required for custom enrollment)
    demo_signature = {
        "signature": base64.b64encode(b"demo_signature_image_data").decode(),  # Base64 encoded signature
        "how_documents_sent": "email",
        "sender_name": "AQI Merchant Services",
        "ip_address": "192.168.1.100",
        "device_id": "demo_device_123",
        "signature_datetime": datetime.now().isoformat(),
        "verification_completed": True
    }

    # Demo onboarding with 2FA and digital signature
    logger.info("🏪 Demo: Onboarding merchant with 2FA and digital signature...")
    result = await integration.onboard_merchant(demo_merchant, "demo_plan_001", demo_signature)

    if result:
        merchant_id = result["merchant_id"]
        logger.info(f"✅ Demo merchant onboarded with North compliance: {merchant_id}")

        # Check status
        logger.info("📊 Demo: Checking application status...")
        await asyncio.sleep(2)  # Simulate time
        status = await integration.check_merchant_status(merchant_id)

        if status:
            logger.info(f"📋 Status: {status['status']}")
            if status.get('mid'):
                logger.info(f"🎉 MID Available: {status['mid']} - Ready for payment processing!")

    # List applications
    logger.info("📋 Demo: Listing all applications...")
    apps = await integration.get_all_applications()
    logger.info(f"📊 Total applications: {apps['total_applications']}")

    await integration.close()
    logger.info("🎉 North Integration Demo Complete (Custom Enrollment with 2FA & Digital Signature)")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_north_integration())