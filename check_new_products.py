import requests
import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    resp = requests.post(url, json=payload, timeout=10)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    resp.raise_for_status()

msg = "[TEST] POLYWELL Monitor OK! Bot is working correctly."
send_telegram(msg)
print("Done!")
