"""
AQI Agent Passkey Authentication System
Integrates Twilio Verify Passkeys for secure agent leasing and management
"""

import os
import json
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import base64
import secrets

class AQIPasskeyManager:
    """
    Manages Passkey authentication for AQI Agent leasing platform
    """

    def __init__(self):
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.verify_service_sid = None  # Will be created
        self.base_url = "https://verify.twilio.com/v2"

        # AQI-specific configuration
        self.relying_party = {
            "id": "aqi-agents.scottdevinc.com",  # Replace with actual domain
            "name": "AQI Autonomous Agents",
            "origins": [
                "https://aqi-agents.scottdevinc.com",
                "https://app.aqi-agents.scottdevinc.com"
            ]
        }

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get Twilio authentication headers"""
        credentials = base64.b64encode(
            f"{self.account_sid}:{self.auth_token}".encode()
        ).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def create_passkey_service(self, service_name: str = "AQI Agent Leasing") -> Dict:
        """
        Create a new Passkey-enabled Verify service for AQI Agents
        """
        url = f"{self.base_url}/Services"

        data = {
            "Name": service_name,
            "Passkeys.RelyingParty.Id": self.relying_party["id"],
            "Passkeys.RelyingParty.Name": self.relying_party["name"],
            "Passkeys.RelyingParty.Origins": ",".join(self.relying_party["origins"]),
            "Passkeys.AuthenticatorAttachment": "any",  # Allow both platform and cross-platform
            "Passkeys.DiscoverableCredentials": "preferred",
            "Passkeys.UserVerification": "required"  # Require user verification for security
        }

        response = requests.post(url, headers=self._get_auth_headers(), data=data)

        if response.status_code == 201:
            service_data = response.json()
            self.verify_service_sid = service_data["sid"]
            print(f"✅ Created Passkey service: {service_data['sid']}")
            return service_data
        else:
            raise Exception(f"Failed to create service: {response.text}")

    def create_passkey_factor(self, identity: str, friendly_name: str) -> Dict:
        """
        Create a Passkey factor for user registration
        """
        if not self.verify_service_sid:
            raise Exception("Verify service not initialized")

        url = f"{self.base_url}/Services/{self.verify_service_sid}/Passkeys/Factors"

        data = {
            "friendly_name": friendly_name,
            "identity": identity,
            "config.authenticator_attachment": "any",
            "config.discoverable_credentials": "preferred",
            "config.user_verification": "required"
        }

        response = requests.post(url, headers={
            "Authorization": f"Basic {base64.b64encode(f'{self.account_sid}:{self.auth_token}'.encode()).decode()}",
            "Content-Type": "application/json"
        }, json=data)

        if response.status_code == 201:
            factor_data = response.json()
            print(f"✅ Created Passkey factor for {identity}")
            return factor_data
        else:
            raise Exception(f"Failed to create factor: {response.text}")

    def verify_passkey_registration(self, factor_sid: str, credential_data: Dict) -> Dict:
        """
        Verify Passkey registration with credential data from browser
        """
        if not self.verify_service_sid:
            raise Exception("Verify service not initialized")

        url = f"{self.base_url}/Services/{self.verify_service_sid}/Passkeys/VerifyFactor"

        # Extract credential components
        data = {
            "id": credential_data.get("id"),
            "keyId": credential_data.get("rawId"),
            "authenticatorAttachment": credential_data.get("authenticatorAttachment", "platform"),
            "type": credential_data.get("type", "public-key"),
            "response": {
                "clientDataJSON": credential_data["response"]["clientDataJSON"],
                "attestationObject": credential_data["response"]["attestationObject"],
                "transports": credential_data["response"].get("transports", [])
            }
        }

        response = requests.post(url, headers={
            "Authorization": f"Basic {base64.b64encode(f'{self.account_sid}:{self.auth_token}'.encode()).decode()}",
            "Content-Type": "application/json"
        }, json=data)

        if response.status_code == 200:
            verification_data = response.json()
            print(f"✅ Verified Passkey registration for factor {factor_sid}")
            return verification_data
        else:
            raise Exception(f"Failed to verify Passkey: {response.text}")

    def create_authentication_challenge(self, identity: str) -> Dict:
        """
        Create authentication challenge for Passkey login
        """
        if not self.verify_service_sid:
            raise Exception("Verify service not initialized")

        url = f"{self.base_url}/Services/{self.verify_service_sid}/Passkeys/Challenges"

        data = {"identity": identity}

        response = requests.post(url, headers={
            "Authorization": f"Basic {base64.b64encode(f'{self.account_sid}:{self.auth_token}'.encode()).decode()}",
            "Content-Type": "application/json"
        }, json=data)

        if response.status_code == 201:
            challenge_data = response.json()
            print(f"✅ Created authentication challenge for {identity}")
            return challenge_data
        else:
            raise Exception(f"Failed to create challenge: {response.text}")

    def approve_authentication_challenge(self, challenge_data: Dict) -> Dict:
        """
        Approve authentication challenge with signed credential
        """
        if not self.verify_service_sid:
            raise Exception("Verify service not initialized")

        url = f"{self.base_url}/Services/{self.verify_service_sid}/Passkeys/ApproveChallenge"

        data = {
            "id": challenge_data.get("id"),
            "rawId": challenge_data.get("rawId"),
            "authenticatorAttachment": challenge_data.get("authenticatorAttachment", "platform"),
            "type": challenge_data.get("type", "public-key"),
            "response": {
                "authenticatorData": challenge_data["response"]["authenticatorData"],
                "clientDataJSON": challenge_data["response"]["clientDataJSON"],
                "signature": challenge_data["response"]["signature"],
                "userHandle": challenge_data["response"].get("userHandle")
            }
        }

        response = requests.post(url, headers={
            "Authorization": f"Basic {base64.b64encode(f'{self.account_sid}:{self.auth_token}'.encode()).decode()}",
            "Content-Type": "application/json"
        }, json=data)

        if response.status_code == 200:
            approval_data = response.json()
            print(f"✅ Approved authentication challenge")
            return approval_data
        else:
            raise Exception(f"Failed to approve challenge: {response.text}")

    def get_service_info(self) -> Dict:
        """
        Get current Verify service information
        """
        if not self.verify_service_sid:
            raise Exception("Verify service not initialized")

        url = f"{self.base_url}/Services/{self.verify_service_sid}"

        response = requests.get(url, headers=self._get_auth_headers())

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get service info: {response.text}")

class AQIAgentLeasingAuth:
    """
    AQI Agent leasing authentication with Passkey integration
    """

    def __init__(self):
        self.passkey_manager = AQIPasskeyManager()
        self.active_sessions = {}  # In production, use Redis/database

    def register_user_passkey(self, user_id: str, user_email: str) -> Dict:
        """
        Register a new user with Passkey authentication
        """
        try:
            # Create Passkey factor
            factor = self.passkey_manager.create_passkey_factor(
                identity=user_id,
                friendly_name=f"AQI Agent Leasing - {user_email}"
            )

            return {
                "status": "registration_initiated",
                "user_id": user_id,
                "factor_sid": factor["sid"],
                "challenge_options": factor["options"],
                "message": "Passkey registration initiated. Complete in browser."
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Registration failed: {str(e)}"
            }

    def complete_passkey_registration(self, user_id: str, credential_data: Dict) -> Dict:
        """
        Complete Passkey registration with browser credential
        """
        try:
            # Find the user's factor (in production, store factor_sid)
            # For demo, we'll assume we have it or search
            factor_sid = credential_data.get("factor_sid")  # Would be stored from registration

            verification = self.passkey_manager.verify_passkey_registration(
                factor_sid=factor_sid,
                credential_data=credential_data
            )

            if verification["status"] == "verified":
                return {
                    "status": "registration_complete",
                    "user_id": user_id,
                    "message": "Passkey registration successful"
                }
            else:
                return {
                    "status": "verification_pending",
                    "message": "Passkey verification in progress"
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Verification failed: {str(e)}"
            }

    def authenticate_user(self, user_id: str) -> Dict:
        """
        Start Passkey authentication for user login
        """
        try:
            challenge = self.passkey_manager.create_authentication_challenge(identity=user_id)

            # Store challenge for verification (in production, use database)
            session_id = secrets.token_urlsafe(32)
            self.active_sessions[session_id] = {
                "user_id": user_id,
                "challenge_sid": challenge["sid"],
                "expires": datetime.utcnow() + timedelta(minutes=5)
            }

            return {
                "status": "authentication_initiated",
                "session_id": session_id,
                "challenge_options": challenge["options"],
                "message": "Please authenticate with your Passkey"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Authentication initiation failed: {str(e)}"
            }

    def complete_authentication(self, session_id: str, credential_data: Dict) -> Dict:
        """
        Complete authentication with signed challenge
        """
        try:
            if session_id not in self.active_sessions:
                return {"status": "error", "message": "Invalid session"}

            session = self.active_sessions[session_id]

            if datetime.utcnow() > session["expires"]:
                del self.active_sessions[session_id]
                return {"status": "error", "message": "Session expired"}

            approval = self.passkey_manager.approve_authentication_challenge(credential_data)

            if approval["status"] == "approved":
                del self.active_sessions[session_id]
                return {
                    "status": "authenticated",
                    "user_id": session["user_id"],
                    "message": "Authentication successful",
                    "token": secrets.token_urlsafe(64)  # JWT token in production
                }
            else:
                return {
                    "status": "authentication_failed",
                    "message": "Passkey authentication failed"
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Authentication completion failed: {str(e)}"
            }

# WebAuthn helper functions for browser integration
WEB_AUTHN_HELPER = """
// Load WebAuthn helper library
const { create, get, parseCreationOptionsFromJSON, parseRequestOptionsFromJSON } = await
import('https://cdn.jsdelivr.net/npm/@github/webauthn-json/dist/esm/webauthn-json.browser-ponyfill.js');

// Register Passkey function
async function registerPasskey(challengeOptions) {
    try {
        const creationOptions = parseCreationOptionsFromJSON(challengeOptions);
        const credential = await create(creationOptions);
        return credential;
    } catch (error) {
        console.error('Passkey registration failed:', error);
        throw error;
    }
}

// Authenticate with Passkey function
async function authenticatePasskey(challengeOptions) {
    try {
        const requestOptions = parseRequestOptionsFromJSON(challengeOptions);
        const credential = await get(requestOptions);
        return credential;
    } catch (error) {
        console.error('Passkey authentication failed:', error);
        throw error;
    }
}

// Export functions for use in your app
window.AQIPasskeyAuth = {
    registerPasskey,
    authenticatePasskey
};
"""

if __name__ == "__main__":
    # Initialize AQI Passkey system
    auth_system = AQIAgentLeasingAuth()

    # Create Passkey service (run once)
    try:
        service = auth_system.passkey_manager.create_passkey_service()
        print(f"Service created: {service['sid']}")
    except Exception as e:
        print(f"Service creation failed: {e}")

    # Example usage
    print("\\n=== AQI Passkey Authentication System Ready ===")
    print("Use the AQIAgentLeasingAuth class to integrate Passkey authentication")
    print("into your AQI Agent leasing platform.")</content>
<parameter name="filePath">C:\Users\signa\OneDrive\Desktop\AQI North Connector\aqi_passkey_auth.py