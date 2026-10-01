# Amazon Price Monitor

A desktop tool that monitors Amazon product prices and sends 
Telegram alerts when the price drops below a threshold.

## What It Does

- Add Amazon product URLs with a target price
- Scrapes price, rating, and stock status on demand or on schedule
- Sends a Telegram notification when price < threshold
- Exports price history to CSV
- Bilingual UI (English / Chinese)

## Tech Stack

- **Playwright** — async browser automation with stealth injection
- **BeautifulSoup** — HTML parsing with multi-selector fallback
- **Tkinter** — desktop GUI
- **Telegram Bot API** — notifications
- **PyInstaller** — packaged as standalone Windows .exe

## Key Features

- Anti-bot handling: detects "Continue shopping" page and retries
- Multi-selector price parsing (4 fallback containers)
- Runs 1–N products concurrently via asyncio
- Scheduled monitoring with countdown timer
- Persistent settings in JSON

## Multi-Currency Handling

Amazon may return prices in different currencies for the same 
ASIN depending on session, IP, or region. This tool parses 
all of them automatically:

- `USD 41.96` → currency=USD, price=41.96
- `HKD 329.23` → currency=HKD, price=329.23
- `$ 16.99` → currency=USD, price=16.99

No hardcoded currency assumption. Each price record stores 
its currency alongside the value.
## Screenshots

**Manual run — 5 products, mixed currencies, per-product thresholds:**

![Manual Run](screenshot-main.png)

**Auto mode — 7 consecutive runs at 5-minute intervals over 32 minutes. 
Same ASIN returns HKD/EUR/USD depending on session, all parsed correctly. 
Each alert in the log matches a Telegram message on the right:**

![Auto Mode](screenshot-auto.png)

## Sample Output

Data is stored in CSV format — ready for analysis in Excel or Python:

| timestamp | asin | title | price | currency | rating | stock |
|-----------|------|-------|-------|----------|--------|-------|
| 2026-10-01 09:20:11 | B0CKYZPPMJ | Zinus Memory Foam 8 Inch... | 682.63 | HKD | 4.4 | Only 2 left |
| 2026-10-01 09:20:11 | B01LYNW421 | Beckham Hotel Collection... | 329.23 | HKD | 4.3 | In Stock |
| 2026-10-01 09:27:32 | B01LYNW421 | Beckham Hotel Collection... | 41.96 | USD | 4.3 | In Stock |
| 2026-10-01 09:46:43 | B01LYNW421 | Beckham Hotel Collection... | 52.8 | EUR | 4.3 | In Stock |

Same ASIN, three different currencies across sessions — all parsed correctly.
## How to Run

```bash
pip install -r requirements.txt
playwright install chromium
python gui.py
