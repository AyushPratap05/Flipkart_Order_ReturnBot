"""
Central configuration for the return automation agent.
Keep secrets in a .env file (not committed) — this just reads them.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Excel task sheet ---
EXCEL_PATH = os.getenv("EXCEL_PATH", "tasks_assign.xlsx")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")

# Column headers expected in the Excel sheet (must match exactly)
COLUMNS = {
    "platform": "Platform",
    "order_id": "Order Id",
    "product_link": "Product Link",
    "return_window": "Return Window",
    "status": "Status",              # To Do / Pending / Done / Needs human review
    "return_id": "Refund ID",
    "return_status": "Return Status",
    "refund_amount": "Refund Amount",
    "timestamp": "Timestamp",
    "log": "Log",
}

# Task statuses that the agent should pick up
PENDING_STATUSES = {"To Do", "Pending", ""}

# --- Login ---
FLIPKART_PHONE = os.getenv("FLIPKART_PHONE")
if not FLIPKART_PHONE:
    raise RuntimeError("FLIPKART_PHONE not set — add it to your .env file")

# --- Browser / bot-avoidance settings ---
HEADLESS = False  # keep headed — headless is far easier to fingerprint
USER_DATA_DIR = os.getenv("USER_DATA_DIR", "./browser_profile")  # persists cookies/login across runs
VIEWPORT = {"width": 1366, "height": 768}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Randomized delay ranges (seconds) between actions — never use fixed sleeps
DELAY_SHORT = (0.8, 2.2)
DELAY_MEDIUM = (2.0, 4.5)
DELAY_LONG = (4.0, 8.0)

# Max return actions per session per hour (rate limiting)
MAX_ACTIONS_PER_HOUR = 20

# Retry / review thresholds
MAX_RETRIES_PER_TASK = 1
