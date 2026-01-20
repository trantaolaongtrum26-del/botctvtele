from flask import Flask
from threading import Thread
import logging

# Tắt log của Flask để tránh rác màn hình
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    # CHỈ TRẢ VỀ DÒNG CHỮ NGẮN GỌN NÀY THÔI
    return "I am alive!" 

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
