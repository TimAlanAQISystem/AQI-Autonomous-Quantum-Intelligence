# workflow_merchant_suspend.py

from typing import Dict, Any


def build_merchant_suspend_workflow(
    name: str = "AQI – Merchant Suspension",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Minimal surface: Webhook → Suspend Merchant
    AQI fills the logic.
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Suspend_Webhook",
                "name": "Merchant Suspension Request",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/merchants/suspend",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "Suspend_Merchant",
                "name": "Processor – Suspend Merchant",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "url": f"{internal_base_url}/internal/merchants/suspend",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": "={{ JSON.stringify($json) }}",
                },
            },
        ],
        "connections": {
            "Merchant Suspension Request": {
                "main": [[{"node": "Processor – Suspend Merchant", "type": "main", "index": 0}]]
            },
        },
    }