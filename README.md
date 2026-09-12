# FlipkartReturnBot

A Playwright-based automation agent that files return requests on Flipkart, driven off an Excel task sheet. It processes returns at the line-item level — each SKU gets tracked and updated independently, so one failed item never stops the rest of the batch.

> **Status: Flipkart-only, selectors not yet confirmed against the live site.** The flow logic (reading tasks, driving the browser, writing results back) is complete. What's missing is a live pass to lock in Flipkart's actual button/field selectors — see [Finishing the Flipkart integration](#finishing-the-flipkart-integration) below. Amazon has a stub only (no test credentials were available).

## What it does

You give it an Excel sheet listing orders you want returned. It:
1. Opens a real (visible, not headless) Chromium browser
2. Logs into your Flipkart account via OTP (once — the session is then saved and reused)
3. Goes through each pending order, requests a return
4. Writes the outcome — refund ID, return status, refund amount, timestamp, and a log line — back into the same Excel sheet, row by row, saving after every single row

If something goes wrong on one order, it logs the failure and moves to the next one instead of stopping the whole run.

## Requirements

- Python 3.9+
- Google Chrome/Chromium (installed automatically by Playwright in setup below)
- A Flipkart account with orders that are within their return window

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/AyushPratap05/Flipkart_Order_ReturnBot.git
cd Flipkart_Order_ReturnBot
```

### 2. Set up a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure your credentials

Create a file named `.env` in the project root (same folder as `flipkart_return_bot.py`):

```
EXCEL_PATH=tasks.xlsx
FLIPKART_PHONE=9999999999
```

Replace `9999999999` with the phone number linked to your Flipkart account. This file is never committed to git (it's in `.gitignore`) — keep it that way, since it's tied to your personal account.

### 4. Prepare your task sheet

Create `tasks.xlsx` (or point `EXCEL_PATH` in `.env` to wherever yours lives) with these exact column headers in row 1:

| Platform | Order Id | Product Link | Return Window | Status | Refund ID | Return Status | Refund Amount | Timestamp | Log |
|---|---|---|---|---|---|---|---|---|---|

- **Platform**: currently only `Flipkart` is handled
- **Order Id**: your Flipkart order ID
- **Product Link**: direct link to the product page for that order
- **Return Window**: informational, e.g. `10 Days`
- **Status**: leave blank, or set to `To Do` or `Pending` — these are the rows the agent picks up. Once processed, the agent updates this itself.
- The rest of the columns (**Refund ID, Return Status, Refund Amount, Timestamp, Log**) are filled in automatically by the agent — leave them empty when you start.

If your column names differ, edit the `COLUMNS` dictionary in `config.py` to match instead of renaming your sheet.

### 5. Run it

```bash
python flipkart_return_bot.py
```

**First run:** a Chromium window opens and navigates to the Flipkart login page, enters your phone number, and requests an OTP. The terminal will pause and prompt you to type in the OTP once you receive it by SMS/call. After this, your login session is saved in `./browser_profile/` — future runs skip the login step entirely.

The agent then works through each pending row in your task sheet, one at a time, with randomized human-like delays between actions.

## Project structure

```
Flipkart_Order_ReturnBot/
├── flipkart_return_bot.py     # entry point — orchestrates the run
├── config.py                  # settings: column mapping, delays, rate limits
├── excel_io.py                # reads tasks, writes results back row by row
├── utils.py                   # bot-avoidance helpers (delays, human-like typing)
├── build_tasks_from_raw.py    # optional: builds tasks.xlsx from a raw order export
├── requirements.txt
└── platforms/
    ├── __init__.py
    ├── base.py                # PlatformHandler interface
    ├── flipkart.py            # Flipkart-specific automation steps
    └── amazon.py              # stub only, not wired in
```

Adding a new platform means writing a new `platforms/<name>.py` that implements the `PlatformHandler` interface in `platforms/base.py`, then adding it to the routing in `flipkart_return_bot.py`.

## Bot-avoidance measures

- Persistent browser profile — no repeated fresh logins across runs
- Randomized delays between actions instead of fixed sleeps
- Character-by-character human-like typing instead of instant field fills
- Rate limiting — default 20 actions/hour, configurable in `config.py`
- Headed (visible) browser by default — headless is far easier for sites to fingerprint and block

## Finishing the Flipkart integration

The selectors in `platforms/flipkart.py` (marked `# TODO`) are best-guess placeholders — they haven't been confirmed against Flipkart's live DOM. To finish them:

1. Run the script (`python flipkart_return_bot.py`) and watch where it fails to find an element.
2. In the opened Chromium window, right-click that element → **Inspect**.
3. In DevTools, right-click the highlighted HTML → **Copy → Copy selector**.
4. Paste that selector into the matching `# TODO` line in `platforms/flipkart.py`.
5. Re-run and repeat for the next step it gets stuck on, until a full return completes end-to-end.

This is normal for browser automation — site DOMs change often enough that hardcoded selectors always need a live confirmation pass rather than being guessed from memory.

## Known limitations

- **Flipkart selectors** are unconfirmed placeholders (see above).
- **Amazon** is not implemented — only a stub with a batch-vs-sequential detection pattern, since no test credentials were available.
- **CAPTCHA handling** is not implemented. If Flipkart presents a CAPTCHA mid-run, the current version will fail on that step rather than pausing for a human to solve it — a production version should detect and pause instead.

## Security notes

- Never commit `.env`, `tasks.xlsx`, or `browser_profile/` — all three are in `.gitignore` for a reason: they contain your phone number, real order data, and a live logged-in session respectively.
- If you fork or adapt this, generate your own `tasks.xlsx` rather than reusing someone else's — order data and addresses are personal.
