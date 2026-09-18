"""Periodic order cleanup decision and its Infrai scheduling entry point."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from infrai import InfraiClient

# The public call-site idiom is infrai.cron.create; this service keeps it typed.


@dataclass(frozen=True)
class Order:
    order_id: str
    status: str
    updated_at: datetime


@dataclass(frozen=True)
class CleanupRequest:
    orders: list[Order]
    older_than_days: int = 30


def stale_orders(request: CleanupRequest, now: datetime) -> list[str]:
    cutoff = now - timedelta(days=request.older_than_days)
    return [
        order.order_id
        for order in request.orders
        if order.status in {"cancelled", "expired"} and order.updated_at < cutoff
    ]


def schedule_sweep(client: InfraiClient, task_url: str) -> str:
    return client.create_cron("0 2 * * *", task_url)


def publish_sweep(client: InfraiClient, request: CleanupRequest, now: datetime) -> dict:
    ids = stale_orders(request, now)
    return client.publish_cleanup({"order_ids": ids, "observed_at": now.astimezone(timezone.utc).isoformat()})
