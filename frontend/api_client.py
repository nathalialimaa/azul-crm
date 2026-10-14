"""Único adaptador HTTP do frontend; nenhum acesso ao lake ou aos modelos."""

import httpx


class CrmApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, **kwargs):
        with httpx.Client(base_url=self.base_url, timeout=15, trust_env=False) as client:
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

    def priorities(self):
        return self._request("GET", "/api/v1/retention/priorities", params={"limit": 500})

    def customer(self, customer_id: str):
        return self._request("GET", f"/api/v1/customers/{customer_id}")

    def recommend(self, customer_id: str):
        return self._request("POST", "/api/v1/agent/recommend", json={"customer_id": customer_id})
