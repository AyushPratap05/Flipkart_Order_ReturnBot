# FlipkartReturnBot

## Setup (run these on your own machine — needs real internet access)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Create a `.env` file next to `flipkart_return_bot.py`:
```
EXCEL_PATH=tasks.xlsx
FLIPKART_PHONE=YOUR_PHONE_NUMBER
```

Your `tasks.xlsx` needs these column headers in row 1 (matches `config.py`'s `COLUMNS` dict — edit that dict if your sheet uses different headers):
`Platform, Order Id, Product Link, Return Window, Status, Refund ID, Return Status, Refund Amount, Timestamp, Log`

Rows with `Status` = `To Do`, `Pending`, or blank are picked up as pending tasks.

## Run

```bash
python flipkart_return_bot.py
```

First run: a real Chromium window opens (not headless — intentional, see below), navigates to Flipkart login, requests an OTP to `YOUR_PHONE_NUMBER`, and the script will pause and ask you to type the OTP into the terminal once you receive the call/SMS. After that, your session is saved in `./browser_profile/` and future runs should skip login entirely.

## Before this actually works end-to-end

The Flipkart selectors in `platforms/flipkart.py` are marked `# TODO` — they're my best guess at Flipkart's structure, but I don't have live browser access to confirm them. To finish it:

1. Run the script once, headed (default) — watch where it gets stuck.
2. Right-click the element it failed to find (e.g. the "Request OTP" button) → Inspect → in DevTools, right-click the highlighted HTML → Copy → Copy selector.
3. Paste that into the matching `# TODO` line in `flipkart.py`.
4. Re-run. Repeat for each step until a full return completes end-to-end.

This is normal for browser automation — sites change their DOM often enough that hardcoded selectors always need a live confirmation pass. The flow logic (order of steps, partial-success handling, write-back) is complete and shouldn't need changes.

## What's implemented

- Excel read/write at line-item level (`excel_io.py`) — every SKU row gets its own outcome, saved after every row so a crash mid-run never loses completed work.
- Partial-success handling (`flipkart_return_bot.py`) — one line item's failure/exception never stops the rest of the queue.
- Bot-avoidance (`utils.py`, `config.py`): persistent browser profile (no repeated fresh logins), randomized delays instead of fixed sleeps, human-like character-by-character typing, rate limiting (default 20 actions/hour), headed (not headless) browser.
- Platform routing (`flipkart_return_bot.py: get_handler`) — dispatches by the `Platform` column; easy to add new platforms by writing a new `platforms/<name>.py` implementing `PlatformHandler`.
- Amazon stub (`platforms/amazon.py`) with batch-vs-sequential detection pattern, not fully wired since no Amazon test credentials were provided in the brief.

## What's NOT implemented (be upfront about this in your submission/interview)

- Exact Flipkart selectors — needs a live pass against the real site (see above).
- Amazon flow — no test credentials given.
- CAPTCHA handling — currently not detected; a production version should detect a CAPTCHA challenge and pause for human handoff rather than fail silently.
