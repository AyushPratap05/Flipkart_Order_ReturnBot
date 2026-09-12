"""
Small helpers used everywhere to make the browser session look human:
randomized pacing instead of fixed sleeps, and character-by-character typing
instead of instant fills.
"""
import random
import time
import config


def human_delay(delay_range=config.DELAY_SHORT):
    lo, hi = delay_range
    time.sleep(random.uniform(lo, hi))


def human_type(locator, text):
    """Types character by character with small random pauses, instead of
    Playwright's instant .fill() — instant fills are a common bot signal."""
    locator.click()
    for ch in text:
        locator.type(ch, delay=random.randint(60, 180))
    human_delay(config.DELAY_SHORT)


def human_click(locator):
    """Adds a short pause before clicking, and scrolls the element into view
    first (mimics a human reading before acting)."""
    locator.scroll_into_view_if_needed()
    human_delay((0.3, 0.9))
    locator.click()


class RateLimiter:
    """Caps how many return actions run per hour, per the config limit."""

    def __init__(self, max_per_hour=config.MAX_ACTIONS_PER_HOUR):
        self.max_per_hour = max_per_hour
        self.timestamps = []

    def wait_if_needed(self):
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < 3600]
        if len(self.timestamps) >= self.max_per_hour:
            sleep_for = 3600 - (now - self.timestamps[0]) + 1
            print(f"[rate-limit] hit {self.max_per_hour}/hr cap — pausing {sleep_for/60:.1f} min")
            time.sleep(sleep_for)
        self.timestamps.append(time.time())
