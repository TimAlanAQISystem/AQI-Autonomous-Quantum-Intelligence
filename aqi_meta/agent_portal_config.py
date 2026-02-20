"""
AQI Agent Portal Integration - Configuration and Deployment
==========================================================

Configuration management and deployment utilities for the Agent Portal integration.

Includes:
- Secure configuration management
- Environment-specific settings
- Deployment validation
- Integration testing utilities

Created: December 15, 2025
Author: TimAlanAQISystem
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration."""
    name: str
    base_url: str
    client_id: str
    client_secret: str
    webhook_secret: str
    callback_url: str
    log_level: str = "INFO"
    enable_audit_logging: bool = True
    rate_limit_requests_per_minute: int = 60


class SecureConfigManager:
    """Secure configuration management with environment variable integration."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self._config_cache: Dict[str, EnvironmentConfig] = {}

    def load_environment_config(self, environment: str = "sandbox") -> EnvironmentConfig:
        """Load configuration for specific environment."""

        if environment in self._config_cache:
            return self._config_cache[environment]

        # Try environment variables first (most secure)
        config = self._load_from_env(environment)

        if not config:
            # Fall back to config file
            config = self._load_from_file(environment)

        if not config:
            raise ValueError(f"No configuration found for environment: {environment}")

        self._config_cache[environment] = config
        return config

    def _load_from_env(self, environment: str) -> Optional[EnvironmentConfig]:
        """Load configuration from environment variables."""
        prefix = f"AQI_AGENT_PORTAL_{environment.upper()}_"

        try:
            return EnvironmentConfig(
                name=environment,
                base_url=os.getenv(f"{prefix}BASE_URL", ""),
                client_id=os.getenv(f"{prefix}CLIENT_ID", ""),
                client_secret=os.getenv(f"{prefix}CLIENT_SECRET", ""),
                webhook_secret=os.getenv(f"{prefix}WEBHOOK_SECRET", ""),
                callback_url=os.getenv(f"{prefix}CALLBACK_URL", "https://api.aqi-system.com/webhooks/agent-portal/v1/events"),
                log_level=os.getenv(f"{prefix}LOG_LEVEL", "INFO"),
                enable_audit_logging=os.getenv(f"{prefix}AUDIT_LOGGING", "true").lower() == "true",
                rate_limit_requests_per_minute=int(os.getenv(f"{prefix}RATE_LIMIT", "60"))
            )
        except (ValueError, TypeError):
            return None

    def _load_from_file(self, environment: str) -> Optional[EnvironmentConfig]:
        """Load configuration from encrypted file."""
        config_file = self.config_dir / f"agent_portal_{environment}.json"

        if not config_file.exists():
            return None

        try:
            with open(config_file, 'r') as f:
                data = json.load(f)

            return EnvironmentConfig(
                name=environment,
                base_url=data["base_url"],
                client_id=data["client_id"],
                client_secret=data["client_secret"],
                webhook_secret=data["webhook_secret"],
                callback_url=data.get("callback_url", "https://api.aqi-system.com/webhooks/agent-portal/v1/events"),
                log_level=data.get("log_level", "INFO"),
                enable_audit_logging=data.get("enable_audit_logging", True),
                rate_limit_requests_per_minute=data.get("rate_limit_requests_per_minute", 60)
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def save_environment_config(self, config: EnvironmentConfig) -> None:
        """Save configuration to file (for development only - use env vars in production)."""
        config_file = self.config_dir / f"agent_portal_{config.name}.json"

        data = {
            "base_url": config.base_url,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "webhook_secret": config.webhook_secret,
            "callback_url": config.callback_url,
            "log_level": config.log_level,
            "enable_audit_logging": config.enable_audit_logging,
            "rate_limit_requests_per_minute": config.rate_limit_requests_per_minute
        }

        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.warning(f"Configuration saved to {config_file} - NOT recommended for production!")


class IntegrationValidator:
    """Validation utilities for the Agent Portal integration."""

    def __init__(self, integration):
        self.integration = integration

    async def validate_oauth2_connection(self) -> Dict[str, Any]:
        """Validate OAuth2 connection and token refresh."""
        try:
            token = await self.integration.oauth_client.get_access_token()
            return {
                "status": "success",
                "message": "OAuth2 connection validated",
                "token_preview": f"{token[:20]}..." if token else "No token"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"OAuth2 validation failed: {e}"
            }

    async def validate_api_endpoints(self) -> Dict[str, Any]:
        """Validate API endpoints are accessible."""
        results = {}

        try:
            async with self.integration.api_client:
                # Test merchants endpoint
                merchants = await self.integration.api_client.list_merchants(limit=1)
                results["merchants_api"] = {
                    "status": "success",
                    "message": f"Found {len(merchants)} merchants"
                }
        except Exception as e:
            results["merchants_api"] = {
                "status": "error",
                "message": f"Merchants API failed: {e}"
            }

        try:
            async with self.integration.api_client:
                # Test webhooks endpoint
                webhooks = await self.integration.api_client.list_webhooks()
                results["webhooks_api"] = {
                    "status": "success",
                    "message": f"Found {len(webhooks)} webhooks"
                }
        except Exception as e:
            results["webhooks_api"] = {
                "status": "error",
                "message": f"Webhooks API failed: {e}"
            }

        return results

    async def validate_webhook_signature(self, test_payload: str = None) -> Dict[str, Any]:
        """Validate webhook signature verification."""
        if not test_payload:
            test_payload = json.dumps({
                "event_type": "test",
                "data": {"test": True}
            })

        # Generate test signature
        import hmac
        import hashlib
        expected_signature = hmac.new(
            self.integration.config.webhook_secret.encode(),
            test_payload.encode(),
            hashlib.sha256
        ).hexdigest()

        # Test validation
        is_valid = self.integration.webhook_handler.validate_signature(
            test_payload,
            f"sha256={expected_signature}"
        )

        return {
            "status": "success" if is_valid else "error",
            "message": "Webhook signature validation working" if is_valid else "Signature validation failed"
        }

    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete integration validation."""
        logger.info("Running full Agent Portal integration validation")

        results = {
            "timestamp": str(datetime.now()),
            "oauth2": await self.validate_oauth2_connection(),
            "api_endpoints": await self.validate_api_endpoints(),
            "webhook_signature": await self.validate_webhook_signature()
        }

        # Overall status
        all_passed = all(
            result.get("status") == "success"
            for result in results.values()
            if isinstance(result, dict) and "status" in result
        )

        results["overall_status"] = "success" if all_passed else "error"
        results["summary"] = f"Validation {'PASSED' if all_passed else 'FAILED'}"

        return results


# Deployment and Monitoring
class IntegrationMonitor:
    """Monitoring and health checks for the integration."""

    def __init__(self, integration):
        self.integration = integration
        self.metrics = {
            "webhook_events_processed": 0,
            "api_requests_made": 0,
            "oauth2_token_refreshes": 0,
            "errors_encountered": 0,
            "last_health_check": None
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all integration components."""
        health_status = {
            "timestamp": str(datetime.now()),
            "components": {}
        }

        # Check OAuth2
        try:
            token = await self.integration.oauth_client.get_access_token()
            health_status["components"]["oauth2"] = {
                "status": "healthy",
                "details": "Token available and valid"
            }
        except Exception as e:
            health_status["components"]["oauth2"] = {
                "status": "unhealthy",
                "details": str(e)
            }

        # Check API connectivity
        try:
            async with self.integration.api_client:
                await self.integration.api_client.list_merchants(limit=1)
            health_status["components"]["api_client"] = {
                "status": "healthy",
                "details": "API endpoints accessible"
            }
        except Exception as e:
            health_status["components"]["api_client"] = {
                "status": "unhealthy",
                "details": str(e)
            }

        # Overall health
        all_healthy = all(
            comp["status"] == "healthy"
            for comp in health_status["components"].values()
        )

        health_status["overall_health"] = "healthy" if all_healthy else "unhealthy"
        self.metrics["last_health_check"] = health_status

        return health_status

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics.copy()

    def increment_metric(self, metric_name: str, value: int = 1) -> None:
        """Increment a metric counter."""
        if metric_name in self.metrics:
            self.metrics[metric_name] += value


# Integration with AQI Relational Backprop System
def create_aqi_agent_portal_bridge(integration, backprop_system):
    """Create bridge between Agent Portal integration and AQI relational backprop."""

    from aqi_relational_backprop import RelationalBackpropLoop, ClassifierModule, TemplateSelectorModule, PolicyStackModule

    # Initialize modules for merchant support domain
    classifier = ClassifierModule("merchant_classifier.v1")
    template_selector = TemplateSelectorModule("merchant_template_selector.v1")
    policy_stack = PolicyStackModule("merchant_policy_stack.v1")

    backprop_system.register_module(classifier)
    backprop_system.register_module(template_selector)
    backprop_system.register_module(policy_stack)

    return AQIAgentPortalBridge(integration, backprop_system)


# Example configuration for different environments
def get_example_configs() -> Dict[str, EnvironmentConfig]:
    """Get example configurations for different environments."""

    return {
        "sandbox": EnvironmentConfig(
            name="sandbox",
            base_url="https://api-sandbox.agentportal.com",
            client_id="aqi_sandbox_client",
            client_secret="sandbox_secret_key_here",
            webhook_secret="sandbox_webhook_secret",
            callback_url="https://api-sandbox.aqi-system.com/webhooks/agent-portal/v1/events"
        ),

        "production": EnvironmentConfig(
            name="production",
            base_url="https://api.agentportal.com",
            client_id="aqi_prod_client",
            client_secret="prod_secret_key_here",
            webhook_secret="prod_webhook_secret",
            callback_url="https://api.aqi-system.com/webhooks/agent-portal/v1/events",
            enable_audit_logging=True,
            rate_limit_requests_per_minute=120
        )
    }


# Main deployment function
async def deploy_agent_portal_integration(environment: str = "sandbox") -> Dict[str, Any]:
    """Deploy and validate the Agent Portal integration."""

    logger.info(f"Deploying Agent Portal integration for environment: {environment}")

    # Load configuration
    config_manager = SecureConfigManager()
    env_config = config_manager.load_environment_config(environment)

    # Convert to integration config
    from agent_portal_integration import AgentPortalConfig, create_agent_portal_integration

    integration_config = AgentPortalConfig(
        base_url=env_config.base_url,
        client_id=env_config.client_id,
        client_secret=env_config.client_secret,
        webhook_secret=env_config.webhook_secret,
        callback_url=env_config.callback_url
    )

    # Create integration
    integration = create_agent_portal_integration({
        "base_url": integration_config.base_url,
        "client_id": integration_config.client_id,
        "client_secret": integration_config.client_secret,
        "webhook_secret": integration_config.webhook_secret,
        "callback_url": integration_config.callback_url
    })

    # Initialize integration
    try:
        await integration.initialize()
        logger.info("Integration initialized successfully")
    except Exception as e:
        logger.error(f"Integration initialization failed: {e}")
        return {"status": "error", "message": f"Initialization failed: {e}"}

    # Run validation
    validator = IntegrationValidator(integration)
    validation_results = await validator.run_full_validation()

    if validation_results["overall_status"] == "success":
        logger.info("Agent Portal integration deployed successfully")

        # Create monitor
        monitor = IntegrationMonitor(integration)

        return {
            "status": "success",
            "message": "Integration deployed and validated",
            "integration": integration,
            "monitor": monitor,
            "validation": validation_results
        }
    else:
        logger.error("Integration validation failed")
        return {
            "status": "error",
            "message": "Validation failed",
            "validation": validation_results
        }


if __name__ == "__main__":
    # Example deployment
    import asyncio

    async def main():
        result = await deploy_agent_portal_integration("sandbox")
        print(json.dumps(result, indent=2, default=str))

    asyncio.run(main())