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
    // Find all elements with potential product identifiers
    const links = Array.from(document.querySelectorAll("a[href*='/product'], a[href*='SalePage'], a[href*='sale_page'], a[href*='ProductDetail']"));
    const productLinks = links.slice(0, 10).map(a => ({href: a.href, text: a.textContent.trim().substring(0, 50)}));
    
    // Try data attributes
    const dataElements = Array.from(document.querySelectorAll("[data-salepage-id], [data-product-id], [data-id], [data-sid]"));
    const dataItems = dataElements.slice(0, 5).map(el => ({
        tag: el.tagName,
        attrs: Object.fromEntries([...el.attributes].map(a => [a.name, a.value.substring(0,50)])),
        text: el.textContent.trim().substring(0, 30)
    }));
    
    // Get a sample of product card HTML
    const cards = document.querySelectorAll("[class*='SalePage'], [class*='sale-page'], [class*='product-card'], [class*='ProductCard'], [class*='ItemCard']");
    const cardSamples = Array.from(cards).slice(0, 3).map(c => c.outerHTML.substring(0, 300));
    
    return {
        productLinks: productLinks,
        dataItems: dataItems,
        cardCount: cards.length,
        cardSamples: cardSamples
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
        print("Reading DOM structure...")
        data = await page.evaluate(READ_SCRIPT)
        print("Product links:", data.get("productLinks", []))
        print("Data items:", data.get("dataItems", []))
        print("Card count:", data.get("cardCount", 0))
        for i, s in enumerate(data.get("cardSamples", [])):
            print("Card sample {}: {}".format(i, s[:200]))
        await browser.close()
    return []

def send_telegram(message):
    base = "https://api.telegram.org"
    url = base + "/bot{}/sendMessage".format(TELEGRAM_TOKEN)
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()

def main():
    products = asyncio.run(fetch_newest_products())
    send_telegram("⚠️ POLYWELL DEBUG #2: 已完成 DOM 結構分析")

if __name__ == "__main__":
    main()
