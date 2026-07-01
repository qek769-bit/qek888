import json
import os
import asyncio
from playwright.async_api import async_playwright
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TEMEGRAM_CHAT_ID")
STATE_FILE = "last_products.json"
TARGET_URL = "https://shop.polywell.com.tw/v2/Official/NewestSalePage"
API_KEYWORD = "91app.com"

async def fetch_newest_products():
    captured = []
    all_api_urls = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        async def handle_response(response):
            url = response.url
            if "91app.com" in url:
                all_api_urls.append(url[:120])
            if "shopNewestSalePage" in url or "NewestSalePage" in url or "newestSalePage" in url.lower():
                try:
                    data = await response.json()
                    items = data.get("data", {}).get("shopNewestSalePage", {}).get("salePageList", {}).get("salePageList", [])
                    if items:
                        captured.extend(items)
                        print("Captured {} items from: {}".format(len(items), url[:80]))
                except Exception as ex:
                    print("Parse error: {}".format(ex))

        page.on("response", handle_response)
        print("Navigating to page...")
        await page.goto(TARGET_URL, timeout=60000)
        print("Waiting for network...")
        await asyncio.sleep(8)
        await browser.close()

    print("All 91app API URLs found: {}", len(all_api_urls))
    for u in all_api_urls[:10]:
        print("  URL:", u)
    return captured

def load_last_ids():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_current_ids(ids):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(ids), f)

def send_telegram(message):
    url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_TOKEN)
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
    current_ids = {str(p["salePageId"]) for p in products}
    last_ids = load_last_ids()

    if not last_ids:
        save_current_ids(current_ids)
        print("First run: saved {} products.".format(len(current_ids)))
        return

    new_ids = current_ids - last_ids
    new_products = [p for p in products if str(p["salePageId"]) in new_ids]

    if new_products:
        print("Found {} new product(s)!".format(len(new_products)))
        for p in new_products:
            orig = p.get("suggestPrice") or 0
            curr = p.get("price") or 0
            if orig and orig != curr:
                price_str = "原價 ${} → 現在 ${}".format(orig, curr)
            else:
                price_str = "${}".format(curr)
            sold_status = "巷售完" if p.get("isSoldOut") else "現貨"
            msg = "🐕 POLYWELL 新品上架！\n\n📦 {}\n💰 {}\n{}\n\n🔗 https://shop.polywell.com.tw/v2/Official/NewestSalePage".format(p["title"], price_str, sold_status)
            send_telegram(msg)
            print("Notified: {}".format(p["title"]))
    else:
        msg = "✅ POLYWELL 監控報告：目前沒有新品上架。"
        send_telegram(msg)
        print("No new products.")

    save_current_ids(current_ids)

if __name__ == "__main__":
    main()
