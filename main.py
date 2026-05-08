import requests
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Test Server is Online"

# تأكد أن الأرقام هذي هي اللي عندك بالضبط
TOKEN = "6828224522:AAEYH892fA-BfS6h6x6r1-2T_f6rY7f6rY7" 
CHAT_ID = "1068286006"

def start_bot():
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": "يا هلا! أنا البوت، كذا تأكدت إن الربط شغال 100% ✅"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=10000))
    t.start()
    start_bot()
