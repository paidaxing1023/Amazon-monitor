import json
import os

import paths


DEFAULTS = {
    "language": "en",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "interval_min": 5,
    "products": [],
}


def load_settings() -> dict:
    if not os.path.exists(paths.SETTINGS_PATH):
        return dict(DEFAULTS)
    try:
        with open(paths.SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULTS)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULTS)


def save_settings(data: dict):
    try:
        with open(paths.SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to save settings: {e}")