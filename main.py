# main.py

from n8n_client import N8NClient
from workflow_tx_create_capture import build_tx_create_and_capture_workflow
from workflow_refund import build_refund_workflow
from workflow_payout import build_payout_workflow
from workflow_chargeback import build_chargeback_workflow
from workflow_reconciliation_hub import build_reconciliation_hub_workflow
from workflow_merchant_onboard import build_merchant_onboard_workflow
from workflow_merchant_underwrite import build_merchant_underwrite_workflow
from workflow_merchant_activate import build_merchant_activate_workflow
from workflow_merchant_review import build_merchant_review_workflow
from workflow_merchant_suspend import build_merchant_suspend_workflow
from workflow_merchant_release import build_merchant_release_workflow


def create_and_activate(client: N8NClient, workflow_payload: dict) -> None:
    created = client.create_workflow(workflow_payload)
    workflow_id = str(created.get("id") or created.get("data", {}).get("id"))
    name = created.get("name")

    print(f"Created workflow: {name} (id={workflow_id})")

    created["active"] = True
    updated = client.update_workflow(workflow_id, created)
    print(f"Activated workflow: {updated.get('name')} (id={workflow_id})")


def bootstrap_all_internal_finance_workflows() -> None:
    client = N8NClient()

    workflows = [
        # Financial workflows
        build_tx_create_and_capture_workflow(),
        build_refund_workflow(),
        build_payout_workflow(),
        build_chargeback_workflow(),
        build_reconciliation_hub_workflow(),
        # Merchant lifecycle workflows
        build_merchant_onboard_workflow(),
        build_merchant_underwrite_workflow(),
        build_merchant_activate_workflow(),
        build_merchant_review_workflow(),
        build_merchant_suspend_workflow(),
        build_merchant_release_workflow(),
    ]

    for wf in workflows:
        create_and_activate(client, wf)


if __name__ == "__main__":
    bootstrap_all_internal_finance_workflows()