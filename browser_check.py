import os
import subprocess
import sys


def _is_browser_installed() -> bool:
    """检查 Playwright Chromium 是否已安装并能启动"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


def _install_browser() -> bool:
    """调用 playwright install chromium 下载浏览器"""
    try:
        # 打包后 sys.executable 指向 exe，需要用 -m playwright 调用
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True
        print(f"Install failed: {result.stderr}")
        return False
    except Exception as e:
        print(f"Install exception: {e}")
        return False


def ensure_browser() -> tuple:
    """
    确保 Playwright Chromium 已安装。
    返回 (ok: bool, message: str)
    """
    if _is_browser_installed():
        return True, "Browser ready"

    # 没装，尝试下载
    ok = _install_browser()
    if ok and _is_browser_installed():
        return True, "Browser installed"

    return False, (
        "Failed to install browser automatically.\n\n"
        "Please run this command manually in the app folder:\n\n"
        "  playwright install chromium"
    )