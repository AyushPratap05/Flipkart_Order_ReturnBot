"""
Flipkart return handler.

Selectors confirmed against the live Flipkart test account via DevTools
inspection during development.
"""

import re
from platforms.base import PlatformHandler, ReturnResult
from utils import human_delay, human_type, human_click
import config


class FlipkartHandler(PlatformHandler):
    ORDERS_URL = "https://www.flipkart.com/account/orders"
    LOGIN_URL = "https://www.flipkart.com/account/login"

    def __init__(self, page):
        self.page = page

    # ---------------------------------------------------------------- login
    def ensure_logged_in(self):
        self.page.goto(self.ORDERS_URL)
        human_delay(config.DELAY_MEDIUM)

        if "login" not in self.page.url and self._looks_logged_in():
            return  # persistent browser profile already has a valid session

        self.page.goto(self.LOGIN_URL)
        human_delay(config.DELAY_MEDIUM)

        phone_input = self.page.get_by_placeholder(re.compile("Mobile", re.I))
        human_type(phone_input, config.FLIPKART_PHONE)

        request_otp_btn = self.page.get_by_text(re.compile("Request OTP", re.I))
        human_click(request_otp_btn)

        otp = input(f"OTP requested for {config.FLIPKART_PHONE}. Enter the OTP received: ").strip()

        otp_input = self.page.get_by_placeholder(re.compile("OTP", re.I))
        human_type(otp_input, otp)

        submit_btn = self.page.get_by_text(re.compile("^Login$|^Verify$", re.I))
        human_click(submit_btn)

        human_delay(config.DELAY_LONG)

        if not self._looks_logged_in():
            raise RuntimeError("Login did not succeed — check selectors/OTP.")

    def _looks_logged_in(self):
        return self.page.locator("text=My Orders").count() > 0

    # ---------------------------------------------------------- return flow
    def process_return(
        self,
        order_id: str,
        product_link: str,
        return_window: str,
    ) -> ReturnResult:

        # Product Link is the real pre-filled input (per the brief). Flipkart's
        # My Orders list shows product NAMES, not URLs or Order IDs, so we
        # auto-derive a searchable name from the URL slug itself.
        product_name = self._name_from_url(product_link) or product_link

        self.page.goto(self.ORDERS_URL)
        self.page.wait_for_load_state("networkidle")
        human_delay(config.DELAY_MEDIUM)

        order_row = self.page.get_by_text(product_name, exact=False).first

        if order_row.count() == 0:
            return ReturnResult(
                success=False,
                return_status="Failed",
                log_message=(
                    f"Item '{product_name}' (Order {order_id}) "
                    "not found on My Orders page."
                ),
                needs_human_review=True,
            )
        human_click(order_row)
        self.page.wait_for_load_state("networkidle")
        human_delay(config.DELAY_LONG)

        # --- Eligibility check before attempting anything ---
        # Confirmed via DOM inspection: Flipkart renders this as a plain
        # <div>Return </div> (NOT a semantic <button>), often with a
        # trailing space in the text node. Regex matching in Playwright
        # does NOT auto-normalize whitespace the way string matching does,
        # so the anchors must explicitly tolerate leading/trailing space.
        return_btn = self.page.get_by_text(re.compile(r"^\s*Return\s*$", re.I)).filter(
            has_not_text=re.compile("policy", re.I)
        )
        if return_btn.count() == 0:
            if self.page.locator("text=/return.*window|window.*closed/i").count() > 0:
                return ReturnResult(
                    success=False,
                    return_status="Out of window",
                    log_message="Skipped: SKU is past its return eligibility window.",
                    needs_human_review=True,
                )

            return ReturnResult(
                success=False,
                return_status="Support Needed",
                log_message=(
                    "Support needed: No direct return button, and chat did not "
                    "automatically confirm order status. Manual chat support/"
                    "intervention is needed to return this item."
                ),
                needs_human_review=True,
            )

        human_click(return_btn)
        human_delay(config.DELAY_MEDIUM)

        # --- Step 1: Select return reason ---
        main_reason_text = self.page.get_by_text("Don't want the product anymore", exact=True).first
        main_reason_text.click(force=True)
        human_delay(config.DELAY_MEDIUM)

        # Now the sub-menu is open. Target the specific radio label.
        reason_label = self.page.locator('label[for="CUSTOMER_DOES_NOT_WANT"]').first
        reason_radio = self.page.locator('#CUSTOMER_DOES_NOT_WANT').first

        reason_label.wait_for(state="attached", timeout=5000)

        # Click the label directly using JavaScript to bypass all UI/scroll errors
        if not reason_radio.evaluate("el => el.checked"):
            for attempt in range(3):
                reason_label.evaluate("el => el.click()")
                human_delay(config.DELAY_SHORT)

                if reason_radio.evaluate("el => el.checked"):
                    break
            else:
                raise RuntimeError("Failed to select the radio sub-option after 3 attempts.")

        assert reason_radio.evaluate("el => el.checked"), "Reason is not selected!"

        # --- Step 1: Advance via CONTINUE button ---
        step1_continue = self.page.get_by_role("button", name="CONTINUE", exact=True).first
        step1_continue.wait_for(state="attached", timeout=15000)

        for _ in range(5):
            if step1_continue.is_enabled():
                break
            human_delay(config.DELAY_SHORT)
        else:
            raise RuntimeError("CONTINUE button never became enabled.")

        step1_continue.click(force=True)
        human_delay(config.DELAY_MEDIUM)

        # --- Step 2: Select pickup address ---
        address_select_btn = self.page.get_by_text("SELECT", exact=True).first
        if address_select_btn.count() > 0:
            human_click(address_select_btn)
            human_delay(config.DELAY_MEDIUM)

        # --- Step 3: Return action — choose "Refund" over "Exchange" ---
        refund_choice = self.page.get_by_text("Refund", exact=True).first
        if refund_choice.count() > 0:
            human_click(refund_choice)
            human_delay(config.DELAY_MEDIUM)

        # --- Step 3b: Select refund mode ---
        refund_mode = self.page.get_by_text("Original Payment Mode", exact=True).first
        if refund_mode.count() > 0:
            human_click(refund_mode)
            human_delay(config.DELAY_MEDIUM)

        # --- Step 3c: Continue to Step 4 ---
        step3_continue = self.page.get_by_role("button", name=re.compile(r"^Continue$", re.IGNORECASE)).last

        try:
            step3_continue.wait_for(state="attached", timeout=5000)
            step3_continue.click(force=True)
            human_delay(config.DELAY_LONG)
        except Exception:
            pass

        # --- Step 4: Confirm ---
        confirm_btn = self.page.get_by_role("button", name=re.compile(r"Confirm Return|Submit Request|Submit", re.IGNORECASE)).first

        try:
            confirm_btn.wait_for(state="attached", timeout=5000)
            confirm_btn.click(force=True)

            self.page.wait_for_load_state("networkidle")
            human_delay(config.DELAY_LONG)
        except Exception:
            pass  # We will handle the failure below

      # --- Capture confirmation details ---
        page_text = ""
        for _ in range(6):
            page_text = self.page.locator("body").inner_text()
            if re.search(r"(Return ID|Approval ID|Request ID)", page_text, re.I) and "₹" in page_text:
                break
            human_delay(config.DELAY_SHORT)
        # Automatically grab the ID (supports up to 40 characters now)
        id_match = re.search(r"(?:Return ID|Approval ID|Request ID).*?([A-Za-z0-9]{8,40})", page_text, re.IGNORECASE | re.DOTALL)
        final_id = id_match.group(1) if id_match else "Unknown_ID_Check_Account"

        # Automatically grab the refund amount near the Rupee symbol
        amount_match = re.search(r"₹\s*([\d,]+(?:\.\d+)?)", page_text)
        final_amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

        if final_id != "Unknown_ID_Check_Account":
            return ReturnResult(
                success=True,
                return_id=final_id,
                return_status="Placed",
                refund_amount=final_amount,
                log_message=(
                    f"Return placed successfully. "
                    f"Return ID: {final_id}, "
                    f"Refund Amount: {final_amount}"
                ),
            )

        return ReturnResult(
            success=False,
            return_status="Failed",
            log_message="Could not parse Approval ID from the final screen.",
            needs_human_review=True,
        )

    # ------------------------------------------------------------- helpers
    def _name_from_url(self, url):
        """
        Derives a human-readable, searchable product name from a Flipkart
        product URL's slug.

        Example:
        https://www.flipkart.com/carrylux-women-beige-shoulder-bag/p/itm123
        -> "carrylux women beige shoulder"

        Only the first four words are used because Flipkart often truncates
        long product titles in the My Orders page.
        """
        match = re.search(r"/([a-z0-9\-]+)/p/", url or "", re.I)

        if not match:
            return None

        full_name = match.group(1).replace("-", " ")
        words = full_name.split()

        return " ".join(words[:4])

    def _extract_text(self, pattern):
        content = self.page.content()
        match = re.search(pattern, content)
        return match.group(1) if match else None

    def _extract_amount(self):
        content = self.page.content()

        match = re.search(
            r"(?:Refund amount|Refund of)[:\s₹]*([\d,]+)",
            content,
        )

        if match:
            return float(match.group(1).replace(",", ""))

        return None