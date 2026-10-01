import asyncio
import random
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
"""


MAIN_PRICE_CONTAINERS = [
    ".apex-pricetopay-value",
    "#corePriceDisplay_desktop_feature_div",
    "#corePrice_feature_div",
    "#price",
]


def parse_price_block(block):
    if block is None:
        return None, None

    off = block.select_one(".a-offscreen")
    if off:
        cur, val = parse_price_text(off.get_text(strip=True))
        if val is not None:
            return cur, val

    sym = block.select_one(".a-price-symbol")
    whole = block.select_one(".a-price-whole")
    frac = block.select_one(".a-price-fraction")

    if whole is None:
        return None, None

    currency = sym.get_text(strip=True) if sym else "?"

    whole_digits = re.sub(r"[^\d]", "", whole.get_text(strip=True))
    frac_digits = re.sub(r"[^\d]", "", frac.get_text(strip=True)) if frac else "00"

    if not whole_digits:
        return None, None

    try:
        value = float(f"{whole_digits}.{frac_digits or '00'}")
    except ValueError:
        return None, None

    return currency, value


def parse_price_text(text: str):
    if not text:
        return None, None

    text = text.strip()

    patterns = [
        (r"(HKD)\s*([\d,]+\.?\d*)", "HKD"),
        (r"(EUR)\s*([\d,]+\.?\d*)", "EUR"),
        (r"(USD)\s*([\d,]+\.?\d*)", "USD"),
        (r"(GBP)\s*([\d,]+\.?\d*)", "GBP"),
        (r"(CAD)\s*([\d,]+\.?\d*)", "CAD"),
        (r"(AUD)\s*([\d,]+\.?\d*)", "AUD"),
        (r"(JPY)\s*([\d,]+\.?\d*)", "JPY"),
        (r"US\$\s*([\d,]+\.?\d*)", "USD"),
        (r"HK\$\s*([\d,]+\.?\d*)", "HKD"),
        (r"\$\s*([\d,]+\.?\d*)", "USD"),
        (r"([\d,]+\.?\d*)\s*美元", "USD"),
        (r"([\d,]+\.?\d*)\s*欧元", "EUR"),
        (r"([\d,]+\.?\d*)\s*港币", "HKD"),
    ]

    for pattern, currency in patterns:
        m = re.search(pattern, text)
        if m:
            num = m.groups()[-1]
            try:
                return currency, float(num.replace(",", ""))
            except ValueError:
                continue

    return "?", None


async def handle_continue_shopping(page, url):
    """如果亚马逊返回反爬验证页，点按钮并重新访问商品页"""
    try:
        html = await page.content()
        if len(html) > 100000:
            return

        btn = await page.query_selector("button:has-text('Continue shopping')")
        if btn:
            print("Detected anti-bot page, clicking Continue shopping...")
            await btn.click()
            await page.wait_for_timeout(2000)

            current_url = page.url
            if "/dp/" not in current_url:
                print("Redirected to homepage, re-navigating to product page...")
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(random.randint(3000, 5000))
    except Exception as e:
        print(f"handle_continue_shopping error: {e}")


async def _scrape_once(url: str, headless: bool) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--start-minimized",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="America/New_York",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        await context.add_init_script(STEALTH_SCRIPT)
        page = await context.new_page()

        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(3000, 5000))

            await handle_continue_shopping(page, url)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            title_el = soup.select_one("#productTitle")
            title = title_el.get_text(strip=True) if title_el else "N/A"

            currency = None
            price = None

            for container_sel in MAIN_PRICE_CONTAINERS:
                container = soup.select_one(container_sel)
                if not container:
                    continue
                price_block = container.select_one(".a-price") or container
                cur, val = parse_price_block(price_block)
                if val is not None:
                    currency, price = cur, val
                    break

            rating = None
            el = soup.select_one("#acrPopover")
            if el:
                m = re.search(r"([\d.]+)", el.get("title", ""))
                if m:
                    rating = float(m.group(1))
            if rating is None:
                for el in soup.select(".a-icon-alt"):
                    m = re.search(r"([\d.]+)", el.get_text(strip=True))
                    if m:
                        rating = float(m.group(1))
                        break

            stock = "Unknown"
            for sel in ["#availability span", "#availability", "#outOfStock"]:
                el = soup.select_one(sel)
                if el:
                    text = el.get_text(strip=True)
                    if text:
                        stock = text[:50]
                        break

            return {
                "url": url,
                "asin": url.split("/dp/")[-1].split("/")[0] if "/dp/" in url else "N/A",
                "title": title[:100],
                "price": price,
                "currency": currency or "?",
                "rating": rating,
                "stock": stock,
            }

        finally:
            await browser.close()


async def scrape_product(url: str, headless: bool = False, retries: int = 1) -> dict:
    last_err = None
    for attempt in range(retries + 1):
        try:
            result = await _scrape_once(url, headless)
            if result.get("price") is not None:
                return result
            last_err = "price not found"
        except Exception as e:
            last_err = str(e)

        if attempt < retries:
            await asyncio.sleep(2)

    return {"url": url, "error": last_err or "unknown error"}


async def scrape_all(urls: list, headless: bool = False) -> list:
    tasks = [scrape_product(url, headless) for url in urls]
    return await asyncio.gather(*tasks)