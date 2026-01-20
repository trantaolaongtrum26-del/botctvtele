from flask import Flask
from threading import Thread
import logging

# 1. Tắt toàn bộ log rác của Flask để giảm tải
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    # Trả về mã 200 OK và nội dung siêu ngắn
    return "OK", 200

def run():
    # use_reloader=False là BẮT BUỘC để tránh chạy 2 tiến trình song song gây tốn RAM
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

def keep_alive():
    t = Thread(target=run)
    t.start()
