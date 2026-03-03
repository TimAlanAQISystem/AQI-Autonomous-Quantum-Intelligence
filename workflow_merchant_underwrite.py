# workflow_merchant_underwrite.py

from typing import Dict, Any


def build_merchant_underwrite_workflow(
    name: str = "AQI – Merchant Underwriting Decision",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Minimal surface: Webhook → Update Merchant Risk
    AQI fills the logic.
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Underwrite_Webhook",
                "name": "Merchant Underwriting Request",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/merchants/underwrite",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "Update_Risk",
                "name": "Processor – Update Merchant Risk",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "url": f"{internal_base_url}/internal/merchants/risk",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": "={{ JSON.stringify($json) }}",
                },
            },
        ],
        "connections": {
            "Merchant Underwriting Request": {
                "main": [[{"node": "Processor – Update Merchant Risk", "type": "main", "index": 0}]]
            },
        },
    }