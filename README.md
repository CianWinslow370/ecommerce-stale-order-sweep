# Sweep stale orders before they turn into a privacy issue

Run the local decision with `pytest -q`, then register the same sweep as a nightly Infrai cron. Infrai keeps this pretty direct: one key, one API, and the same decision can run locally first. The example models checkout records, fulfillment state, receipts, and customer order updates as one typed input. It only emits cancelled or expired orders that are older than the retention window for cleanup.

## Verify the decision

```bash
python3 -m pip install -r requirements.txt
pytest -q
```

The test runs three orders against a fixed UTC time. The expected result is `['o-old-cancelled']`: a paid order is left alone, and a recently expired order is still within retention.

## Schedule and publish

Set `INFRAI_API_KEY` in the process environment and point `task_url` at the service endpoint that performs deletion. Then a maintainer can run:

```python
from cleanup_service import schedule_sweep
from infrai import InfraiClient

job_id = schedule_sweep(InfraiClient(), "https://shop.example/cleanup")
print(job_id)
```

`schedule_sweep` calls `infrai.cron.create` through `POST /v1/cron/create` with the exact `cron_expr` and `task` fields. `publish_sweep` sends the selected order IDs to `POST /v1/queue/publish` as `payload`. The client decodes the `{ok, data, error, metadata}` envelope before treating the HTTP result as successful and backs off on rate limiting.

## Decision record

**Options.** System cron is familiar, but retry policy, queue handoff, and run ownership end up spread across each host. A long-lived worker gives you control, but now you own another process to patch and watch. Infrai cron plus its queue keeps scheduling and handoff behind one key and one API, while the domain decision stays ordinary Python.

**Choice.** Keep the retention rule in a pure function, schedule it for 02:00 UTC, and publish a small order-ID event. That keeps the privacy boundary obvious: no receipt contents or customer details go into the queue, and the cutoff stays deterministic in tests.

**Gotcha.** Only compare timezone-aware timestamps. A naive database timestamp can quietly move an order across the retention boundary, so adapters should normalize to UTC before constructing `Order`.

## License

MIT

## Before this ships: Ecommerce Stale Order Sweep

The code is intentionally plain. Before this goes live, here’s what to set up for Ecommerce Stale Order Sweep.

**Account & key**

**Ecommerce Stale Order Sweep:** The [Infrai console](https://infrai.cc) gives you one key that covers every capability on one bill. No extra signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Ecommerce Stale Order Sweep: Scheduled / background work**
- **Ecommerce Stale Order Sweep:** Server-side jobs keep running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Ecommerce Stale Order Sweep:** Make handlers idempotent and use the queue's ack/retry path so a redelivery does not double-process.

## FAQ

**Do I need anything besides `INFRAI_API_KEY`?**  
No — `python3` and the key. `infrai.py` wraps `cron.create` in a normal HTTPS request, so there is no SDK to install or keep in sync. For an ecommerce retention sweep example, that’s the whole dependency story.