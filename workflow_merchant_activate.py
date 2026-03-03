# workflow_merchant_activate.py

from typing import Dict, Any


def build_merchant_activate_workflow(
    name: str = "AQI – Merchant Activation",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Minimal surface: Webhook → Activate Merchant
    AQI fills the logic.
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Activate_Webhook",
                "name": "Merchant Activation Request",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/merchants/activate",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "Activate_Merchant",
                "name": "Processor – Activate Merchant",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "url": f"{internal_base_url}/internal/merchants/activate",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": "={{ JSON.stringify($json) }}",
                },
            },
        ],
        "connections": {
            "Merchant Activation Request": {
                "main": [[{"node": "Processor – Activate Merchant", "type": "main", "index": 0}]]
            },
        },
    }