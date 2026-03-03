# workflow_merchant_release.py

from typing import Dict, Any


def build_merchant_release_workflow(
    name: str = "AQI – Merchant Release",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Minimal surface: Webhook → Release Merchant
    AQI fills the logic.
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Release_Webhook",
                "name": "Merchant Release Request",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/merchants/release",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "Release_Merchant",
                "name": "Processor – Release Merchant",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "url": f"{internal_base_url}/internal/merchants/release",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": "={{ JSON.stringify($json) }}",
                },
            },
        ],
        "connections": {
            "Merchant Release Request": {
                "main": [[{"node": "Processor – Release Merchant", "type": "main", "index": 0}]]
            },
        },
    }