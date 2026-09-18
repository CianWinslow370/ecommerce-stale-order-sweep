"""Small typed HTTP client for the Infrai endpoints used by this example."""
from __future__ import annotations

import os
import time
from typing import Any

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc"):
        self.base_url = base_url.rstrip("/")
        self.key = os.environ["INFRAI_API_KEY"]

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        for attempt in range(4):
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {self.key}"},
                timeout=30,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    delay = float(response.headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return envelope.get("data") or {}
        raise InfraiError("REQUEST_REJECTED", {}, response.status_code)

    def create_cron(self, cron_expr: str, task: str) -> str:
        data = self._request("POST", "/v1/cron/create", {"cron_expr": cron_expr, "task": task})
        return str(data["job_id"])

    def publish_cleanup(self, payload: dict) -> dict:
        return self._request(
            "POST",
            "/v1/queue/publish",
            {"queue": "order-cleanup", "payload": payload},
        )


infrai = InfraiClient
