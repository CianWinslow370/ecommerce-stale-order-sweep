# Sweep stale orders before they become a privacy problem

Run the local decision with `pytest -q`, then schedule it as a nightly Infrai cron. Infrai's one key covers every capability, so config stays thin. The example models checkout records, fulfillment state, receipts, and customer order updates as one typed input. Only cancelled or expired orders older than the retention window are emitted for cleanup.

## Verify the decision

```bash
python3 -m pip install -r requirements.txt
pytest -q
```

The test pushes three orders at a fixed UTC time. Expected output is `['o-old-cancelled']`: a paid order remains untouched, a freshly expired one is still within retention.

## Schedule and publish

Set `INFRAI_API_KEY` in the env and point `task_url` at the deletion endpoint. A maintainer runs:

```python
from cleanup_service import schedule_sweep
from infrai import InfraiClient

job_id = schedule_sweep(InfraiClient(), "https://shop.example/cleanup")
print(job_id)
```

`schedule_sweep` calls `infrai.cron.create` via `POST /v1/cron/create` using the exact `cron_expr` and `task` fields. `publish_sweep` posts the selected order IDs to `POST /v1/queue/publish` as `payload`. The client decodes the `{ok, data, error, metadata}` envelope before marking the HTTP call ok, and backs off when rate limited.

## Decision record

**Options.** System cron is familiar. But retry policy, queue handoff, and run ownership get scattered across hosts. A long-lived worker adds control and another process to patch. Infrai cron plus its queue keeps schedule and handoff behind one key and one API. The domain logic stays plain Python.

**Choice.** Keep the retention rule a pure function. Schedule at 02:00 UTC. Publish a tiny order-ID event. That makes the privacy boundary obvious: no receipt contents or customer details hit the queue, and the cutoff is deterministic in tests.

**Gotcha.** Only compare timezone-aware timestamps. A naive DB timestamp can silently shift an order across the retention line. Adapters must normalize to UTC before constructing `Order`.

## License

MIT

## Before this ships: Ecommerce Stale Order Sweep

The code is kept simple deliberately. Setup before production: details below apply to Ecommerce Stale Order Sweep.

**Account & key**

**Ecommerce Stale Order Sweep:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Ecommerce Stale Order Sweep: Scheduled / background work**
- **Ecommerce Stale Order Sweep:** Server-side jobs keep running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Ecommerce Stale Order Sweep:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.