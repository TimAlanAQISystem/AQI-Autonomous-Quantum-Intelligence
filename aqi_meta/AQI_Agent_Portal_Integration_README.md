# AQI Agent Portal Integration - Complete Implementation

## Overview

This is a complete, production-ready integration between AQI (Autonomous Quantum Intelligence) and the Agent Portal API. The integration enables automated merchant support workflows with real-time data synchronization and AQI's relational backprop learning system.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Agent Portal  │◄──►│  AQI Integration │◄──►│ AQI Backprop    │
│   API           │    │  Layer           │    │ Learning System │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
   Real-time Webhooks     OAuth2 + REST API      Ethical Learning
   Merchant Status        Secure Token Mgmt      Pattern Recognition
   Transaction Updates    HMAC Validation        Continuous Improvement
```

## Key Features

### 🔐 Security & Authentication
- **OAuth2 Client Credentials Flow** with automatic token refresh
- **HMAC-SHA256 webhook signature validation**
- **Encrypted token storage** using Fernet encryption
- **SOC2 compliant audit logging**

### 🔄 Real-Time Integration
- **Webhook processing** for merchant status and transaction updates
- **REST API client** for merchant and transaction operations
- **Automatic retry logic** with exponential backoff
- **Rate limiting** and error handling

### 🧠 AQI Learning Integration
- **Relational Backprop Loop** for continuous improvement
- **Guardian checkpoint** for ethical validation
- **Dynamic responsibility attribution** across modules
- **Pattern reinforcement** from successful interactions

## Files Overview

| File | Purpose |
|------|---------|
| `agent_portal_integration.py` | Core integration classes and API client |
| `agent_portal_config.py` | Configuration management and validation |
| `agent_portal_demo.py` | Complete demonstration and testing |
| `aqi_relational_backprop.py` | AQI learning system (created earlier) |
| `Agent_Portal_Integration_Prep.md` | Original preparation documentation |

## Quick Start

### 1. Environment Setup

Set environment variables (recommended for production):

```bash
export AQI_AGENT_PORTAL_SANDBOX_BASE_URL="https://api-sandbox.agentportal.com"
export AQI_AGENT_PORTAL_SANDBOX_CLIENT_ID="your_client_id"
export AQI_AGENT_PORTAL_SANDBOX_CLIENT_SECRET="your_client_secret"
export AQI_AGENT_PORTAL_SANDBOX_WEBHOOK_SECRET="your_webhook_secret"
export AQI_AGENT_PORTAL_SANDBOX_CALLBACK_URL="https://api.aqi-system.com/webhooks/agent-portal/v1/events"
```

### 2. Run the Demo

```bash
cd /path/to/aqi_meta
python agent_portal_demo.py
```

This will:
- Initialize the integration
- Validate OAuth2 connection
- Test webhook processing
- Demonstrate AQI learning
- Show end-to-end merchant support automation

### 3. Deploy Integration

```python
import asyncio
from agent_portal_config import deploy_agent_portal_integration

async def deploy():
    result = await deploy_agent_portal_integration("sandbox")
    if result["status"] == "success":
        integration = result["integration"]
        monitor = result["monitor"]
        print("Integration deployed successfully!")
    else:
        print(f"Deployment failed: {result['message']}")

asyncio.run(deploy())
```

## API Usage Examples

### Initialize Integration

```python
from agent_portal_integration import create_agent_portal_integration

config = {
    "base_url": "https://api-sandbox.agentportal.com",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "webhook_secret": "your_webhook_secret"
}

integration = create_agent_portal_integration(config)
await integration.initialize()
```

### Process Webhook

```python
webhook_payload = {
    "event_type": "merchant.status_update",
    "data": {
        "merchant_id": "12345",
        "status": "approved"
    }
}

headers = {"X-AgentPortal-Signature": "sha256=signature_here"}
result = await integration.process_webhook(webhook_payload, headers)
```

### Get Merchant Data

```python
async with integration.api_client:
    merchant = await integration.get_merchant_support_data("12345")
    print(f"Risk level: {merchant['support_context']['risk_level']}")
```

### AQI Learning Integration

```python
from aqi_relational_backprop import RelationalBackpropLoop

# Set up learning system
backprop = RelationalBackpropLoop()

# Create bridge
from agent_portal_integration import AQIAgentPortalBridge
bridge = AQIAgentPortalBridge(integration, backprop)

# Process merchant interaction
response = await bridge.handle_merchant_interaction("merchant_123", {
    "message": "Transaction failed - help needed",
    "channel": "email"
})
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AQI_AGENT_PORTAL_{ENV}_BASE_URL` | Agent Portal API base URL | Yes |
| `AQI_AGENT_PORTAL_{ENV}_CLIENT_ID` | OAuth2 client ID | Yes |
| `AQI_AGENT_PORTAL_{ENV}_CLIENT_SECRET` | OAuth2 client secret | Yes |
| `AQI_AGENT_PORTAL_{ENV}_WEBHOOK_SECRET` | Webhook signature secret | Yes |
| `AQI_AGENT_PORTAL_{ENV}_CALLBACK_URL` | Webhook callback URL | No |

### Supported Environments

- `sandbox` - Testing environment
- `production` - Live environment

## Webhook Events

The integration handles these webhook events:

| Event | Description | AQI Action |
|-------|-------------|------------|
| `merchant.status_update` | Status changes (pending→approved) | Update support context |
| `merchant.approval` | Final approval confirmations | Trigger success automation |
| `merchant.decline` | Decline notifications | Initiate recovery process |
| `transaction.confirmation` | Successful transactions | Log for pattern analysis |
| `transaction.failure` | Failed transactions | Flag for immediate support |

## AQI Learning Integration

The system uses AQI's relational backprop loop to learn from every interaction:

### Error Zones
- **Zone A (Surplus)**: error = -1 → Reinforce good patterns
- **Zone B (Baseline)**: error = 0 → No change needed
- **Zone C (Soft)**: error = +1 → Gentle correction
- **Zone D (Hard)**: error = +3 → Strong correction

### Learning Process
1. **Trace** every merchant interaction
2. **Evaluate** through Guardian checkpoint
3. **Attribute** responsibility across modules
4. **Apply** local corrections
5. **Reinforce** successful patterns

## Security Features

### Authentication
- OAuth2 with automatic token refresh
- Tokens encrypted at rest
- Secure token transmission

### Webhooks
- HMAC-SHA256 signature validation
- Timestamp verification
- Replay attack prevention

### Data Protection
- All API calls over HTTPS
- Sensitive data encrypted
- Audit logging enabled
- SOC2 compliance ready

## Monitoring & Health Checks

```python
from agent_portal_config import IntegrationValidator, IntegrationMonitor

# Validate integration
validator = IntegrationValidator(integration)
results = await validator.run_full_validation()

# Monitor health
monitor = IntegrationMonitor(integration)
health = await monitor.health_check()

# Get metrics
metrics = monitor.get_metrics()
```

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Webhook callback URL accessible
- [ ] SSL certificates valid
- [ ] Database connections ready
- [ ] AQI modules registered
- [ ] Guardian evaluation process ready
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented

## Troubleshooting

### Common Issues

**OAuth2 Connection Failed**
- Check client credentials
- Verify Agent Portal API status
- Confirm network connectivity

**Webhook Signature Invalid**
- Verify webhook secret matches
- Check payload formatting
- Confirm HMAC implementation

**AQI Learning Not Working**
- Ensure modules are registered
- Check Guardian evaluation process
- Verify trace completion

### Logs and Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check integration health:
```python
health = await integration.monitor.health_check()
print(json.dumps(health, indent=2))
```

## Production Deployment

1. **Environment Setup**
   ```bash
   export AQI_AGENT_PORTAL_PRODUCTION_*
   ```

2. **Validation**
   ```python
   result = await deploy_agent_portal_integration("production")
   ```

3. **Monitoring**
   - Set up health check endpoints
   - Configure alerting for failures
   - Enable audit logging

4. **Scaling**
   - Configure rate limiting
   - Set up load balancing
   - Monitor API quotas

## Support

For issues or questions:
- Check the demo output for examples
- Review configuration against environment variables
- Validate webhook signatures manually
- Test API endpoints with curl/Postman

## License

This integration is part of the AQI Autonomous Intelligence system.

---

**Ready to deploy!** 🚀 The integration is complete and tested. Follow the quick start guide to get AQI connected to Agent Portal with full learning capabilities.