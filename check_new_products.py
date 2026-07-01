import json
import os
import asyncio
from playwright.async_api import async_playwright
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TEMEGRAM_CHAT_ID")
STATE_FILE = "last_products.json"
TARGET_URL = "https://" + "shop.polywell.com.tw/v2/Official/NewestSalePage"

READ_SCRIPT = """
() => {
    // Try to find product data in window object
    const sources = [
        window.__NEXT_DATA__,
        window.__NUXT__,
        window.__INITIAL_STATE__,
        window.__redux_state__,
        window.__APP_DATA__,
    ];

    // Try DOM scraping as fallback
    const productCards = document.querySelectorAll("[class*='product'], [class*='item'], [data-product-id]");
    const domProducts = [];
    productCards.forEach(card => {
        const id = card.getAttribute("data-product-id") || card.getAttribute("data-id");
        const titleEl = card.querySelector("[class*='title'], [class*='name'], h3, h4");
        if (id || titleEl) {
            domProducts.push({
                salePageId: id || Math.random(),
                title: titleEl ? titleEl.textContent.trim() : "unknown",
            });
        }
    });

    return {
        windowSources: sources.filter(x => x != null).map(x => JSON.stringify(x).substring(0, 200)),
        domProducts: domProducts.slice(0, 5),
        windowKeys: Object.keys(window).filter(k => k.startsWith("__")).join(", "),
        bodyTextSample: document.body.innerText.substring(0, 500)
    };
}
"""

async def fetch_newest_products():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        print("Loading page...")
        await page.goto(TARGET_URL, timeout=60000, wait_until="networkidle")
        await asyncio.sleep(3)
        print("Reading page data...")
        data = await page.evaluate(READ_SCRIPT)
        print("Window keys:", data.get("windowKeys", "none"))
        print("DOM products:", len(data.get("domProducts", [])))
        print("Window sources:", data.get("windowSources", []))
        print("Body text:", data.get("bodyTextSample", "")[:200])
        await browser.close()
    return []

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
    products = asyncio.run(fetch_newest_products())
    send_telegram("⚠️ POLYWELL DEBUG: 已完成頁面分析，請檢查 GitHub Actions 日誌")

if __name__ == "__main__":
    main()
