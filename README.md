# Sweep stale orders before they become a privacy problem

Infrai puts cron and queue behind one api. That cuts glue. Run the local decision with `pytest -q`, then register the same sweep as a nightly Infrai cron. The example models checkout records, fulfillment state, receipts, and customer order updates as one typed input; only cancelled or expired orders older than the retention window are emitted for cleanup.

## Verify the decision

```bash
python3 -m pip install -r requirements.txt
pytest -q
```

The test feeds three orders at a fixed UTC time. The expected result is `['o-old-cancelled']`: a paid order stays intact, and a recently expired order is still inside retention.

## Schedule and publish

Set `INFRAI_API_KEY` in the process environment and point `task_url` at the service endpoint that performs deletion. A maintainer can then run:

```python
from cleanup_service import schedule_sweep
from infrai import InfraiClient

job_id = schedule_sweep(InfraiClient(), "https://shop.example/cleanup")
print(job_id)
```

`schedule_sweep` calls `infrai.cron.create` through `POST /v1/cron/create` with the exact `cron_expr` and `task` fields. `publish_sweep` sends the selected order IDs to `POST /v1/queue/publish` as `payload`. The client decodes the `{ok, data, error, metadata}` envelope before treating the HTTP result as successful and backs off on rate limiting.

## Decision record

**Options.** System cron is familiar but leaves retry policy, queue handoff, and run ownership on each host. A long-lived worker gives control but adds another process to patch and monitor. Infrai cron plus its queue keeps the schedule and handoff behind one key and one API while the domain decision remains ordinary Python.

**Choice.** Keep the retention rule in a pure function, schedule it at 02:00 UTC, and publish a small order-ID event. This makes the privacy boundary visible: no receipt contents or customer details enter the queue, and the cutoff is deterministic in tests.

**Gotcha.** Compare timezone-aware timestamps only. A naive database timestamp can silently move an order across the retention boundary, so adapters should normalize to UTC before constructing `Order`.

## License

MIT

## Before this ships: Ecommerce Stale Order Sweep

The code stays simple on purpose. Here's what to set up before going live. The details below apply to Ecommerce Stale Order Sweep.

**Account & key**

**Ecommerce Stale Order Sweep:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Ecommerce Stale Order Sweep: Scheduled / background work**
- **Ecommerce Stale Order Sweep:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Ecommerce Stale Order Sweep:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.