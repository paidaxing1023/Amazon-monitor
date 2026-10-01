import os
import sys


def get_app_dir():
    # Directory of the exe when frozen; project root during development
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_dir()
DATA_DIR = os.path.join(APP_DIR, "data")
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
CSV_PATH = os.path.join(DATA_DIR, "prices.csv")


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)