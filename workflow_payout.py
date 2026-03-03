# workflow_payout.py

from typing import Dict, Any


def build_payout_workflow(
    name: str = "AQI – Internal Payout Engine",
    internal_base_url: str = "https://processor.internal",
) -> Dict[str, Any]:
    """
    Flow: Cron/Manual → Compute Payouts → Execute Payouts → Reconcile
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "Payout_Trigger",
                "name": "Payout Trigger",
                "type": "n8n-nodes-base.cron",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "triggerTimes": [
                        {
                            "hour": 1,
                            "minute": 0,
                        }
                    ],
                },
            },
            {
                "id": "Compute_Payouts",
                "name": "Processor – Compute Payouts",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "url": f"{internal_base_url}/payouts/compute",
                    "method": "POST",
                    "sendBody": False,
                    "jsonParameters": False,
                },
            },
            {
                "id": "Execute_Payouts",
                "name": "Processor – Execute Payouts",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [900, 200],
                "parameters": {
                    "url": f"{internal_base_url}/payouts/execute",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": """
                    {
                        "payout_batch_id": "={{ $json[\"batch_id\"] }}"
                    }
                    """,
                },
            },
            {
                "id": "Reconcile_Payouts",
                "name": "Processor – Reconcile Payouts",
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
                        "type": "payout_batch",
                        "payout_batch_id": "={{ $json[\"batch_id\"] }}",
                        "status": "={{ $json[\"status\"] }}"
                    }
                    """,
                },
            },
        ],
        "connections": {
            "Payout Trigger": {
                "main": [[{"node": "Processor – Compute Payouts", "type": "main", "index": 0}]]
            },
            "Processor – Compute Payouts": {
                "main": [[{"node": "Processor – Execute Payouts", "type": "main", "index": 0}]]
            },
            "Processor – Execute Payouts": {
                "main": [[{"node": "Processor – Reconcile Payouts", "type": "main", "index": 0}]]
            },
        },
    }