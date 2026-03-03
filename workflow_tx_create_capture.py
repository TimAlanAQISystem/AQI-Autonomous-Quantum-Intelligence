# workflow_tx_create_capture.py

from typing import Dict, Any


def build_tx_create_and_capture_workflow(
    name: str = "AQI – Internal Tx Create & Capture",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Flow: Webhook → Create Tx → Capture Tx → Reconcile
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Webhook_In",
                "name": "Incoming Transaction Request",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/transactions",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "Create_Tx",
                "name": "Processor – Create Transaction",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 150],
                "parameters": {
                    "url": f"{internal_base_url}/transactions",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": """
                    {
                        "merchant_id": "={{ $json[\"merchant_id\"] }}",
                        "amount": "={{ $json[\"amount\"] }}",
                        "currency": "={{ $json[\"currency\"] || \"usd\" }}",
                        "source": "={{ $json[\"source\"] }}",
                        "reference_id": "={{ $json[\"reference_id\"] }}"
                    }
                    """,
                },
            },
            {
                "id": "Capture_Tx",
                "name": "Processor – Capture Transaction",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [900, 150],
                "parameters": {
                    "url": f"{internal_base_url}/transactions/capture",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": """
                    {
                        "transaction_id": "={{ $json[\"id\"] }}",
                        "amount": "={{ $json[\"amount\"] }}"
                    }
                    """,
                },
            },
            {
                "id": "Reconcile_Tx",
                "name": "Processor – Reconcile Transaction",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [1200, 150],
                "parameters": {
                    "url": f"{internal_base_url}/reconciliation",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": """
                    {
                        "type": "transaction",
                        "transaction_id": "={{ $json[\"id\"] }}",
                        "merchant_id": "={{ $json[\"merchant_id\"] }}",
                        "amount": "={{ $json[\"amount\"] }}",
                        "currency": "={{ $json[\"currency\"] }}",
                        "status": "captured"
                    }
                    """,
                },
            },
        ],
        "connections": {
            "Incoming Transaction Request": {
                "main": [[{"node": "Processor – Create Transaction", "type": "main", "index": 0}]]
            },
            "Processor – Create Transaction": {
                "main": [[{"node": "Processor – Capture Transaction", "type": "main", "index": 0}]]
            },
            "Processor – Capture Transaction": {
                "main": [[{"node": "Processor – Reconcile Transaction", "type": "main", "index": 0}]]
            },
        },
    }