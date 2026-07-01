import requests
import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    print("Telegram notification sent successfully!")

msg = (
    "\ud83d\udd27 <b>PELYPÅL MONITOR \u6dd8\u8a74\u7f4d\u4f7f<u7f6e</b>\n\n"
    "\u2f55 \u76f4\u63a5\u5235\u8fdf\u9001\u901a\u77e5\u6a1f\u80fd\u6253\u8116\u529f\uff01\n\n"
    "\ud83d\udc15 <b>\u76ee\u5728\u7a7a\u767b\u55ac\u8b84 POLYWELL \u65b0\u54c1\u4e0a\u67b6</b>\n\n"
    "\ud83d\udce6 CAT6A \u9030\u9015\u7f50\u8eaa\u7fda 45\u5165 RGJ45\n"
    "\ud83d\udcb0 \u539f\u50f9 <s>$240</s> \u2192 \u73fe\u5728 <b>$95</b>\n"
    "\u2705 \u73fe\u8ca8\n\n"
    "\ud83d\udd17 https://shop.polywell.com.tw/v2/Official/NewestSalePage"
)

send_telegram(msg)
