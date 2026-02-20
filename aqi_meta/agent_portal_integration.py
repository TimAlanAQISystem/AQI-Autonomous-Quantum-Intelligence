"""
AQI Agent Portal Integration
============================

Complete integration module for AQI backend to connect with Agent Portal API.

Features:
- OAuth2 client credentials authentication with automatic token refresh
- Webhook handler with HMAC-SHA256 signature validation
- REST API client for merchant and transaction operations
- SOC2 compliant security and audit logging
- Integration with AQI's relational backprop governance system

Created: December 15, 2025
Author: TimAlanAQISystem
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

import aiohttp
import requests
from cryptography.fernet import Fernet
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentPortalConfig:
    """Configuration for Agent Portal integration."""
    base_url: str
    client_id: str
    client_secret: str
    scopes: List[str] = field(default_factory=lambda: [
        "merchants:read", "merchants:write", "transactions:read", "webhooks:manage"
    ])
    webhook_secret: str = ""
    callback_url: str = "https://api.aqi-system.com/webhooks/agent-portal/v1/events"
    token_refresh_buffer: int = 300  # 5 minutes before expiry
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 30


@dataclass
class OAuth2Token:
    """OAuth2 token with metadata."""
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    issued_at: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        expiry_time = self.issued_at + timedelta(seconds=self.expires_in)
        return datetime.now() >= expiry_time

    @property
    def expires_soon(self, buffer_seconds: int = 300) -> bool:
        """Check if token expires soon (within buffer)."""
        expiry_time = self.issued_at + timedelta(seconds=self.expires_in - buffer_seconds)
        return datetime.now() >= expiry_time


class SecureTokenStorage:
    """Encrypted token storage using Fernet encryption."""

    def __init__(self, encryption_key: str):
        """Initialize with base64-encoded Fernet key."""
        self.cipher = Fernet(encryption_key.encode())

    def store_token(self, token: OAuth2Token) -> None:
        """Encrypt and store token data."""
        token_data = {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "expires_in": token.expires_in,
            "scope": token.scope,
            "issued_at": token.issued_at.isoformat()
        }
        encrypted_data = self.cipher.encrypt(json.dumps(token_data).encode())
        with open("agent_portal_token.enc", "wb") as f:
            f.write(encrypted_data)

    def load_token(self) -> Optional[OAuth2Token]:
        """Load and decrypt token data."""
        try:
            with open("agent_portal_token.enc", "rb") as f:
                encrypted_data = f.read()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            token_data = json.loads(decrypted_data.decode())

            return OAuth2Token(
                access_token=token_data["access_token"],
                token_type=token_data["token_type"],
                expires_in=token_data["expires_in"],
                scope=token_data["scope"],
                issued_at=datetime.fromisoformat(token_data["issued_at"])
            )
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            return None

    def clear_token(self) -> None:
        """Remove stored token."""
        try:
            import os
            os.remove("agent_portal_token.enc")
        except FileNotFoundError:
            pass


class OAuth2Client:
    """OAuth2 client credentials flow implementation."""

    def __init__(self, config: AgentPortalConfig, token_storage: SecureTokenStorage):
        self.config = config
        self.token_storage = token_storage
        self._token: Optional[OAuth2Token] = None

    async def get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary."""
        # Load existing token
        if not self._token:
            self._token = self.token_storage.load_token()

        # Check if token needs refresh
        if not self._token or self._token.is_expired or self._token.expires_soon(self.config.token_refresh_buffer):
            await self._refresh_token()

        return f"{self._token.token_type} {self._token.access_token}"

    async def _refresh_token(self) -> None:
        """Perform OAuth2 token refresh."""
        logger.info("Refreshing OAuth2 token")

        token_url = f"{self.config.base_url}/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": " ".join(self.config.scopes)
        }

        async with aiohttp.ClientSession() as session:
            for attempt in range(self.config.max_retries):
                try:
                    async with session.post(
                        token_url,
                        data=data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                    ) as response:
                        if response.status == 200:
                            token_data = await response.json()
                            self._token = OAuth2Token(
                                access_token=token_data["access_token"],
                                token_type=token_data["token_type"],
                                expires_in=token_data["expires_in"],
                                scope=token_data.get("scope", "")
                            )
                            self.token_storage.store_token(self._token)
                            logger.info("OAuth2 token refreshed successfully")
                            return
                        else:
                            error_text = await response.text()
                            logger.warning(f"Token refresh failed (attempt {attempt + 1}): {response.status} - {error_text}")

                except Exception as e:
                    logger.warning(f"Token refresh error (attempt {attempt + 1}): {e}")

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))

        raise Exception("Failed to refresh OAuth2 token after all retries")


class WebhookHandler:
    """Webhook handler with HMAC signature validation."""

    def __init__(self, config: AgentPortalConfig):
        self.config = config
        self.event_handlers: Dict[str, Callable] = {}

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register handler for specific event type."""
        self.event_handlers[event_type] = handler

    def validate_signature(self, payload: str, signature: str) -> bool:
        """Validate HMAC-SHA256 signature."""
        if not self.config.webhook_secret:
            logger.warning("No webhook secret configured - signature validation disabled")
            return True

        expected_signature = hmac.new(
            self.config.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected_signature}", signature)

    async def handle_webhook(self, request_data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Process incoming webhook with validation."""
        try:
            # Extract signature
            signature = headers.get("X-AgentPortal-Signature", "")
            if not signature:
                return {"status": "error", "message": "Missing signature header"}

            # Validate signature
            payload_str = json.dumps(request_data, separators=(',', ':'))
            if not self.validate_signature(payload_str, signature):
                logger.warning("Invalid webhook signature")
                return {"status": "error", "message": "Invalid signature"}

            # Process event
            event_type = request_data.get("event_type", "")
            event_data = request_data.get("data", {})

            logger.info(f"Processing webhook event: {event_type}")

            # Route to appropriate handler
            if event_type in self.event_handlers:
                await self.event_handlers[event_type](event_data)
                return {"status": "success", "message": f"Event {event_type} processed"}
            else:
                logger.warning(f"No handler registered for event type: {event_type}")
                return {"status": "success", "message": f"Event {event_type} received (no handler)"}

        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            return {"status": "error", "message": "Internal processing error"}


class AgentPortalAPIClient:
    """REST API client for Agent Portal operations."""

    def __init__(self, config: AgentPortalConfig, oauth_client: OAuth2Client):
        self.config = config
        self.oauth_client = oauth_client
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request with retry logic."""
        url = f"{self.config.base_url}/api/v1{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = await self.oauth_client.get_access_token()
        headers["Content-Type"] = "application/json"

        for attempt in range(self.config.max_retries):
            try:
                async with self.session.request(
                    method, url, headers=headers, **kwargs
                ) as response:
                    response_data = await response.json()

                    if response.status == 200:
                        return response_data
                    elif response.status == 401:
                        # Token might be expired, refresh and retry
                        logger.info("Token expired, refreshing...")
                        await self.oauth_client._refresh_token()
                        headers["Authorization"] = await self.oauth_client.get_access_token()
                        continue
                    else:
                        logger.warning(f"API request failed: {response.status} - {response_data}")
                        if attempt == self.config.max_retries - 1:
                            raise Exception(f"API request failed: {response.status}")

            except Exception as e:
                logger.warning(f"API request error (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    raise

        raise Exception("API request failed after all retries")

    # Merchant Operations
    async def get_merchant(self, merchant_id: str) -> Dict[str, Any]:
        """Get merchant details."""
        return await self._make_request("GET", f"/merchants/{merchant_id}")

    async def list_merchants(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List merchants with optional filtering."""
        params = {"limit": limit}
        if status:
            params["status"] = status
        return await self._make_request("GET", "/merchants", params=params)

    async def update_merchant_status(self, merchant_id: str, status: str, notes: str = "") -> Dict[str, Any]:
        """Update merchant status."""
        data = {"status": status, "notes": notes, "updated_by": "AQI_SYSTEM"}
        return await self._make_request("PATCH", f"/merchants/{merchant_id}/status", json=data)

    # Transaction Operations
    async def get_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Get transaction details."""
        return await self._make_request("GET", f"/transactions/{transaction_id}")

    async def list_merchant_transactions(self, merchant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List transactions for a merchant."""
        params = {"merchant_id": merchant_id, "limit": limit}
        return await self._make_request("GET", "/transactions", params=params)

    # Webhook Configuration
    async def register_webhook(self, events: List[str]) -> Dict[str, Any]:
        """Register webhook endpoint."""
        data = {
            "url": self.config.callback_url,
            "events": events,
            "active": True
        }
        return await self._make_request("POST", "/webhooks", json=data)

    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """List configured webhooks."""
        return await self._make_request("GET", "/webhooks")


class AgentPortalIntegration:
    """Complete Agent Portal integration for AQI system."""

    def __init__(self, config: AgentPortalConfig):
        # Generate encryption key for token storage
        self.encryption_key = base64.urlsafe_b64encode(
            config.client_secret[:32].ljust(32, '0').encode()
        ).decode()

        self.config = config
        self.token_storage = SecureTokenStorage(self.encryption_key)
        self.oauth_client = OAuth2Client(config, self.token_storage)
        self.webhook_handler = WebhookHandler(config)
        self.api_client = AgentPortalAPIClient(config, self.oauth_client)

        # Register default event handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default webhook event handlers."""

        async def handle_merchant_status_update(data: Dict[str, Any]):
            """Handle merchant status update events."""
            merchant_id = data.get("merchant_id")
            new_status = data.get("status")
            logger.info(f"Merchant {merchant_id} status updated to: {new_status}")

            # Here you would integrate with AQI's relational backprop system
            # to trigger appropriate responses based on the status change

        async def handle_transaction_update(data: Dict[str, Any]):
            """Handle transaction status updates."""
            transaction_id = data.get("transaction_id")
            status = data.get("status")
            logger.info(f"Transaction {transaction_id} status: {status}")

            # Integrate with AQI support automation

        self.webhook_handler.register_event_handler("merchant.status_update", handle_merchant_status_update)
        self.webhook_handler.register_event_handler("transaction.update", handle_transaction_update)

    async def initialize(self):
        """Initialize the integration."""
        logger.info("Initializing Agent Portal integration")

        # Test OAuth2 connection
        try:
            token = await self.oauth_client.get_access_token()
            logger.info("OAuth2 authentication successful")
        except Exception as e:
            logger.error(f"OAuth2 initialization failed: {e}")
            raise

        # Register webhooks
        try:
            async with self.api_client:
                webhook_result = await self.api_client.register_webhook([
                    "merchant.status_update",
                    "merchant.approval",
                    "merchant.decline",
                    "transaction.confirmation",
                    "transaction.failure"
                ])
            logger.info(f"Webhook registration successful: {webhook_result}")
        except Exception as e:
            logger.error(f"Webhook registration failed: {e}")
            raise

    async def process_webhook(self, request_data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Process incoming webhook."""
        return await self.webhook_handler.handle_webhook(request_data, headers)

    async def get_merchant_support_data(self, merchant_id: str) -> Dict[str, Any]:
        """Get comprehensive merchant data for support automation."""
        async with self.api_client:
            merchant = await self.api_client.get_merchant(merchant_id)
            transactions = await self.api_client.list_merchant_transactions(merchant_id, limit=10)

        return {
            "merchant": merchant,
            "recent_transactions": transactions,
            "support_context": self._generate_support_context(merchant, transactions)
        }

    def _generate_support_context(self, merchant: Dict[str, Any], transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate context for AQI support automation."""
        status = merchant.get("status", "unknown")
        recent_failures = [t for t in transactions if t.get("status") == "failed"]

        risk_level = "low"
        if status in ["suspended", "pending"]:
            risk_level = "high"
        elif recent_failures:
            risk_level = "medium"

        return {
            "risk_level": risk_level,
            "recent_failures": len(recent_failures),
            "merchant_status": status,
            "recommendations": self._get_support_recommendations(risk_level, merchant)
        }

    def _get_support_recommendations(self, risk_level: str, merchant: Dict[str, Any]) -> List[str]:
        """Generate support recommendations based on risk level."""
        recommendations = []

        if risk_level == "high":
            recommendations.extend([
                "Immediate human review required",
                "Escalate to compliance team",
                "Pause automated responses"
            ])
        elif risk_level == "medium":
            recommendations.extend([
                "Monitor transaction patterns",
                "Offer additional verification support",
                "Schedule follow-up check"
            ])
        else:
            recommendations.extend([
                "Standard automated support appropriate",
                "Proactive success messaging",
                "Offer upsell opportunities"
            ])

        return recommendations

    async def update_merchant_from_aqi_decision(self, merchant_id: str, decision: Dict[str, Any]) -> bool:
        """Update merchant status based on AQI decision."""
        try:
            async with self.api_client:
                result = await self.api_client.update_merchant_status(
                    merchant_id=merchant_id,
                    status=decision.get("new_status", "active"),
                    notes=f"AQI Decision: {decision.get('reason', 'Automated update')}"
                )
            logger.info(f"Merchant {merchant_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update merchant {merchant_id}: {e}")
            return False


# Integration with AQI Relational Backprop System
class AQIAgentPortalBridge:
    """Bridge between Agent Portal integration and AQI's relational backprop system."""

    def __init__(self, agent_portal: AgentPortalIntegration, backprop_system):
        self.agent_portal = agent_portal
        self.backprop_system = backprop_system

    async def handle_merchant_interaction(self, merchant_id: str, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process merchant interaction through AQI with Agent Portal data."""

        # Get merchant context from Agent Portal
        merchant_data = await self.agent_portal.get_merchant_support_data(merchant_id)

        # Enrich interaction with Agent Portal context
        enriched_interaction = {
            **interaction_data,
            "merchant_context": merchant_data,
            "agent_portal_data": {
                "risk_level": merchant_data["support_context"]["risk_level"],
                "merchant_status": merchant_data["merchant"]["status"]
            }
        }

        # Process through AQI agents (this would integrate with your existing agent system)
        aqi_response = await self._process_with_aqi_agents(enriched_interaction)

        # Create trace for relational backprop
        signal_id = f"merchant_{merchant_id}_{interaction_data.get('timestamp', datetime.now().isoformat())}"

        trace = self.backprop_system.start_trace(signal_id, enriched_interaction)

        # Add processing steps (would integrate with your actual agent modules)
        # ... processing steps ...

        # Generate final response
        final_response = {
            "reply_text": aqi_response.get("response", ""),
            "template_id": aqi_response.get("template", ""),
            "policy_rules": aqi_response.get("policies", [])
        }

        self.backprop_system.complete_trace(signal_id, final_response)

        # Apply any AQI decisions back to Agent Portal
        if "status_update" in aqi_response:
            await self.agent_portal.update_merchant_from_aqi_decision(merchant_id, aqi_response["status_update"])

        return final_response

    async def _process_with_aqi_agents(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process interaction through AQI agent system."""
        # This would integrate with your existing AQI agent orchestration
        # For now, return a placeholder response
        return {
            "response": "Thank you for your inquiry. We're here to help you succeed.",
            "template": "support_empathetic_v1",
            "policies": ["merchant_protection", "clear_communication"]
        }


# Configuration and Initialization
def create_agent_portal_integration(config_data: Dict[str, Any]) -> AgentPortalIntegration:
    """Factory function to create Agent Portal integration."""

    config = AgentPortalConfig(
        base_url=config_data["base_url"],
        client_id=config_data["client_id"],
        client_secret=config_data["client_secret"],
        scopes=config_data.get("scopes", ["merchants:read", "merchants:write", "transactions:read", "webhooks:manage"]),
        webhook_secret=config_data.get("webhook_secret", ""),
        callback_url=config_data.get("callback_url", "https://api.aqi-system.com/webhooks/agent-portal/v1/events")
    )

    return AgentPortalIntegration(config)


# Example usage and testing
async def example_integration():
    """Example of how to use the Agent Portal integration."""

    # Configuration (would come from secure config)
    config_data = {
        "base_url": "https://api.agentportal.com",
        "client_id": "your_client_id",
        "client_secret": "your_client_secret",
        "webhook_secret": "your_webhook_secret"
    }

    # Create integration
    integration = create_agent_portal_integration(config_data)

    # Initialize (test connections, register webhooks)
    await integration.initialize()

    # Example: Process a webhook
    webhook_payload = {
        "event_type": "merchant.status_update",
        "data": {
            "merchant_id": "12345",
            "status": "approved",
            "timestamp": "2025-12-15T10:00:00Z"
        }
    }

    webhook_headers = {
        "X-AgentPortal-Signature": "sha256=signature_here"
    }

    result = await integration.process_webhook(webhook_payload, webhook_headers)
    print(f"Webhook processing result: {result}")

    # Example: Get merchant data for support
    async with integration.api_client:
        merchant_data = await integration.get_merchant_support_data("12345")
        print(f"Merchant support data: {merchant_data}")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_integration())