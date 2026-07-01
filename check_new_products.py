import requests
import json
import os

GRAPHQL_URL = "https://fts-api.91app.com/pythia-cdn/graphql"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TEMEGRAM_CHAT_ID")
STATE_FILE = "last_products.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://shop.polywell.com.tw/",
    "Origin": "https://shop.polywell.com.tw",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

QUERY = """
query cms_shopNewestSalePage($shopId: Int!, $startIndex: Int!, $fetchCount: Int!) {
  shopNewestSalePage(shopId: $shopId) {
    salePageList(startIndex: $startIndex, maxCount: $fetchCount) {
      salePageList {
        salePageId
        title
        price
        suggestPrice
        isSoldOut
      }
      totalSize
    }
  }
}
"""

def fetch_newest_products():
    payload = {
        "operationName": "cms_shopNewestSalePage",
        "query": QUERY.strip(),
        "variables": {
            "shopId": 42027,
            "startIndex": 0,
            "fetchCount": 50
        }
    }
    resp = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["shopNewestSalePage"]["salePageList"]["salePageList"]

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
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()

def main():
    try:
        products = fetch_newest_products()
    except Exception as e:
        err_msg = "⚠️ POLYWELL 監控錯誤：API 呢叫失敗 - {}".format(e)
        print(err_msg)
        send_telegram(err_msg)
        return

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
