# workflow_reconciliation_hub.py

from typing import Dict, Any


def build_reconciliation_hub_workflow(
    name: str = "AQI – Reconciliation Hub",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Flow: Webhook → Normalize → Post to Reconciliation Engine
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Recon_Webhook",
                "name": "Incoming Recon Event",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/reconciliation",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "Normalize_Recon",
                "name": "Normalize Reconciliation Payload",
                "type": "n8n-nodes-base.function",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "functionCode": """
                    // Example: pass-through for now.
                    // Here AQI can normalize from multiple event shapes to your canonical schema.
                    return items;
                    """,
                },
            },
            {
                "id": "Post_Recon",
                "name": "Processor – Reconciliation Engine",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [1000, 200],
                "parameters": {
                    "url": f"{internal_base_url}/reconciliation",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": "={{ JSON.stringify($json) }}",
                },
            },
        ],
        "connections": {
            "Incoming Recon Event": {
                "main": [[{"node": "Normalize Reconciliation Payload", "type": "main", "index": 0}]]
            },
            "Normalize Reconciliation Payload": {
                "main": [[{"node": "Processor – Reconciliation Engine", "type": "main", "index": 0}]]
            },
        },
    }