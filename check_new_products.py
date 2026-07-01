import json
import os
import asyncio
from playwright.async_api import async_playwright
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TEMEGRAM_CHAT_ID")
STATE_FILE = "last_products.json"
TARGET_URL = "https://" + "shop.polywell.com.tw/v2/Official/NewestSalePage"
API_PATTERN = "**/graphql*shopNewestSalePage*"

async def fetch_newest_products():
    captured_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        async def handle_response(response):
            url = response.url
            if "shopNewestSalePage" in url:
                print("Intercepted URL:", url[:100])
                try:
                    body = await response.body()
                    # Try to decompress if needed
                    try:
                        import gzip
                        body = gzip.decompress(body)
                    except Exception:
                        pass
                    try:
                        import brotli
                        body = brotli.decompress(body)
                    except Exception:
                        pass
                    data = json.loads(body)
                    items = data.get("data", {}).get("shopNewestSalePage", {}).get("salePageList", {}).get("salePageList", [])
                    if items:
                        captured_data.extend(items)
                        print("Got {} items!".format(len(items)))
                    else:
                        print("Response body (no items):", str(data)[:200])
                except Exception as ex:
                    print("Parse error:", ex)

        page.on("response", handle_response)
        print("Navigating...")
        await page.goto(TARGET_URL, timeout=60000)
        print("Waiting 10s...")
        await asyncio.sleep(10)
        await browser.close()

    print("Total captured:", len(captured_data))
    return captured_data
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
            link = "https://" + "shop.polywell.com.tw/v2/Official/NewestSalePage"
            msg = "🐕 POLYWELL 新品上架！\n\n📦 {}\n💰 {}\n{}\n\n🔗 {}".format(p["title"], price_str, sold_status, link)
            send_telegram(msg)
            print("Notified: {}".format(p["title"]))
    else:
        msg = "✅ POLYWELL 監控報告：目前沒有新品上架。"
        send_telegram(msg)
        print("No new products.")

    save_current_ids(current_ids)

if __name__ == "__main__":
    main()
