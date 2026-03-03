# workflow_merchant_onboard.py

from typing import Dict, Any


def build_merchant_onboard_workflow(
    name: str = "AQI – Merchant Onboarding Intake",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Minimal surface: Webhook → Create Merchant
    AQI fills the logic.
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Onboard_Webhook",
                "name": "Merchant Onboarding Request",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/merchants/onboard",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "Create_Merchant",
                "name": "Processor – Create Merchant",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "url": f"{internal_base_url}/internal/merchants/create",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": "={{ JSON.stringify($json) }}",
                },
            },
        ],
        "connections": {
            "Merchant Onboarding Request": {
                "main": [[{"node": "Processor – Create Merchant", "type": "main", "index": 0}]]
            },
        },
    }