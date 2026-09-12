"""
Every platform handler (Flipkart, Amazon, ...) implements this same interface,
so the orchestrator doesn't need to know platform-specific details.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ReturnResult:
    success: bool
    return_id: Optional[str] = None
    return_status: str = "Failed"   # Placed / Failed / Out of window / Support Needed
    refund_amount: Optional[float] = None
    log_message: str = ""
    needs_human_review: bool = False


class PlatformHandler:
    """Abstract base — subclass per platform."""

    def ensure_logged_in(self):
        raise NotImplementedError

    def process_return(self, order_id: str, product_link: str, return_window: str) -> ReturnResult:
        """
        Executes the full return micro-flow for ONE line item and returns
        the outcome. Must never raise on expected failure states (out of
        window, item not found) — those are normal outcomes, captured in
        ReturnResult, not exceptions. Only raise for genuinely unexpected
        errors (page crash, selector not found after retries).
        """
        raise NotImplementedError
