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
API_BASE_URL = "https://ezconnectdgp.com"
API_KEY = "2a10ba0198d7cabdb6ec163cc2990a95"
Private_Key = "9ccce2b2e97e8cfd5815f9492e94be32"

# --- CẤU HÌNH WEBHOOK (RENDER) ---
# Link Render của bạn (đảm bảo đúng link sau khi deploy xong)
DOMAIN_RENDER = "https://botctvtele-04kd.onrender.com"
CALLBACK_URL = f"{DOMAIN_RENDER}/callback"

# --- FILE DỮ LIỆU ---
FILE_ANH_NAP = "huong-dan-nap-usdt-binance.jpg"
FILE_BANNER = "banner.png" # Dùng ảnh nhẹ để tránh lỗi deploy
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
STATE_WAITING_CUSTOM_AMOUNT = 4  # Trạng thái chờ khách nhập số tiền khác

# ==============================================================================
# 🔧 PHẦN 2: XỬ LÝ THANH TOÁN & API
# ==============================================================================

def generate_checksum(body_json_str, secret_key):
    """Tính Checksum: hex(hmac_md5(body))"""
    key_bytes = secret_key.encode('utf-8')
    body_bytes = body_json_str.encode('utf-8')
    signature = hmac.new(key_bytes, body_bytes, hashlib.md5).hexdigest()
    return signature

def get_bank_list():
    """Gọi API lấy danh sách ngân hàng hoạt động"""
    url = f"{API_BASE_URL}/deposit/banks"
    headers = {'Content-Type': 'application/json', 'APIKEY': API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if data.get('err_code') == 0:
            return data.get('banks', [])
        return []
    except Exception as e:
        logger.error(f"Lỗi lấy bank list: {e}")
        return []

def create_payment_order(amount, bank_type, user_id, user_name):
    """Gọi API tạo đơn nạp"""
    ref_id = f"ORDER_{user_id}_{int(time.time())}"
    
    # Payload chuẩn để tạo đơn
    payload = {
        "type": "bank",
        "ref_id": ref_id,
        "bank_type": bank_type,
        "amount": int(amount),
        "callback": CALLBACK_URL,
        "user_name": str(user_name)
    }
    
    # JSON compact (không dấu cách) để tính checksum chính xác
    payload_str = json.dumps(payload, separators=(',', ':'))
    checksum = generate_checksum(payload_str, Private_Key)
    
    headers = {
        'Content-Type': 'application/json',
        'APIKEY': API_KEY,
        'Checksum': checksum
    }
    
    try:
        # Gửi request POST
        response = requests.post(f"{API_BASE_URL}/deposit", data=payload_str, headers=headers, timeout=15)
        return response.json()
    except Exception as e:
        logger.error(f"Lỗi API Payment: {e}")
        return None

# ==============================================================================
# 🌐 PHẦN 3: SERVER WEBHOOK FLASK
# ==============================================================================
app = Flask(__name__)
log_flask = logging.getLogger('werkzeug')
log_flask.setLevel(logging.ERROR)

bot_app_instance = None 

@app.route('/')
def index():
    return "Bot Payment Service is Running!", 200

@app.route('/callback', methods=['POST'])
async def payment_callback():
    """Nhận thông báo tiền về từ cổng thanh toán"""
    try:
        data = request.json
        # Check err_code = 0 là thành công
        if data and data.get('err_code') == 0:
            amount = data.get('amount', 0)
            ref_id = data.get('ref_id', 'Unknown')
            
            # Lấy ID khách từ ref_id (Format: ORDER_IDKhach_Time)
            try:
                user_id = ref_id.split('_')[1]
            except:
                user_id = "Unknown"

            # 1. Báo Admin
            msg_admin = (
                f"💰 <b>TING TING! TIỀN VỀ!</b>\n"
                f"➖➖➖➖➖➖➖➖\n"
                f"👤 Khách ID: <code>{user_id}</code>\n"
                f"💵 Số tiền: <b>{amount:,} VNĐ</b>\n"
                f"🆔 Mã đơn: <code>{ref_id}</code>\n"
                f"✅ <b>Trạng thái: THÀNH CÔNG</b>"
            )
            
            if bot_app_instance:
                # Gửi cho Admin
                await bot_app_instance.bot.send_message(chat_id=ID_ADMIN_CHINH, text=msg_admin, parse_mode="HTML")
                
                # 2. Báo cho Khách (nếu ID hợp lệ)
                try:
                    if str(user_id).isdigit():
                        await bot_app_instance.bot.send_message(
                            chat_id=int(user_id), 
                            text=f"✅ <b>NẠP TIỀN THÀNH CÔNG!</b>\n\nBạn đã nhận được: <b>{amount:,} VNĐ</b>\nChúc bạn chơi vui vẻ!", 
                            parse_mode="HTML"
                        )
                except: pass

        return jsonify({"err_code": 0, "err_msg": "OK"}), 200
    except Exception as e:
        logger.error(f"Lỗi Webhook: {e}")
        return jsonify({"err_code": 1, "err_msg": "Error"}), 500

def run_flask():
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

# ==============================================================================
# 📂 PHẦN 4: QUẢN LÝ DỮ LIỆU & CTV (GIỮ NGUYÊN)
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
# 👮 PHẦN 5: CHỨC NĂNG ADMIN
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

async def show_bank_selection(update_obj, amount):
    """Hàm hiển thị danh sách ngân hàng tự động"""
    # Gửi tin nhắn chờ
    if hasattr(update_obj, 'message'):
        msg_wait = await update_obj.message.reply_text("⏳ Đang tải danh sách ngân hàng...")
    else:
        # Trường hợp callback query
        msg_wait = None

    # Lấy list bank từ API
    banks = get_bank_list()
    
    # Xóa tin nhắn chờ nếu có
    if msg_wait:
        try: await msg_wait.delete()
        except: pass

    if not banks:
        # Fallback nếu API lỗi hoặc bảo trì
        txt_err = "❌ Hệ thống ngân hàng đang bảo trì. Vui lòng thử lại sau ít phút!"
        if hasattr(update_obj, 'message'):
            await update_obj.message.reply_text(txt_err)
        else:
            await update_obj.edit_message_text(txt_err)
        return

    # Tạo nút bấm động từ danh sách API trả về
    keyboard = []
    for bank in banks:
        b_type = bank.get('bank_type')
        b_name = bank.get('bank_name')
        # Format callback: pay_MABANK_SOTIEN
        keyboard.append([InlineKeyboardButton(f"🏦 {b_name} ({b_type})", callback_data=f"pay_{b_type}_{amount}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data="menu_nap_tien")])

    text_msg = f"💰 Nạp: <b>{int(amount):,} VNĐ</b>\n👇 Vui lòng chọn <b>NGÂN HÀNG</b> chuyển khoản:"
    
    if hasattr(update_obj, 'message'):
        # Nếu gọi từ nhập text (nhập số khác)
        await update_obj.message.reply_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        # Nếu gọi từ callback (chọn mệnh giá có sẵn)
        await update_obj.edit_message_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý sự kiện bấm nút Inline"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.username or "Unknown"

    # 1. BẤM "NẠP TỰ ĐỘNG"
    if data == "menu_nap_tien":
        context.user_data['state'] = STATE_NORMAL # Reset trạng thái
        keyboard = [
            [InlineKeyboardButton("💎 50.000đ", callback_data="chon_50000")],
            [InlineKeyboardButton("💎 100.000đ", callback_data="chon_100000")],
            [InlineKeyboardButton("💎 200.000đ", callback_data="chon_200000")],
            [InlineKeyboardButton("💎 500.000đ", callback_data="chon_500000")],
            [InlineKeyboardButton("💎 1.000.000đ", callback_data="chon_1000000")],
            [InlineKeyboardButton("✏️ Nhập Số Khác", callback_data="nhap_khac")], # Nút nhập tay
        ]
        await query.message.reply_text("👇 Chọn <b>MỆNH GIÁ</b> muốn nạp:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    # 2. KHÁCH CHỌN TIỀN CÓ SẴN
    elif data.startswith("chon_"):
        amount = data.split("_")[1]
        await show_bank_selection(query, amount)

    # 3. KHÁCH CHỌN "NHẬP SỐ KHÁC"
    elif data == "nhap_khac":
        context.user_data['state'] = STATE_WAITING_CUSTOM_AMOUNT
        await query.message.reply_text("✏️ Vui lòng nhập số tiền muốn nạp (VD: 150000):")

    # 4. KHÁCH CHỌN BANK -> TẠO ĐƠN
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
                f"🏦 Ngân hàng: <b>{bank_code}</b>\n"
                f"💰 Số tiền: <b>{amount:,} VNĐ</b>\n"
                f"🆔 Mã đơn: <code>{ref_id}</code>\n\n"
                f"🚀 <b>BẤM NÚT DƯỚI ĐỂ LẤY MÃ QR:</b>"
            )
            btn = []
            if pay_url: 
                btn.append([InlineKeyboardButton("🔗 MỞ MÃ QR THANH TOÁN", url=pay_url)])
            
            # Thêm nút kiểm tra trạng thái (dự phòng nếu webhook chậm)
            btn.append([InlineKeyboardButton("🔙 Menu Chính", callback_data="menu_nap_tien")])

            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(btn), parse_mode="HTML")
        else:
            err = result.get("err_msg") if result else "Lỗi kết nối"
            await query.edit_message_text(f"❌ Lỗi: {err}. Vui lòng thử lại sau!", parse_mode="HTML")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = STATE_NORMAL
    
    # MENU CHÍNH
    menu_keyboard = [
        [KeyboardButton("💳 NẠP TIỀN (AUTO)"), KeyboardButton("🎁 Nhận Giftcode")], 
        [KeyboardButton("💰 Ưu Đãi & Khuyến Mãi"), KeyboardButton("🍀 Giới Thiệu Group")],
        [KeyboardButton("🕵️ Dịch Vụ Thanh Toán Ẩn Danh")], 
        [KeyboardButton("🤝 Đăng Ký CTV Ngay"), KeyboardButton("👤 Tài Khoản Cá Nhân")],
        [KeyboardButton("🔐 Đăng Nhập CTV (Báo Khách)")], 
    ]
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)
    
    welcome_text = "👋 <b>Xin chào! Chào mừng đến với C168!!!</b>\n\n🔥 <b>NẠP ĐẦU TẶNG 8.888K</b> - Mã: <code>ND01</code>\n👉 <a href='https://c168c.cam/'><b>https://c168c.cam/</b></a>"

    if os.path.exists(FILE_BANNER):
        try:
            with open(FILE_BANNER, 'rb') as f:
                await update.message.reply_photo(photo=f, caption=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
        except: 
             await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_state = context.user_data.get('state', STATE_NORMAL)
    
    # --- LOGIC XỬ LÝ NHẬP SỐ TIỀN KHÁC ---
    if user_state == STATE_WAITING_CUSTOM_AMOUNT:
        if text.isdigit():
            amount = int(text)
            if amount < 20000: # Giới hạn min nạp
                await update.message.reply_text("⚠️ Số tiền nạp tối thiểu là 20,000đ. Vui lòng nhập lại:")
                return
            # Số hợp lệ -> Reset state -> Gọi hàm chọn bank
            context.user_data['state'] = STATE_NORMAL
            await show_bank_selection(update, amount)
        else:
            await update.message.reply_text("❌ Vui lòng chỉ nhập số (Ví dụ: 200000):")
        return

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
    
    # === NÚT NẠP TIỀN AUTO ===
    elif text == "💳 NẠP TIỀN (AUTO)":
        msg = (
            "💳 <b>CỔNG NẠP TIỀN TỰ ĐỘNG</b>\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "👇 <b>Vui lòng chọn hình thức nạp:</b>\n"
            "<i>(Hệ thống tự động lên điểm sau 1-3 phút)</i>"
        )
        keyboard_nap = [
            [InlineKeyboardButton("⚡ Nạp Bank/QR (Tự động)", callback_data="menu_nap_tien")],
            [InlineKeyboardButton("💎 Hướng dẫn nạp USDT", callback_data="huong_dan_usdt")]
        ]
        
        if os.path.exists(FILE_ANH_NAP):
             with open(FILE_ANH_NAP, 'rb') as f:
                await context.bot.send_photo(update.effective_chat.id, photo=f, caption=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_nap))
        else:
             await context.bot.send_message(update.effective_chat.id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_nap))
        return

    # Hỗ trợ nút cũ
    elif text == "🔒 Nạp/Rút USDT An Toàn":
        keyboard_nap = [[InlineKeyboardButton("⚡ Nạp Tự Động (Lấy QR)", callback_data="menu_nap_tien")]]
        await context.bot.send_message(update.effective_chat.id, text="👇 Bấm bên dưới để lấy QR:", reply_markup=InlineKeyboardMarkup(keyboard_nap))
        return

    elif text == "🕵️ Dịch Vụ Thanh Toán Ẩn Danh": msg = "🛡️ <b>DỊCH VỤ ẨN DANH</b>\nPhí 0.1% - LH: @Bez_api"
    elif text == "🤝 Đăng Ký CTV Ngay": msg = "🤝 <b>TUYỂN DỤNG CTV</b>\nHoa hồng cao - LH: @Bez_api"
    elif text == "👤 Tài Khoản Cá Nhân": msg = f"👤 ID: {update.effective_user.id}\n@{update.effective_user.username}"
    elif text == "📢 Báo Khách / Hỗ Trợ": msg = "✅ Đã gửi hỗ trợ. Admin sẽ phản hồi sớm."
    else: msg = "🤔 Chọn menu bên dưới."

    if msg: await context.bot.send_message(update.effective_chat.id, text=msg, parse_mode="HTML", disable_web_page_preview=True)

async def command_bao_khach(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    print("🚀 Bot đang khởi động...")
    global bot_app_instance
    bot_app_instance = ApplicationBuilder().token(TOKEN_BOT).build()

    bot_app_instance.add_handler(CommandHandler('start', start))
    bot_app_instance.add_handler(CommandHandler(['xoa', 'cls'], clear_chat))
    bot_app_instance.add_handler(CommandHandler(['F', 'f'], command_bao_khach))
    bot_app_instance.add_handler(CommandHandler(['admin', 'quanly'], admin_quan_ly))
    bot_app_instance.add_handler(CommandHandler('themctv', admin_them_ctv))
    bot_app_instance.add_handler(CommandHandler('xoactv', admin_xoa_ctv))
    bot_app_instance.add_handler(CommandHandler('chitiet', admin_xem_chi_tiet))
    bot_app_instance.add_handler(CommandHandler(['xuatfile', 'export'], admin_xuat_file))
    
    bot_app_instance.add_handler(CallbackQueryHandler(handle_callback_query))
    bot_app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    bot_app_instance.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
