# workflow_refund.py

from typing import Dict, Any


def build_refund_workflow(
    name: str = "AQI – Internal Refund Processor",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Flow: Webhook → Create Refund → Reconcile
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Webhook_Refund",
                "name": "Incoming Refund Request",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/refunds",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "Create_Refund",
                "name": "Processor – Create Refund",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "url": f"{internal_base_url}/refunds",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": """
                    {
                        "transaction_id": "={{ $json[\"transaction_id\"] }}",
                        "amount": "={{ $json[\"amount\"] }}",
                        "reason": "={{ $json[\"reason\"] }}",
                        "merchant_id": "={{ $json[\"merchant_id\"] }}"
                    }
                    """,
                },
            },
            {
                "id": "Reconcile_Refund",
                "name": "Processor – Reconcile Refund",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [1000, 200],
                "parameters": {
                    "url": f"{internal_base_url}/reconciliation",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": """
                    {
                        "type": "refund",
                        "refund_id": "={{ $json[\"id\"] }}",
                        "transaction_id": "={{ $json[\"transaction_id\"] }}",
                        "merchant_id": "={{ $json[\"merchant_id\"] }}",
                        "amount": "={{ $json[\"amount\"] }}",
                        "status": "={{ $json[\"status\"] }}"
                    }
                    """,
                },
            },
        ],
        "connections": {
            "Incoming Refund Request": {
                "main": [[{"node": "Processor – Create Refund", "type": "main", "index": 0}]]
            },
            "Processor – Create Refund": {
                "main": [[{"node": "Processor – Reconcile Refund", "type": "main", "index": 0}]]
            },
        },
    }