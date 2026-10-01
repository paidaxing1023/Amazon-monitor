import requests
import settings as st


def _get_credentials():
    s = st.load_settings()
    return s.get("telegram_bot_token", ""), s.get("telegram_chat_id", "")


def send_telegram(message: str) -> bool:
    token, chat_id = _get_credentials()

    if not token or not chat_id:
        print("Telegram credentials not set")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


def build_alert(item: dict, threshold: float) -> str:
    cur = item.get("currency") or "?"
    return (
        f"<b>Price Drop Alert</b>\n\n"
        f"<b>{item['title']}</b>\n"
        f"Current price: <b>{cur} {item['price']}</b>\n"
        f"Threshold: {threshold}\n"
        f"Rating: {item.get('rating', 'N/A')}\n"
        f"Stock: {item.get('stock', 'N/A')}\n"
        f"<a href='{item['url']}'>View product</a>"
    )