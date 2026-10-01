import asyncio
import csv
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime

from scraper import scrape_all
from notifier import send_telegram, build_alert
import settings as st
import paths
from browser_check import ensure_browser


CSV_PATH = paths.CSV_PATH


TRANSLATIONS = {
    "en": {
        "app_title": "Amazon Price Monitor",
        "nav_config": "Software Config",
        "nav_auto": "Auto Monitor",
        "nav_settings": "Settings",

        "add_product": "Add Product",
        "url_label": "Amazon URL:",
        "threshold_label": "Threshold:",
        "add_btn": "Add",
        "monitored": "Monitored Products",
        "col_asin": "ASIN",
        "col_url": "URL",
        "col_threshold": "Threshold",
        "remove_btn": "Remove Selected",
        "run_btn": "Run Once",
        "edit_hint": "Tip: double-click a row to edit its threshold",
        "log_title": "Log",

        "auto_title": "Auto Monitor",
        "interval_label": "Interval (min):",
        "auto_start_btn": "Start Auto",
        "auto_stop_btn": "Stop Auto",
        "auto_log_title": "Auto Log",

        "settings_title": "Settings",
        "lang_label": "Language:",
        "tg_section": "Telegram",
        "tg_token_label": "Bot Token:",
        "tg_chat_label": "Chat ID:",
        "tg_test_btn": "Test Connection",
        "save_btn": "Save Settings",
        "clear_log_btn": "Clear Log",
        "export_csv_btn": "Export CSV",
        "price_history_btn": "Price History",
        "settings_saved": "Settings saved",

        "status_ready": "Ready",
        "status_scraping": "Scraping...",
        "status_auto_running": "Auto running",
        "status_auto_next": "Next run in",
        "status_seconds": "s",

        "err_invalid_url": "Invalid Amazon URL. Must contain /dp/ASIN",
        "err_threshold": "Threshold must be a number",
        "err_interval": "Interval must be a positive number",
        "info_duplicate": "This product is already in the list",
        "info_no_csv": "No CSV file yet. Run once first.",
        "warn_no_products": "Add at least one product first",
        "info_no_data": "Not enough data to draw a chart",

        "log_added": "Added",
        "log_removed": "Removed",
        "log_scraping": "Scraping started...",
        "log_scraped": "Scraped",
        "log_alert": "Alert sent",
        "log_done": "Done.",
        "log_tg_ok": "Telegram test sent successfully",
        "log_tg_fail": "Telegram test FAILED",
        "log_error": "ERROR",
        "log_auto_started": "Auto mode started, interval",
        "log_auto_stopped": "Auto mode stopped",
        "log_auto_tick": "Auto run triggered",
        "log_exported": "Exported to",
        "log_threshold_updated": "Threshold updated for",
        "log_settings_saved": "Settings saved",
    },
    "zh": {
        "app_title": "亚马逊价格监控",
        "nav_config": "软件配置",
        "nav_auto": "定时监控",
        "nav_settings": "设置",

        "add_product": "添加商品",
        "url_label": "亚马逊链接:",
        "threshold_label": "价格阈值:",
        "add_btn": "添加",
        "monitored": "监控中的商品",
        "col_asin": "ASIN",
        "col_url": "链接",
        "col_threshold": "阈值",
        "remove_btn": "删除选中",
        "run_btn": "立即运行一次",
        "edit_hint": "提示：双击某一行可编辑阈值",
        "log_title": "日志",

        "auto_title": "定时监控",
        "interval_label": "间隔(分钟):",
        "auto_start_btn": "开始自动监控",
        "auto_stop_btn": "停止自动监控",
        "auto_log_title": "自动监控日志",

        "settings_title": "设置",
        "lang_label": "语言:",
        "tg_section": "Telegram",
        "tg_token_label": "Bot Token:",
        "tg_chat_label": "Chat ID:",
        "tg_test_btn": "测试连接",
        "save_btn": "保存设置",
        "clear_log_btn": "清空日志",
        "export_csv_btn": "导出 CSV",
        "price_history_btn": "价格走势",
        "settings_saved": "设置已保存",

        "status_ready": "就绪",
        "status_scraping": "抓取中...",
        "status_auto_running": "自动运行中",
        "status_auto_next": "下次运行倒计时",
        "status_seconds": "秒",

        "err_invalid_url": "无效的亚马逊链接，必须包含 /dp/ASIN",
        "err_threshold": "阈值必须是数字",
        "err_interval": "间隔必须是正数",
        "info_duplicate": "该商品已在列表中",
        "info_no_csv": "还没有 CSV 文件，请先运行一次",
        "warn_no_products": "请先添加至少一个商品",
        "info_no_data": "数据不足，无法绘制图表",

        "log_added": "已添加",
        "log_removed": "已删除",
        "log_scraping": "开始抓取...",
        "log_scraped": "已抓取",
        "log_alert": "已发送提醒",
        "log_done": "完成。",
        "log_tg_ok": "Telegram 测试发送成功",
        "log_tg_fail": "Telegram 测试失败",
        "log_error": "错误",
        "log_auto_started": "自动监控已启动，间隔",
        "log_auto_stopped": "自动监控已停止",
        "log_auto_tick": "自动触发抓取",
        "log_exported": "已导出到",
        "log_threshold_updated": "阈值已更新",
        "log_settings_saved": "设置已保存",
    },
}


class PriceMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1000x720")
        self.root.minsize(900, 650)

        paths.ensure_dirs()

        self.settings = st.load_settings()
        self.lang = self.settings.get("language", "en")
        self.products = list(self.settings.get("products", []))

        self.auto_running = False
        self.auto_job = None
        self.auto_countdown_job = None
        self.auto_next_run_ts = None

        self.build_ui()
        self.apply_language()
        self.refresh_product_tree()
        self.update_status(self.t("status_ready"))

    def t(self, key):
        return TRANSLATIONS[self.lang][key]

    # ==================== UI 构建 ====================
    def build_ui(self):
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        self.nav_frame = ttk.Frame(container, width=160, relief="ridge")
        self.nav_frame.pack(side="left", fill="y")
        self.nav_frame.pack_propagate(False)

        self.nav_buttons = {}
        for key, label_key in [
            ("config", "nav_config"),
            ("auto", "nav_auto"),
            ("settings", "nav_settings"),
        ]:
            btn = tk.Button(
                self.nav_frame,
                text="",
                anchor="w",
                relief="flat",
                bg="#f0f0f0",
                activebackground="#d0e0f0",
                padx=15, pady=12,
                command=lambda k=key: self.show_page(k),
            )
            btn.pack(fill="x")
            self.nav_buttons[key] = (btn, label_key)

        self.content = ttk.Frame(container)
        self.content.pack(side="right", fill="both", expand=True)

        self.pages = {}
        self.pages["config"] = self.build_config_page()
        self.pages["auto"] = self.build_auto_page()
        self.pages["settings"] = self.build_settings_page()

        self.status_var = tk.StringVar(value="")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padding=(8, 4),
        )
        status_bar.pack(side="bottom", fill="x")

        self.show_page("config")

    def build_config_page(self):
        page = ttk.Frame(self.content)

        self.add_frame = ttk.LabelFrame(page, padding=10)
        self.add_frame.pack(fill="x", padx=10, pady=8)

        self.url_label = ttk.Label(self.add_frame)
        self.url_label.grid(row=0, column=0, sticky="w")

        self.url_entry = ttk.Entry(self.add_frame, width=55)
        self.url_entry.grid(row=0, column=1, padx=5)

        self.threshold_label = ttk.Label(self.add_frame)
        self.threshold_label.grid(row=0, column=2, sticky="w")

        self.threshold_entry = ttk.Entry(self.add_frame, width=10)
        self.threshold_entry.grid(row=0, column=3, padx=5)
        self.threshold_entry.insert(0, "999.99")

        self.add_btn = ttk.Button(self.add_frame, command=self.add_product)
        self.add_btn.grid(row=0, column=4, padx=5)

        self.mid_frame = ttk.LabelFrame(page, padding=10)
        self.mid_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("asin", "url", "threshold")
        self.tree = ttk.Treeview(self.mid_frame, columns=columns, show="headings", height=8)
        self.tree.column("asin", width=120)
        self.tree.column("url", width=550)
        self.tree.column("threshold", width=100)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_row_double_click)

        self.remove_btn = ttk.Button(self.mid_frame, command=self.remove_selected)
        self.remove_btn.pack(pady=5)

        self.action_frame = ttk.Frame(page)
        self.action_frame.pack(fill="x", padx=10)

        self.run_btn = ttk.Button(self.action_frame, command=self.run_once)
        self.run_btn.pack(side="left", padx=5)

        self.clear_log_btn = ttk.Button(self.action_frame, command=self.clear_log)
        self.clear_log_btn.pack(side="left", padx=5)

        self.export_csv_btn = ttk.Button(self.action_frame, command=self.export_csv)
        self.export_csv_btn.pack(side="left", padx=5)

        self.price_history_btn = ttk.Button(self.action_frame, command=self.show_price_history)
        self.price_history_btn.pack(side="left", padx=5)

        self.log_frame = ttk.LabelFrame(page, padding=10)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self.log = scrolledtext.ScrolledText(self.log_frame, height=10, state="disabled")
        self.log.pack(fill="both", expand=True)

        return page

    def build_auto_page(self):
        page = ttk.Frame(self.content)

        self.auto_frame = ttk.LabelFrame(page, padding=15)
        self.auto_frame.pack(fill="x", padx=10, pady=8)

        self.interval_label = ttk.Label(self.auto_frame)
        self.interval_label.grid(row=0, column=0, sticky="w")

        self.interval_entry = ttk.Entry(self.auto_frame, width=10)
        self.interval_entry.grid(row=0, column=1, padx=5)
        self.interval_entry.insert(0, str(self.settings.get("interval_min", 5)))

        self.auto_start_btn = ttk.Button(self.auto_frame, command=self.start_auto)
        self.auto_start_btn.grid(row=0, column=2, padx=5)

        self.auto_stop_btn = ttk.Button(self.auto_frame, command=self.stop_auto, state="disabled")
        self.auto_stop_btn.grid(row=0, column=3, padx=5)

        self.auto_log_frame = ttk.LabelFrame(page, padding=10)
        self.auto_log_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self.auto_log = scrolledtext.ScrolledText(self.auto_log_frame, height=15, state="disabled")
        self.auto_log.pack(fill="both", expand=True)

        return page

    def build_settings_page(self):
        page = ttk.Frame(self.content)

        self.lang_frame = ttk.LabelFrame(page, padding=10)
        self.lang_frame.pack(fill="x", padx=10, pady=8)

        self.lang_label = ttk.Label(self.lang_frame)
        self.lang_label.pack(side="left")

        self.lang_var = tk.StringVar(value="English")
        self.lang_combo = ttk.Combobox(
            self.lang_frame,
            textvariable=self.lang_var,
            values=["English", "中文"],
            state="readonly",
            width=10,
        )
        self.lang_combo.pack(side="left", padx=5)
        self.lang_combo.bind("<<ComboboxSelected>>", self.on_lang_change)

        self.tg_frame = ttk.LabelFrame(page, padding=10)
        self.tg_frame.pack(fill="x", padx=10, pady=8)

        self.tg_token_label = ttk.Label(self.tg_frame)
        self.tg_token_label.grid(row=0, column=0, sticky="w", pady=3)

        self.tg_token_entry = ttk.Entry(self.tg_frame, width=55)
        self.tg_token_entry.grid(row=0, column=1, padx=5, pady=3)
        self.tg_token_entry.insert(0, self.settings.get("telegram_bot_token", ""))

        self.tg_chat_label = ttk.Label(self.tg_frame)
        self.tg_chat_label.grid(row=1, column=0, sticky="w", pady=3)

        self.tg_chat_entry = ttk.Entry(self.tg_frame, width=55)
        self.tg_chat_entry.grid(row=1, column=1, padx=5, pady=3)
        self.tg_chat_entry.insert(0, self.settings.get("telegram_chat_id", ""))

        self.tg_test_btn = ttk.Button(self.tg_frame, command=self.test_telegram)
        self.tg_test_btn.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        self.save_btn = ttk.Button(page, command=self.save_all_settings)
        self.save_btn.pack(pady=10)

        help_text = (
            "How to get Bot Token and Chat ID:\n"
            "1. Search @BotFather in Telegram, send /newbot, follow the steps, copy the token\n"
            "2. Search your new bot, send it any message (e.g. hi)\n"
            "3. Open in browser: https://api.telegram.org/bot<TOKEN>/getUpdates\n"
            "4. Find \"chat\":{\"id\":...}, that number is your Chat ID\n\n"
            "如何获取 Bot Token 和 Chat ID：\n"
            "1. 在 Telegram 搜索 @BotFather，发送 /newbot，按步骤创建，复制 token\n"
            "2. 搜索你刚创建的 bot，给它发任意消息（比如 hi）\n"
            "3. 浏览器打开：https://api.telegram.org/bot<TOKEN>/getUpdates\n"
            "4. 找到 \"chat\":{\"id\":...}，那个数字就是 Chat ID"
        )
        self.help_label = ttk.Label(page, text=help_text, justify="left", foreground="#555")
        self.help_label.pack(padx=15, pady=10, anchor="w")

        return page

    # ==================== 页面切换 ====================
    def show_page(self, key):
        for k, frame in self.pages.items():
            if k == key:
                frame.pack(fill="both", expand=True, padx=5, pady=5)
            else:
                frame.pack_forget()

        for k, (btn, _) in self.nav_buttons.items():
            btn.config(bg="#d0e0f0" if k == key else "#f0f0f0")

    # ==================== 语言 ====================
    def apply_language(self):
        self.root.title(self.t("app_title"))

        for k, (btn, label_key) in self.nav_buttons.items():
            btn.config(text=self.t(label_key))

        self.add_frame.config(text=self.t("add_product"))
        self.url_label.config(text=self.t("url_label"))
        self.threshold_label.config(text=self.t("threshold_label"))
        self.add_btn.config(text=self.t("add_btn"))

        self.mid_frame.config(text=self.t("monitored"))
        self.tree.heading("asin", text=self.t("col_asin"))
        self.tree.heading("url", text=self.t("col_url"))
        self.tree.heading("threshold", text=self.t("col_threshold"))
        self.remove_btn.config(text=self.t("remove_btn"))

        self.run_btn.config(text=self.t("run_btn"))
        self.clear_log_btn.config(text=self.t("clear_log_btn"))
        self.export_csv_btn.config(text=self.t("export_csv_btn"))
        self.price_history_btn.config(text=self.t("price_history_btn"))

        self.log_frame.config(text=self.t("log_title"))

        self.auto_frame.config(text=self.t("auto_title"))
        self.interval_label.config(text=self.t("interval_label"))
        self.auto_start_btn.config(text=self.t("auto_start_btn"))
        self.auto_stop_btn.config(text=self.t("auto_stop_btn"))
        self.auto_log_frame.config(text=self.t("auto_log_title"))

        self.lang_frame.config(text=self.t("lang_label"))
        self.lang_label.config(text=self.t("lang_label"))
        self.tg_frame.config(text=self.t("tg_section"))
        self.tg_token_label.config(text=self.t("tg_token_label"))
        self.tg_chat_label.config(text=self.t("tg_chat_label"))
        self.tg_test_btn.config(text=self.t("tg_test_btn"))
        self.save_btn.config(text=self.t("save_btn"))

        self.lang_var.set("中文" if self.lang == "zh" else "English")

    def on_lang_change(self, event):
        self.lang = "zh" if self.lang_var.get() == "中文" else "en"
        self.apply_language()
        self.log_msg(f"Language switched to {self.lang}")
        self.settings["language"] = self.lang
        st.save_settings(self.settings)

    # ==================== 日志 ====================
    def log_msg(self, msg):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n"
        for widget in (self.log, self.auto_log):
            widget.config(state="normal")
            widget.insert("end", line)
            widget.see("end")
            widget.config(state="disabled")

    def clear_log(self):
        for widget in (self.log, self.auto_log):
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.config(state="disabled")

    # ==================== 状态栏 ====================
    def update_status(self, text):
        self.status_var.set(text)

    # ==================== 商品管理 ====================
    def refresh_product_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.products:
            self.tree.insert("", "end", values=(p["asin"], p["url"], p["threshold"]))

    def add_product(self):
        url = self.url_entry.get().strip()
        threshold_str = self.threshold_entry.get().strip()

        if "/dp/" not in url:
            messagebox.showerror("Error", self.t("err_invalid_url"))
            return

        asin = url.split("/dp/")[-1].split("/")[0].split("?")[0]
        url = f"https://www.amazon.com/dp/{asin}"

        try:
            threshold = float(threshold_str)
        except ValueError:
            messagebox.showerror("Error", self.t("err_threshold"))
            return

        for p in self.products:
            if p["asin"] == asin:
                messagebox.showinfo("Info", self.t("info_duplicate"))
                return

        self.products.append({"url": url, "asin": asin, "threshold": threshold})
        self.tree.insert("", "end", values=(asin, url, threshold))
        self.url_entry.delete(0, "end")
        self.log_msg(f"{self.t('log_added')}: {asin}")
        self.persist_products()

    def remove_selected(self):
        for item in self.tree.selection():
            asin = self.tree.item(item, "values")[0]
            self.products = [p for p in self.products if p["asin"] != asin]
            self.tree.delete(item)
            self.log_msg(f"{self.t('log_removed')}: {asin}")
        self.persist_products()

    def on_row_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        values = self.tree.item(item, "values")
        asin, url, old_threshold = values[0], values[1], values[2]

        win = tk.Toplevel(self.root)
        win.title("Edit Threshold")
        win.geometry("300x120")
        win.transient(self.root)
        win.grab_set()

        ttk.Label(win, text=f"{asin}").pack(pady=5)
        entry = ttk.Entry(win, width=15)
        entry.pack(pady=5)
        entry.insert(0, str(old_threshold))

        def save():
            try:
                new_val = float(entry.get().strip())
            except ValueError:
                messagebox.showerror("Error", self.t("err_threshold"))
                return
            for p in self.products:
                if p["asin"] == asin:
                    p["threshold"] = new_val
            self.tree.item(item, values=(asin, url, new_val))
            self.log_msg(f"{self.t('log_threshold_updated')}: {asin} -> {new_val}")
            self.persist_products()
            win.destroy()

        ttk.Button(win, text="OK", command=save).pack(pady=5)

    def persist_products(self):
        self.settings["products"] = self.products
        st.save_settings(self.settings)

    # ==================== 手动运行 ====================
    def run_once(self):
        if not self.products:
            messagebox.showwarning("Warning", self.t("warn_no_products"))
            return
        self.run_btn.config(state="disabled")
        self.update_status(self.t("status_scraping"))
        threading.Thread(target=self._run_once_thread, daemon=True).start()

    # ==================== 自动模式 ====================
    def start_auto(self):
        if not self.products:
            messagebox.showwarning("Warning", self.t("warn_no_products"))
            return

        try:
            interval_min = float(self.interval_entry.get().strip())
            if interval_min <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", self.t("err_interval"))
            return

        self.auto_running = True
        self.auto_start_btn.config(state="disabled")
        self.auto_stop_btn.config(state="normal")
        self.interval_entry.config(state="disabled")

        self.log_msg(f"{self.t('log_auto_started')}: {interval_min} min")
        self.settings["interval_min"] = interval_min
        st.save_settings(self.settings)

        self._auto_run()

    def stop_auto(self):
        self.auto_running = False

        for job in (self.auto_job, self.auto_countdown_job):
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
        self.auto_job = None
        self.auto_countdown_job = None

        self.auto_start_btn.config(state="normal")
        self.auto_stop_btn.config(state="disabled")
        self.interval_entry.config(state="normal")
        self.update_status(self.t("status_ready"))
        self.log_msg(self.t("log_auto_stopped"))

    def _auto_run(self):
        if not self.auto_running:
            return

        self.log_msg(self.t("log_auto_tick"))
        threading.Thread(target=self._run_once_thread, daemon=True).start()

        interval_min = float(self.interval_entry.get().strip())
        ms = int(interval_min * 60 * 1000)

        self.auto_next_run_ts = datetime.now().timestamp() + ms / 1000
        self.auto_job = self.root.after(ms, self._auto_run)
        self._tick_countdown()

    def _tick_countdown(self):
        if not self.auto_running or self.auto_next_run_ts is None:
            return
        remain = int(self.auto_next_run_ts - datetime.now().timestamp())
        if remain < 0:
            remain = 0
        self.update_status(f"{self.t('status_auto_running')} | {self.t('status_auto_next')} {remain} {self.t('status_seconds')}")
        self.auto_countdown_job = self.root.after(1000, self._tick_countdown)

    # ==================== 抓取线程 ====================
    def _run_once_thread(self):
        self.log_msg(self.t("log_scraping"))
        urls = [p["url"] for p in self.products]
        items = asyncio.run(scrape_all(urls, headless=False))

        paths.ensure_dirs()
        file_exists = os.path.exists(CSV_PATH)

        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "asin", "title", "price", "currency", "rating", "stock", "url"])
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for item in items:
                if "error" in item:
                    self.log_msg(f"{self.t('log_error')}: {item['url']} - {item['error']}")
                    continue

                cur = item.get("currency") or "?"

                writer.writerow([
                    now,
                    item.get("asin", ""),
                    item.get("title", ""),
                    item.get("price", ""),
                    item.get("currency", ""),
                    item.get("rating", ""),
                    item.get("stock", ""),
                    item.get("url", ""),
                ])
                self.log_msg(f"{self.t('log_scraped')}: {item['asin']} - {cur} {item.get('price')}")

                threshold = next((p["threshold"] for p in self.products if p["asin"] == item["asin"]), None)
                if threshold and item.get("price") is not None and item["price"] < threshold:
                    send_telegram(build_alert(item, threshold))
                    self.log_msg(f"{self.t('log_alert')}: {item['asin']} - {cur} {item['price']}")

        self.log_msg(self.t("log_done"))
        self.root.after(0, lambda: self.run_btn.config(state="normal"))
        if not self.auto_running:
            self.root.after(0, lambda: self.update_status(self.t("status_ready")))

    # ==================== 设置页操作 ====================
    def test_telegram(self):
        self.settings["telegram_bot_token"] = self.tg_token_entry.get().strip()
        self.settings["telegram_chat_id"] = self.tg_chat_entry.get().strip()
        st.save_settings(self.settings)

        ok = send_telegram("Test message from Amazon Price Monitor")
        self.log_msg(self.t("log_tg_ok") if ok else self.t("log_tg_fail"))

    def save_all_settings(self):
        self.settings["language"] = self.lang
        self.settings["telegram_bot_token"] = self.tg_token_entry.get().strip()
        self.settings["telegram_chat_id"] = self.tg_chat_entry.get().strip()
        self.settings["interval_min"] = self.interval_entry.get().strip()
        self.settings["products"] = self.products
        st.save_settings(self.settings)

        self.log_msg(self.t("log_settings_saved"))
        messagebox.showinfo("Info", self.t("settings_saved"))

    # ==================== 导出 CSV ====================
    def export_csv(self):
        if not os.path.exists(CSV_PATH):
            messagebox.showinfo("Info", self.t("info_no_csv"))
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="prices_export.csv",
        )
        if not path:
            return

        try:
            with open(CSV_PATH, "r", encoding="utf-8") as src, open(path, "w", encoding="utf-8", newline="") as dst:
                dst.write(src.read())
            self.log_msg(f"{self.t('log_exported')}: {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ==================== 价格走势 ====================
    def show_price_history(self):
        if not os.path.exists(CSV_PATH):
            messagebox.showinfo("Info", self.t("info_no_csv"))
            return

        rows = []
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        if not rows:
            messagebox.showinfo("Info", self.t("info_no_data"))
            return

        series = {}
        for r in rows:
            asin = r.get("asin", "")
            try:
                price = float(r.get("price", ""))
            except (ValueError, TypeError):
                continue
            ts = r.get("timestamp", "")
            series.setdefault(asin, []).append((ts, price))

        if not series:
            messagebox.showinfo("Info", self.t("info_no_data"))
            return

        win = tk.Toplevel(self.root)
        win.title(self.t("price_history_btn"))
        win.geometry("800x500")

        canvas = tk.Canvas(win, bg="white")
        canvas.pack(fill="both", expand=True, padx=10, pady=10)

        def redraw(event=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 50 or h < 50:
                return

            padding_left = 60
            padding_right = 20
            padding_top = 30
            padding_bottom = 40

            all_prices = [p for pts in series.values() for (_, p) in pts]
            if not all_prices:
                return

            pmin = min(all_prices)
            pmax = max(all_prices)
            if pmax == pmin:
                pmax = pmin + 1

            colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

            canvas.create_line(padding_left, h - padding_bottom, w - padding_right, h - padding_bottom, fill="#888")
            canvas.create_line(padding_left, padding_top, padding_left, h - padding_bottom, fill="#888")

            for i in range(5):
                y = padding_top + (h - padding_top - padding_bottom) * i / 4
                val = pmax - (pmax - pmin) * i / 4
                canvas.create_text(padding_left - 8, y, text=f"{val:.1f}", anchor="e", fill="#555", font=("Arial", 8))
                canvas.create_line(padding_left, y, w - padding_right, y, fill="#eee")

            for idx, (asin, pts) in enumerate(series.items()):
                if len(pts) < 1:
                    continue
                color = colors[idx % len(colors)]
                n = len(pts)
                step = (w - padding_left - padding_right) / max(n - 1, 1)

                coords = []
                for i, (ts, price) in enumerate(pts):
                    x = padding_left + step * i
                    y = padding_top + (h - padding_top - padding_bottom) * (1 - (price - pmin) / (pmax - pmin))
                    coords.append((x, y))

                for i in range(len(coords) - 1):
                    canvas.create_line(coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1], fill=color, width=2)

                for (x, y) in coords:
                    canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline=color)

                lx = padding_left + 10
                ly = padding_top + 15 + idx * 18
                canvas.create_line(lx, ly, lx + 20, ly, fill=color, width=3)
                canvas.create_text(lx + 25, ly, text=asin, anchor="w", font=("Arial", 9))

        canvas.bind("<Configure>", redraw)
        win.after(100, redraw)


if __name__ == "__main__":
    # 先检查浏览器（弹窗提示）
    _check_root = tk.Tk()
    _check_root.withdraw()

    _checking = tk.Toplevel(_check_root)
    _checking.title("Please wait")
    _checking.geometry("360x100")
    _checking.transient(_check_root)
    _checking.grab_set()
    tk.Label(_checking, text="Checking browser, please wait...").pack(pady=30)
    _checking.update()

    ok, msg = ensure_browser()

    _checking.destroy()
    _check_root.destroy()

    if not ok:
        _err = tk.Tk()
        _err.withdraw()
        messagebox.showerror("Error", msg)
        _err.destroy()
        raise SystemExit(1)

    root = tk.Tk()
    app = PriceMonitorApp(root)
    root.mainloop()