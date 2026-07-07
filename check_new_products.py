import json
import os
import re
import asyncio
from playwright.async_api import async_playwright
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "last_products.json"
TARGET_URL = "https://" + "shop.polywell.com.tw/v2/Official/NewestSalePage"

SCRAPE_SCRIPT = """
() => {
// Find all product card links with /SalePage/Index/{id}
const cards = document.querySelectorAll("a[href*='/SalePage/Index/']");
const products = [];
const seen = new Set();
cards.forEach(card => {
const href = card.getAttribute("href") || "";
const match = href.match(/\/SalePage\/Index\/(\d+)/);
if (!match) return;
const salePageId = match[1];
if (seen.has(salePageId)) return;
seen.add(salePageId);
const titleEl = card.querySelector("[class*='title'], [class*='name'], strong, p");
const title = titleEl ? titleEl.textContent.trim() : card.textContent.trim().substring(0, 60);
const priceEls = card.querySelectorAll("[class*='price'], [class*='Price']");
let price = "";
priceEls.forEach(el => { price += el.textContent.trim() + " "; });
products.push({ salePageId: salePageId, title: title, priceText: price.trim() });
});
return products;
}
"""

async def fetch_newest_products():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        await page.goto(TARGET_URL, timeout=60000, wait_until="networkidle")
        await asyncio.sleep(3)
        products = await page.evaluate(SCRAPE_SCRIPT)
        await browser.close()
        print("Scraped {} products".format(len(products)))
        return products

def load_last_ids():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_current_ids(ids):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(ids), f)

def send_telegram(message):
    base = "https://api.telegram.org"
    url = base + "/bot{}/sendMessage".format(TELEGRAM_TOKEN)
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()

def main():
    try:
        products = asyncio.run(fetch_newest_products())
    except Exception as e:
        err_msg = "⚠️ POLYWELL 監控錯誤：{}".format(e)
        print(err_msg)
        send_telegram(err_msg)
        return

    if not products:
        err_msg = "⚠️ POLYWELL 監控錯誤：無法取得商品資料"
        print(err_msg)
        send_telegram(err_msg)
        return

    print("Fetched {} products.".format(len(products)))
    current_ids = {p["salePageId"] for p in products}
    last_ids = load_last_ids()

    if not last_ids:
        save_current_ids(current_ids)
        print("First run: saved {} products.".format(len(current_ids)))
        return

    new_ids = current_ids - last_ids
    new_products = [p for p in products if p["salePageId"] in new_ids]

    if new_products:
        print("Found {} new product(s)!".format(len(new_products)))
        for p in new_products:
            link = "https://" + "shop.polywell.com.tw/SalePage/Index/{}".format(p["salePageId"])
            msg = "🐕 POLYWELL 新品上架！\n\n📦 {}\n💰 {}\n\n🔗 {}".format(
                p["title"], p.get("priceText", ""), link)
            send_telegram(msg)
            print("Notified: {}".format(p["title"]))
    else:
        msg = "✅ POLYWELL 監控報告：目前沒有新品上架。"
        send_telegram(msg)
        print("No new products.")

    save_current_ids(current_ids)

if __name__ == "__main__":
    main()
