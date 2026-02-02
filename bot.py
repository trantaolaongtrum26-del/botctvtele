import logging
import os
import csv
import json
import asyncio
import hashlib
import hmac
import requests
import time
from datetime import datetime
from threading import Thread
from flask import Flask, request, jsonify

# Thư viện Telegram
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# ==============================================================================
# ⚙️ PHẦN 1: CẤU HÌNH HỆ THỐNG
# ==============================================================================

TOKEN_BOT = '8269134409:AAFCc7tB1kdc0et_4pnH52SoG_RyCu-UX0w'
ID_ADMIN_CHINH = 8457924201  # ID Admin nhận thông báo tiền về

# --- CẤU HÌNH CỔNG THANH TOÁN (SUSH) ---
API_URL_CREATE = "https://ezconnectdgp.com/deposit"
API_KEY = "2a10ba0198d7cabdb6ec163cc2990a95"
Private_Key = "9ccce2b2e97e8cfd5815f9492e94be32"

# --- CẤU HÌNH WEBHOOK (RENDER) ---
# QUAN TRỌNG: Thay link Render của bạn vào đây sau khi deploy
DOMAIN_RENDER = "https://botctvtele-04kd.onrender.com"
CALLBACK_URL = f"https://botctvtele-04kd.onrender.com/callback"

# --- FILE DỮ LIỆU ---
FILE_ANH_NAP = "huong-dan-nap-usdt-binance.jpg"
FILE_ANH_RUT = "huong-dan-nap-usdt.jpg"
FILE_BANNER = "BM-B1.mp4"
FILE_DATA_KHACH = "danh_sach_bao_khach.csv"
FILE_TK_CTV = "taikhoan_ctv.json"

DEFAULT_ACCOUNTS = {"ctv01": "123456", "admin": "admin888"}

# Cấu hình Log
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Trạng thái hội thoại
STATE_NORMAL = 0
STATE_WAITING_ID = 1
STATE_WAITING_PASS = 2
STATE_LOGGED_IN = 3

# ==============================================================================
# 🔧 PHẦN 2: XỬ LÝ THANH TOÁN & API (MỚI THÊM)
# ==============================================================================

def generate_checksum(body_json_str, secret_key):
    """Tính Checksum bảo mật"""
    key_bytes = secret_key.encode('utf-8')
    body_bytes = body_json_str.encode('utf-8')
    signature = hmac.new(key_bytes, body_bytes, hashlib.md5).hexdigest()
    return signature

def create_payment_order(amount, bank_type, user_id, user_name):
    """Gọi API tạo đơn nạp"""
    ref_id = f"ORDER_{user_id}_{int(time.time())}"
    
    payload = {
        "type": "bank",
        "ref_id": ref_id,
        "amount": int(amount),
        "callback": CALLBACK_URL,
        "bank_type": bank_type,
        "user_name": str(user_name)
    }
    
    # JSON dumps không được có khoảng trắng thừa
    payload_str = json.dumps(payload, separators=(',', ':'))
    checksum = generate_checksum(payload_str, Private_Key)
    
    headers = {
        'Content-Type': 'application/json',
        'APIKEY': API_KEY,
        'Checksum': checksum
    }
    
    try:
        response = requests.post(API_URL_CREATE, data=payload_str, headers=headers)
        return response.json()
    except Exception as e:
        logger.error(f"Lỗi API Payment: {e}")
        return None

# ==============================================================================
# 🌐 PHẦN 3: SERVER WEBHOOK FLASK (THAY THẾ KEEP_ALIVE)
# ==============================================================================
app = Flask(__name__)
# Tắt log rác Flask
log_flask = logging.getLogger('werkzeug')
log_flask.setLevel(logging.ERROR)

bot_app_instance = None # Biến global để gọi bot từ Flask

@app.route('/')
def index():
    return "Bot C168 Payment is running!", 200

@app.route('/callback', methods=['POST'])
async def payment_callback():
    """Nhận thông báo khi khách nạp tiền thành công"""
    try:
        data = request.json
        if data and data.get('err_code') == 0:
            amount = data.get('amount', 0)
            ref_id = data.get('ref_id', 'Unknown')
            try:
                user_id = ref_id.split('_')[1]
            except:
                user_id = "Unknown"

            # 1. Báo Admin
            msg_admin = (
                f"💰 <b>TING TING! TIỀN VỀ!</b>\n"
                f"➖➖➖➖➖➖➖➖\n"
                f"👤 User ID: <code>{user_id}</code>\n"
                f"💵 Số tiền: <b>{amount:,} VNĐ</b>\n"
                f"🆔 Mã đơn: <code>{ref_id}</code>\n"
                f"✅ <b>Trạng thái: THÀNH CÔNG</b>"
            )
            
            if bot_app_instance:
                await bot_app_instance.bot.send_message(chat_id=ID_ADMIN_CHINH, text=msg_admin, parse_mode="HTML")
                
                # 2. Báo Khách
                try:
                    if user_id.isdigit():
                        await bot_app_instance.bot.send_message(chat_id=int(user_id), text=f"✅ Giao dịch thành công! Đã nhận <b>{amount:,} VNĐ</b>.\nChúc bạn chơi vui vẻ!", parse_mode="HTML")
                except: pass

        return jsonify({"err_code": 0, "err_msg": "OK"}), 200
    except Exception as e:
        logger.error(f"Lỗi Webhook: {e}")
        return jsonify({"err_code": 1, "err_msg": "Error"}), 500

def run_flask():
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

# ==============================================================================
# 📂 PHẦN 4: CÁC HÀM XỬ LÝ DỮ LIỆU CŨ (GIỮ NGUYÊN)
# ==============================================================================
def load_ctv_accounts():
    if not os.path.exists(FILE_TK_CTV):
        with open(FILE_TK_CTV, 'w') as f: json.dump(DEFAULT_ACCOUNTS, f)
        return DEFAULT_ACCOUNTS
    try:
        with open(FILE_TK_CTV, 'r') as f: return json.load(f)
    except: return DEFAULT_ACCOUNTS

def save_ctv_accounts(accounts):
    with open(FILE_TK_CTV, 'w') as f: json.dump(accounts, f)

def luu_bao_khach(telegram_id, username_khach, ma_ctv, so_tien):
    file_exists = os.path.isfile(FILE_DATA_KHACH)
    with open(FILE_DATA_KHACH, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['ThoiGian', 'TelegramID_User', 'TenKhach', 'MaCTV', 'SoTien'])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), telegram_id, username_khach, ma_ctv, so_tien])

def dem_so_khach(ma_ctv_can_tim):
    if not os.path.exists(FILE_DATA_KHACH): return 0, 0
    tong_khach = 0
    tong_tien = 0
    with open(FILE_DATA_KHACH, mode='r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        next(reader, None)
        for row in reader:
            if len(row) >= 5:
                if row[3].strip().lower() == ma_ctv_can_tim.lower():
                    tong_khach += 1
                    try: tong_tien += int(''.join(filter(str.isdigit, row[4])))
                    except: pass
    return tong_khach, tong_tien

# ==============================================================================
# 👮 PHẦN 5: CHỨC NĂNG ADMIN & HỆ THỐNG
# ==============================================================================
async def admin_them_ctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("⚠️ VD: /themctv user pass", parse_mode="HTML"); return
        new_user, new_pass = args[0].strip(), args[1].strip()
        accounts = load_ctv_accounts()
        if new_user in accounts: await update.message.reply_text("⚠️ Đã tồn tại!"); return
        accounts[new_user] = new_pass
        save_ctv_accounts(accounts)
        await update.message.reply_text(f"✅ Đã thêm: {new_user}", parse_mode="HTML")
    except: pass

async def admin_xoa_ctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        args = context.args
        if len(args) < 1: await update.message.reply_text("⚠️ VD: /xoactv user"); return
        del_user = args[0].strip()
        accounts = load_ctv_accounts()
        if del_user not in accounts: await update.message.reply_text("⚠️ Không tìm thấy."); return
        del accounts[del_user]
        save_ctv_accounts(accounts)
        await update.message.reply_text(f"🗑️ Đã xóa: {del_user}")
    except: pass

async def admin_quan_ly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    accounts = load_ctv_accounts()
    msg = f"👑 <b>ADMIN CONTROL</b>\n👥 CTV: {len(accounts)}\n\n"
    total_money = 0
    for ma in accounts:
        sl, tien = dem_so_khach(ma)
        total_money += tien
        msg += f"👤 {ma}: {sl} khách | {tien:,} k\n"
    msg += f"\n💰 <b>TỔNG: {total_money:,} k</b>"
    await update.message.reply_text(msg, parse_mode="HTML")

async def admin_xem_chi_tiet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        if not context.args: await update.message.reply_text("⚠️ VD: /chitiet ctv01"); return
        target = context.args[0].strip().lower()
        if not os.path.exists(FILE_DATA_KHACH): return
        rows = []
        with open(FILE_DATA_KHACH, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if len(r) >= 5 and r[3].strip().lower() == target:
                    rows.append(f"🕒 {r[0][11:16]} | {r[2]} | {r[4]}")
        if not rows: await update.message.reply_text("❌ Không có dữ liệu.")
        else: await update.message.reply_text("\n".join(rows[-15:]), parse_mode="HTML")
    except: pass

async def admin_xuat_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    if os.path.exists(FILE_DATA_KHACH):
        with open(FILE_DATA_KHACH, 'rb') as f:
            await update.message.reply_document(f, filename="data.csv")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    msg = await context.bot.send_message(update.effective_chat.id, "🧹 Cleaning...")
    for i in range(1, 21):
        try: await context.bot.delete_message(update.effective_chat.id, update.message.message_id - i)
        except: pass
    await asyncio.sleep(1)
    try: await context.bot.delete_message(update.effective_chat.id, msg.message_id)
    except: pass

# ==============================================================================
# 🎮 PHẦN 6: LOGIC BOT & MENU & CALLBACK
# ==============================================================================

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý các nút bấm Inline (Nạp tiền, Chọn Bank)"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.username or "Unknown"

    # 1. KHÁCH BẤM "NẠP TỰ ĐỘNG" -> HIỆN MỆNH GIÁ
    if data == "menu_nap_tien":
        keyboard = [
            [InlineKeyboardButton("💎 50.000đ", callback_data="chon_50000")],
            [InlineKeyboardButton("💎 100.000đ", callback_data="chon_100000")],
            [InlineKeyboardButton("💎 200.000đ", callback_data="chon_200000")],
            [InlineKeyboardButton("💎 500.000đ", callback_data="chon_500000")],
            [InlineKeyboardButton("💎 1.000.000đ", callback_data="chon_1000000")],
        ]
        await query.message.reply_text("👇 Chọn <b>MỆNH GIÁ</b> muốn nạp:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    # 2. KHÁCH CHỌN TIỀN -> HIỆN BANK
    elif data.startswith("chon_"):
        amount = data.split("_")[1]
        keyboard_banks = [
            [InlineKeyboardButton("🏦 MB Bank (MBB)", callback_data=f"pay_MBB_{amount}")],
            [InlineKeyboardButton("🏦 Vietcombank (VCB)", callback_data=f"pay_VCB_{amount}")],
            [InlineKeyboardButton("🏦 ACB", callback_data=f"pay_ACB_{amount}")],
            [InlineKeyboardButton("🏦 Techcombank (TCB)", callback_data=f"pay_TCB_{amount}")],
            [InlineKeyboardButton("🏦 BIDV", callback_data=f"pay_BIDV_{amount}")],
        ]
        await query.edit_message_text(f"💰 Nạp: <b>{int(amount):,} VNĐ</b>\n👇 Chọn <b>NGÂN HÀNG</b> chuyển khoản:", reply_markup=InlineKeyboardMarkup(keyboard_banks), parse_mode="HTML")

    # 3. KHÁCH CHỌN BANK -> GỌI API -> LẤY QR
    elif data.startswith("pay_"):
        _, bank_code, amount_str = data.split("_")
        amount = int(amount_str)

        await query.edit_message_text(f"⏳ Đang kết nối <b>{bank_code}</b> lấy mã QR...", parse_mode="HTML")
        result = create_payment_order(amount, bank_code, user_id, user_name)

        if result and result.get("err_code") == 0:
            pay_url = result.get("payUrl")
            ref_id = result.get("ref_id")
            
            msg = (
                f"✅ <b>TẠO ĐƠN THÀNH CÔNG!</b>\n➖➖➖➖➖➖➖➖\n"
                f"🏦 Bank: <b>{bank_code}</b> | 💰 Tiền: <b>{amount:,} VNĐ</b>\n"
                f"🆔 Mã đơn: <code>{ref_id}</code>\n\n"
                f"🚀 <b>BẤM LINK DƯỚI ĐỂ LẤY QR CODE:</b>"
            )
            btn = []
            if pay_url: btn.append([InlineKeyboardButton("🔗 MỞ MÃ QR THANH TOÁN", url=pay_url)])
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(btn), parse_mode="HTML")
        else:
            err = result.get("err_msg") if result else "Lỗi mạng"
            await query.edit_message_text(f"❌ Lỗi: {err}. Thử ngân hàng khác nhé!", parse_mode="HTML")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = STATE_NORMAL
    menu_keyboard = [
        [KeyboardButton("🍀 Giới Thiệu Group"), KeyboardButton("🎁 Nhận Giftcode")],
        [KeyboardButton("💰 Ưu Đãi & Khuyến Mãi"), KeyboardButton("🔒 Nạp/Rút USDT An Toàn")],
        [KeyboardButton("🕵️ Dịch Vụ Thanh Toán Ẩn Danh")], 
        [KeyboardButton("🤝 Đăng Ký CTV Ngay"), KeyboardButton("👤 Tài Khoản Cá Nhân")],
        [KeyboardButton("🔐 Đăng Nhập CTV (Báo Khách)")], 
    ]
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)
    welcome_text = "👋 <b>Xin chào! Chào mừng đến với C168!!!</b>\n\n🔥 <b>NẠP ĐẦU TẶNG 8.888K</b> - Mã: <code>ND01</code>\n👉 <a href='https://c168c.cam/'><b>https://c168c.cam/</b></a>"

    if os.path.exists(FILE_BANNER):
        try:
            with open(FILE_BANNER, 'rb') as f:
                await update.message.reply_video(video=f, caption=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
        except: # Fallback nếu gửi video lỗi
             await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_state = context.user_data.get('state', STATE_NORMAL)
    
    # --- LOGIC ĐĂNG NHẬP CTV ---
    if text == "🔐 Đăng Nhập CTV (Báo Khách)":
        context.user_data['state'] = STATE_WAITING_ID
        await update.message.reply_text("👤 Nhập ID CTV:", reply_markup=ReplyKeyboardRemove()); return

    if user_state == STATE_WAITING_ID:
        accounts = load_ctv_accounts()
        if text in accounts:
            context.user_data['temp_id'] = text; context.user_data['state'] = STATE_WAITING_PASS
            await update.message.reply_text("🔑 Nhập Mật Khẩu:")
        else: await update.message.reply_text("❌ ID sai!"); return
        return

    if user_state == STATE_WAITING_PASS:
        saved_id = context.user_data.get('temp_id')
        accounts = load_ctv_accounts()
        if text == accounts.get(saved_id):
            context.user_data['state'] = STATE_LOGGED_IN; context.user_data['logged_ctv_code'] = saved_id
            kb = [[KeyboardButton("📊 Xem Thống Kê"), KeyboardButton("📞 Lấy File Đối Soát")], [KeyboardButton("❌ Đăng Xuất")]]
            await update.message.reply_text(f"🎉 Login thành công: {saved_id}", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        else: await update.message.reply_text("❌ Sai mật khẩu!")
        return

    # --- MENU CTV ---
    if user_state == STATE_LOGGED_IN:
        current_ctv = context.user_data.get('logged_ctv_code')
        if text == "❌ Đăng Xuất": await start(update, context); return
        elif text == "📊 Xem Thống Kê":
            sl, tien = dem_so_khach(current_ctv)
            await update.message.reply_text(f"📊 <b>{current_ctv}</b>: {sl} khách | {tien:,} k", parse_mode="HTML"); return
        elif text == "📞 Lấy File Đối Soát": await update.message.reply_text("📞 LH Admin: @Bez_api"); return
        if not text.startswith('/'): await update.message.reply_text("💡 Dùng lệnh /F ...", parse_mode="HTML"); return

    # --- MENU CHÍNH ---
    msg = ""
    if text == "🍀 Giới Thiệu Group": msg = "🌿 <b>CỘNG ĐỒNG XÔI MẶN</b>\n👉 <a href='https://t.me/congdongxoiman'>t.me/congdongxoiman</a>"
    elif text == "🎁 Nhận Giftcode": msg = "🎁 <b>KHO GIFTCODE</b>\n👉 <a href='https://hupcode.xo.je'>hupcode.xo.je</a>"
    elif text == "💰 Ưu Đãi & Khuyến Mãi": msg = "🧧 <b>KHUYẾN MÃI TẾT 2026</b>\n• Nạp đầu 150%\n• Hoàn trả 1.2%..."
    
    # === CẬP NHẬT PHẦN NẠP TIỀN ===
    elif text == "🔒 Nạp/Rút USDT An Toàn":
        msg = (
            "💳 <b>CỔNG THANH TOÁN TỰ ĐỘNG C168</b>\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "1️⃣ <b>Nạp USDT:</b> Vui lòng làm theo ảnh hướng dẫn bên dưới.\n"
            "2️⃣ <b>Nạp Bank/QR (Siêu Tốc):</b> Bấm nút bên dưới để lấy mã QR chuyển khoản tự động.\n\n"
            "<i>Hệ thống tự động cộng điểm sau 1-3 phút.</i>"
        )
        # Nút bấm kích hoạt Inline Menu
        keyboard_nap = [[InlineKeyboardButton("⚡ Nạp Tự Động (Lấy QR)", callback_data="menu_nap_tien")]]
        
        if os.path.exists(FILE_ANH_NAP):
            with open(FILE_ANH_NAP, 'rb') as f:
                await context.bot.send_photo(update.effective_chat.id, photo=f, caption=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_nap))
        else:
            await context.bot.send_message(update.effective_chat.id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_nap))
        return

    elif text == "🕵️ Dịch Vụ Thanh Toán Ẩn Danh": msg = "🛡️ <b>DỊCH VỤ ẨN DANH</b>\nPhí 0.1% - LH: @Bez_api"
    elif text == "🤝 Đăng Ký CTV Ngay": msg = "🤝 <b>TUYỂN DỤNG CTV</b>\nHoa hồng cao - LH: @Bez_api"
    elif text == "👤 Tài Khoản Cá Nhân": msg = f"👤 ID: {update.effective_user.id}\n@{update.effective_user.username}"
    elif text == "📢 Báo Khách / Hỗ Trợ": msg = "✅ Đã gửi hỗ trợ. Admin sẽ phản hồi sớm."
    else: msg = "🤔 Chọn menu bên dưới."

    if msg: await context.bot.send_message(update.effective_chat.id, text=msg, parse_mode="HTML", disable_web_page_preview=True)

async def command_bao_khach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Logic báo khách cũ (giữ nguyên)
    if context.user_data.get('state') != STATE_LOGGED_IN:
        await update.message.reply_text("⚠️ Cần đăng nhập CTV!"); return
    try:
        parts = update.message.text[3:].strip().split('-')
        if len(parts) < 3: raise ValueError
        ten, ma, tien = parts[0].strip(), parts[1].strip(), parts[2].strip()
        current = context.user_data.get('logged_ctv_code')
        if ma.lower() != current.lower(): await update.message.reply_text("⚠️ Sai mã CTV!"); return
        luu_bao_khach(update.effective_user.id, ten, ma, tien)
        await update.message.reply_text(f"✅ Báo thành công: {ten} - {tien}")
    except: await update.message.reply_text("⚠️ Sai mẫu: /F Tên - Mã - Tiền")

# ==============================================================================
# 🚀 MAIN EXECUTION
# ==============================================================================
def main():
    # 1. Chạy Webhook Flask (Thay cho keep_alive)
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    print("🚀 Bot đang khởi động...")
    global bot_app_instance
    bot_app_instance = ApplicationBuilder().token(TOKEN_BOT).build()

    # Handlers
    bot_app_instance.add_handler(CommandHandler('start', start))
    bot_app_instance.add_handler(CommandHandler(['xoa', 'cls'], clear_chat))
    bot_app_instance.add_handler(CommandHandler(['F', 'f'], command_bao_khach))
    bot_app_instance.add_handler(CommandHandler(['admin', 'quanly'], admin_quan_ly))
    bot_app_instance.add_handler(CommandHandler('themctv', admin_them_ctv))
    bot_app_instance.add_handler(CommandHandler('xoactv', admin_xoa_ctv))
    bot_app_instance.add_handler(CommandHandler('chitiet', admin_xem_chi_tiet))
    bot_app_instance.add_handler(CommandHandler(['xuatfile', 'export'], admin_xuat_file))
    
    # Callback Handler (Quan trọng cho nút bấm Nạp tiền)
    bot_app_instance.add_handler(CallbackQueryHandler(handle_callback_query))
    
    bot_app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    bot_app_instance.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

