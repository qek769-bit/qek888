import requests
import json
import os

GRAPHQL_URL = "https://fts-api.91app.com/pythia-cdn/graphql"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TEMEGRAM_CHAT_ID")
STATE_FILE = "last_products.json"

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
    params = {
        "operationName": "cms_shopNewestSalePage",
        "query": QUERY.strip(),
        "variables": json.dumps({
            "shopId": 42027,
            "startIndex": 0,
            "fetchCount": 50
        })
    }
    resp = requests.get(GRAPHQL_URL, params=params, timeout=15)
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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()

def main():
    try:
        products = fetch_newest_products()
    except Exception as e:
        print(f"API error: {e}")
        return

    current_ids = {str(p["salePageId"]) for p in products}
    last_ids = load_last_ids()

    if not last_ids:
        save_current_ids(current_ids)
        print(f"First run: saved {len(current_ids)} products.")
        return

    new_ids = current_ids - last_ids
    new_products = [p for p in products if str(p["salePageId"]) in new_ids]

    if new_products:
        print(f"Found {len(new_products)} new product(s)!")
        for p in new_products:
            orig = p.get("suggestPrice") or 0
            curr = p.get("price") or 0
            if orig and orig != curr:
                price_str = f"\u539f\u50f9 <s>${orig}</s> \u2192 \u73fe\u5728 <b>${curr}</b>"
            else:
                price_str = f"<b>${curr}</b>"
            msg = (
                f"\ud83d\udc15 <b>POLYWELL \u65b0\u54c1\u4e0a\u67b6\uff01</b>\n\n"
                f"\ud83d\udce6 {p['title']}\n"
                f"\ud83d\udcb0 {price_str}\n"
                f"{'\ud83d\udeab \u5df7\u552e\u5b8c' if p.get('isSoldOut') else '\u2705 \u73fe\u8ca8'}\n\n"
                f"\ud83d\udd17 https://shop.polywell.com.tw/v2/Official/NewestSalePage"
            )
            send_telegram(msg)
            print(f"Notified: {p['title']}")
    else:
        print("No new products.")

    save_current_ids(current_ids)

if __name__ == "__main__":
    main()
