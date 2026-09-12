"""
Amazon return handler — stub.

Not built out with real selectors (no test credentials were provided for
Amazon in the brief — only Flipkart). Structure mirrors FlipkartHandler so
it's a drop-in once Amazon test credentials/selectors are available.

Key difference from Flipkart: Amazon sometimes offers a BATCH return flow
(select multiple items on one order, return them together) — detect_batch_flow()
below shows the pattern for that check.
"""
import re
from platforms.base import PlatformHandler, ReturnResult
from utils import human_delay, human_click
import config


class AmazonHandler(PlatformHandler):
    ORDERS_URL = "https://www.amazon.in/gp/css/order-history"

    def __init__(self, page):
        self.page = page

    def ensure_logged_in(self):
        raise NotImplementedError(
            "Amazon login not implemented — no test credentials provided in the brief."
        )

    def detect_batch_flow(self, order_id: str) -> bool:
        """Batch-capable if the return page renders a multi-select item list
        (checkbox per SKU) rather than forcing one item at a time."""
        # TODO: confirm selector once Amazon test account is available
        checkboxes = self.page.locator("input[type=checkbox][data-item-id]")
        return checkboxes.count() > 1

    def process_return(self, order_id: str, product_link: str, return_window: str) -> ReturnResult:
        return ReturnResult(
            success=False, return_status="Failed",
            log_message="Amazon handler not implemented yet — needs test credentials.",
            needs_human_review=True,
        )
