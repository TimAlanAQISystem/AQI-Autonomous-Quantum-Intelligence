# workflow_chargeback.py

from typing import Dict, Any


def build_chargeback_workflow(
    name: str = "AQI – Internal Chargeback Handler",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Flow: Webhook/Event → Fetch Evidence → Submit → Reconcile
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Chargeback_Event",
                "name": "Incoming Chargeback Event",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/chargebacks",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "Fetch_Evidence",
                "name": "Processor – Fetch Evidence",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "url": f"{internal_base_url}/chargebacks/evidence",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": """
                    {
                        "chargeback_id": "={{ $json[\"chargeback_id\"] }}",
                        "transaction_id": "={{ $json[\"transaction_id\"] }}"
                    }
                    """,
                },
            },
            {
                "id": "Submit_Evidence",
                "name": "Processor – Submit Evidence",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [900, 200],
                "parameters": {
                    "url": f"{internal_base_url}/chargebacks/submit",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": """
                    {
                        "chargeback_id": "={{ $json[\"chargeback_id\"] }}",
                        "evidence_bundle_id": "={{ $json[\"evidence_bundle_id\"] }}"
                    }
                    """,
                },
            },
            {
                "id": "Reconcile_Chargeback",
                "name": "Processor – Reconcile Chargeback",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [1200, 200],
                "parameters": {
                    "url": f"{internal_base_url}/reconciliation",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": """
                    {
                        "type": "chargeback",
                        "chargeback_id": "={{ $json[\"chargeback_id\"] }}",
                        "transaction_id": "={{ $json[\"transaction_id\"] }}",
                        "status": "submitted"
                    }
                    """,
                },
            },
        ],
        "connections": {
            "Incoming Chargeback Event": {
                "main": [[{"node": "Processor – Fetch Evidence", "type": "main", "index": 0}]]
            },
            "Processor – Fetch Evidence": {
                "main": [[{"node": "Processor – Submit Evidence", "type": "main", "index": 0}]]
            },
            "Processor – Submit Evidence": {
                "main": [[{"node": "Processor – Reconcile Chargeback", "type": "main", "index": 0}]]
            },
        },
    }