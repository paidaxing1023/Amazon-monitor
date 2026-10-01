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

## Screenshots

*(add 2–3 screenshots here)*

## How to Run

```bash
pip install -r requirements.txt
playwright install chromium
python gui.py
