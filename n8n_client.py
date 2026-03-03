# n8n_client.py

import requests
from typing import Any, Dict, Optional, List
from config import N8NConfig


class N8NClient:
    def __init__(self, config: Optional[N8NConfig] = None) -> None:
        self.config = config or N8NConfig.from_env()
        self.base_url = self.config.base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "X-N8N-API-KEY": self.config.api_key,
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def list_workflows(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/rest/workflows"))
        resp.raise_for_status()
        return resp.json().get("data", resp.json())

    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        resp = self.session.get(self._url(f"/rest/workflows/{workflow_id}"))
        resp.raise_for_status()
        return resp.json()

    def create_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(self._url("/rest/workflows"), json=workflow)
        resp.raise_for_status()
        return resp.json()

    def update_workflow(self, workflow_id: str, workflow: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.patch(self._url(f"/rest/workflows/{workflow_id}"), json=workflow)
        resp.raise_for_status()
        return resp.json()

    def execute_workflow(self, workflow_id: str, run_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = self.session.post(self._url(f"/rest/workflows/{workflow_id}/run"), json=run_data or {})
        resp.raise_for_status()
        return resp.json()