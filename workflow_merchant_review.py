# workflow_merchant_review.py

from typing import Dict, Any


def build_merchant_review_workflow(
    name: str = "AQI – Merchant Review",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Minimal surface: Webhook → Update Merchant
    AQI fills the logic.
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Review_Webhook",
                "name": "Merchant Review Request",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/merchants/review",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "Update_Merchant",
                "name": "Processor – Update Merchant",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "url": f"{internal_base_url}/internal/merchants/update",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": "={{ JSON.stringify($json) }}",
                },
            },
        ],
        "connections": {
            "Merchant Review Request": {
                "main": [[{"node": "Processor – Update Merchant", "type": "main", "index": 0}]]
            },
        },
    }