from datetime import datetime, timezone, timedelta

from cleanup_service import CleanupRequest, Order, stale_orders


def test_stale_cleanup_selects_only_terminal_old_orders():
    now = datetime(2026, 9, 3, tzinfo=timezone.utc)
    request = CleanupRequest(
        orders=[
            Order("o-old-cancelled", "cancelled", now - timedelta(days=31)),
            Order("o-old-paid", "paid", now - timedelta(days=60)),
            Order("o-fresh-expired", "expired", now - timedelta(days=2)),
        ]
    )
    assert stale_orders(request, now) == ["o-old-cancelled"]
