"""
Loop, per the brief:
  1. Read next pending task from Excel.
  2. Open browser for that platform.
  3. Initiate the return.
  4. Capture return ID / status / refund amount.
  5. Write result back to Excel (per line item).
  6. Mark Done or flag for human review.
  Never abandon the rest of an order because one line item failed.
"""
import sys
from playwright.sync_api import sync_playwright
import config
from excel_io import ExcelTaskStore
from utils import RateLimiter
from platforms.flipkart import FlipkartHandler
from platforms.amazon import AmazonHandler


def get_handler(platform: str, page):
    platform = (platform or "").strip().lower()
    if platform == "flipkart":
        return FlipkartHandler(page)
    if platform == "amazon":
        return AmazonHandler(page)
    return None


def run():
    store = ExcelTaskStore()
    tasks = store.get_pending_tasks()
    print(f"[agent] {len(tasks)} pending task(s) found.")

    if not tasks:
        print("[agent] Nothing to do.")
        return

    rate_limiter = RateLimiter()

    with sync_playwright() as p:
        # Persistent context = same browser profile/cookies reused across
        # runs, so we don't re-trigger OTP/login-velocity flags every time.
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            headless=config.HEADLESS,
            viewport=config.VIEWPORT,
            user_agent=config.USER_AGENT,
        )
        page = context.pages[0] if context.pages else context.new_page()

        # Cache one logged-in handler per platform for the whole run,
        # instead of logging in fresh per task.
        handlers = {}

        for task in tasks:
            platform = task["platform"]
            order_id = task["order_id"]
            row = task["row"]

            print(f"\n[agent] Row {row} | Order {order_id} | Platform {platform}")

            handler = handlers.get(platform)
            if handler is None:
                handler = get_handler(platform, page)
                if handler is None:
                    store.write_result(
                        row, task_status="Needs human review",
                        log_message=f"Unknown/unsupported platform: '{platform}'",
                    )
                    print(f"  -> unsupported platform, flagged for review.")
                    continue
                try:
                    handler.ensure_logged_in()
                except NotImplementedError as e:
                    store.write_result(
                        row, task_status="Needs human review",
                        log_message=str(e),
                    )
                    print(f"  -> {e}")
                    continue
                except Exception as e:
                    store.write_result(
                        row, task_status="Needs human review",
                        log_message=f"Login failed: {e}",
                    )
                    print(f"  -> login failed: {e}")
                    continue
                handlers[platform] = handler

            rate_limiter.wait_if_needed()

            # --- Partial-success handling: this task's failure never stops
            # the loop; every remaining line item still gets attempted.
            try:
                result = handler.process_return(
                    order_id=order_id,
                    product_link=task["product_link"],
                    return_window=task["return_window"],
                )
            except Exception as e:
                # Genuinely unexpected error (crash, selector not found) —
                # log it, flag for review, move on to the next line item.
                store.write_result(
                    row, task_status="Needs human review",
                    return_status="Failed",
                    log_message=f"Unexpected error: {e}",
                )
                print(f"  -> unexpected error: {e}")
                continue

            task_status = "Done" if result.success else "Needs human review"
            store.write_result(
                row,
                return_id=result.return_id,
                return_status=result.return_status,
                refund_amount=result.refund_amount,
                task_status=task_status,
                log_message=result.log_message,
            )
            print(f"  -> {result.return_status} | {result.log_message}")

        context.close()

    print("\n[agent] Run complete. All line items have a recorded state.")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n[agent] Interrupted — progress already written is safe (saved per row).")
        sys.exit(1)
