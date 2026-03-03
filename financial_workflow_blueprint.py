# financial_workflow_blueprint.py

from typing import Dict, Any


def build_charge_and_reconcile_workflow(
    name: str = "AQI – Charge and Reconcile",
) -> Dict[str, Any]:
    """
    Example n8n workflow payload:
    - Webhook trigger
    - Stripe charge (via HTTP Request)
    - Reconciliation stub (e.g., post to internal SCSDMC API)
    """

    return {
        "name": name,
        "active": False,
        "nodes": [
            {
                "id": "WebhookTrigger",
                "name": "Incoming Charge Request",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {
                    "httpMethod": "POST",
                    "path": "aqi/charge",
                    "responseMode": "onReceived",
                    "responseCode": 200,
                },
            },
            {
                "id": "StripeCharge",
                "name": "Stripe – Create Charge",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [600, 200],
                "parameters": {
                    "url": "https://api.stripe.com/v1/payment_intents",
                    "method": "POST",
                    "authentication": "predefinedCredentialType",  # use Stripe credentials in n8n
                    "options": {},
                    "sendBody": True,
                    "bodyParametersUi": {
                        "parameter": [
                            {
                                "name": "amount",
                                "value": "={{ $json[\"amount\"] }}",
                            },
                            {
                                "name": "currency",
                                "value": "={{ $json[\"currency\"] || \"usd\" }}",
                            },
                            {
                                "name": "payment_method",
                                "value": "={{ $json[\"payment_method_id\"] }}",
                            },
                            {
                                "name": "confirm",
                                "value": "true",
                            },
                        ],
                    },
                },
                "credentials": {
                    "httpBasicAuth": {
                        "id": "STRIPE_CREDENTIAL_ID"  # replace with actual credential id in n8n
                    }
                },
            },
            {
                "id": "Reconcile",
                "name": "SCSDMC – Reconcile",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [1000, 200],
                "parameters": {
                    "url": "https://your-internal-recon-endpoint/transactions",
                    "method": "POST",
                    "sendBody": True,
                    "jsonParameters": True,
                    "bodyParametersJson": """
                    {
                        "aqi_correlation_id": "={{ $json[\"correlation_id\"] }}",
                        "stripe_payment_intent_id": "={{ $json[\"id\"] }}",
                        "amount": "={{ $json[\"amount\"] }}",
                        "currency": "={{ $json[\"currency\"] }}"
                    }
                    """,
                },
            },
        ],
        "connections": {
            "Incoming Charge Request": {
                "main": [
                    [
                        {
                            "node": "Stripe – Create Charge",
                            "type": "main",
                            "index": 0,
                        }
                    ]
                ]
            },
            "Stripe – Create Charge": {
                "main": [
                    [
                        {
                            "node": "SCSDMC – Reconcile",
                            "type": "main",
                            "index": 0,
                        }
                    ]
                ]
            },
        },
    }