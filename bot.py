import logging
import os
import csv
import json
import asyncio
from datetime import datetime
import hashlib
import hmac
import requests

# Xử lý keep_alive
try:
    from keep_alive import keep_alive
except ImportError:
    def keep_alive(): pass 

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ================== 1. CẤU HÌNH HỆ THỐNG ==================
# ⚠️ Thay TOKEN và ID Admin của bạn vào đây
TOKEN_BOT = '8269134409:AAFCc7tB1kdc0et_4pnH52SoG_RyCu-UX0w'
ID_ADMIN_CHINH = 8457924201 

# === CẤU HÌNH API PAYMENT ===
API_BASE_URL = "https://ezconnectdgp.com"
API_KEY = "2a10ba0198d7cabdb6ec163cc2990a95"
SECRET_KEY = "9ccce2b2e97e8cfd5815f9492e94be32"

# === CẤU HÌNH FILE ẢNH & DỮ LIỆU ===
# ⚠️ CẬP NHẬT TÊN FILE ẢNH CỦA BẠN TẠI ĐÂY
FILE_BANNER_START = "banner.png"          # <--- Ảnh chào mừng (thay cho video cũ)
FILE_BANNER_INTRO = "banner_gioi_thieu.jpg"       # Ảnh Banner khi bấm Giới Thiệu
FILE_ANH_NAP = "huong-dan-nap-usdt-binance.jpg"   # Ảnh hướng dẫn nạp USDT
FILE_DATA_KHACH = "danh_sach_bao_khach.csv"
FILE_TK_CTV = "taikhoan_ctv.json"

# === HẰNG SỐ ===
BTN_BACK_MAIN = "🔙 Quay lại Menu Chính"
CALLBACK_URL = "https://example.com/callback"

DEFAULT_ACCOUNTS = {
    "ctv01": "123456",
    "admin": "admin888"
}

# Cấu hình Log
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Các trạng thái hội thoại
STATE_NORMAL = 0
STATE_WAITING_ID = 1
STATE_WAITING_PASS = 2
STATE_LOGGED_IN = 3
STATE_WAITING_DEPOSIT_AMOUNT = 4
STATE_WAITING_NETWORK = 5
STATE_WAITING_CARD_TELCO = 6
STATE_WAITING_CARD_SERIAL = 7
STATE_WAITING_CARD_CODE = 8

# ================== 2. CÁC HÀM XỬ LÝ DỮ LIỆU ==================
def load_ctv_accounts():
    if not os.path.exists(FILE_TK_CTV):
        with open(FILE_TK_CTV, 'w') as f:
            json.dump(DEFAULT_ACCOUNTS, f)
        return DEFAULT_ACCOUNTS
    try:
        with open(FILE_TK_CTV, 'r') as f:
            return json.load(f)
    except:
        return DEFAULT_ACCOUNTS

def save_ctv_accounts(accounts):
    with open(FILE_TK_CTV, 'w') as f:
        json.dump(accounts, f)

def luu_bao_khach(telegram_id, username_khach, ma_ctv, so_tien):
    file_exists = os.path.isfile(FILE_DATA_KHACH)
    with open(FILE_DATA_KHACH, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['ThoiGian', 'TelegramID_User', 'TenKhach', 'MaCTV', 'SoTien'])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), telegram_id, username_khach, ma_ctv, so_tien])

def dem_so_khach(ma_ctv_can_tim):
    if not os.path.exists(FILE_DATA_KHACH):
        return 0, 0
    tong_khach = 0
    tong_tien = 0
    with open(FILE_DATA_KHACH, mode='r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        next(reader, None)
        for row in reader:
            if len(row) >= 5:
                if row[3].strip().lower() == ma_ctv_can_tim.lower():
                    tong_khach += 1
                    try:
                        tien_clean = ''.join(filter(str.isdigit, row[4]))
                        tong_tien += int(tien_clean)
                    except: pass
    return tong_khach, tong_tien

# ================== 3. LOGIC API & CHECKSUM ==================

def calculate_checksum(json_body_string: str) -> str:
    hmac_obj = hmac.new(SECRET_KEY.encode('utf-8'), json_body_string.encode('utf-8'), hashlib.md5)
    return hmac_obj.hexdigest()

async def get_usdt_rates():
    try:
        headers = {"APIKEY": API_KEY} 
        r = requests.get(f"{API_BASE_URL}/info/usdt", headers=headers, timeout=10)
        data = r.json()
        if data.get("rc") == 0 or data.get("err_code") == 0:
            in_data = data.get("in", {})
            return in_data.get("price"), data.get("out", {}).get("price")
        return None, None
    except Exception as e:
        print(f"Lỗi lấy tỷ giá: {e}")
        return None, None

async def create_deposit_order(update: Update, context: ContextTypes.DEFAULT_TYPE, dep_type: str, amount_vnd: int = None, network: str = None, card_telco: str = None, card_serial: str = None, card_code: str = None):
    ref_id = f"tg_{update.effective_user.id}_{int(datetime.now().timestamp())}"

    body_dict = {
        "type": dep_type,
        "ref_id": ref_id,
        "amount": amount_vnd
    }
    if network: body_dict["network"] = network.upper()
    if card_telco: body_dict["card_telco"] = card_telco
    if card_serial: body_dict["card_serial"] = card_serial
    if card_code: body_dict["card_code"] = card_code
    if CALLBACK_URL: body_dict["callback"] = CALLBACK_URL

    json_body_str = json.dumps(body_dict, separators=(',', ':'), ensure_ascii=False)
    checksum = calculate_checksum(json_body_str)

    headers = {
        "APIKEY": API_KEY,
        "Checksum": checksum,
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(f"{API_BASE_URL}/deposit", data=json_body_str, headers=headers, timeout=20)
        try:
            data = r.json()
        except:
            await update.message.reply_text(f"❌ Lỗi Server: {r.text[:100]}")
            return

        if data.get("err_code") == 0:
            msg = f"✅ <b>LÊN ĐƠN THÀNH CÔNG</b>\nMã đơn: <code>{ref_id}</code>\n\n"

            if dep_type == "usdt":
                usdt_amt = data.get("usdt_amount", 0)
                price = data.get("usdt_price", 0)
                receiver = data.get("receiver", "N/A")
                expire = data.get("expire_at")
                expire_str = datetime.fromtimestamp(expire / 1000).strftime('%H:%M %d/%m') if expire else "N/A"
                
                msg += (
                    f"⚠️ <b>QUAN TRỌNG: Chuyển chính xác số lẻ bên dưới!</b>\n"
                    f"💰 Số lượng: <code>{usdt_amt}</code> (Chạm để copy)\n"
                    f"📍 Địa chỉ ví: <code>{receiver}</code> (Chạm để copy)\n"
                    f"🔗 Mạng lưới: <b>{network}</b>\n"
                    f"💵 Tỷ giá: {price:,} VND/USDT\n"
                    f"⏳ Hết hạn: {expire_str}"
                )
            else:
                if data.get("url"):
                    msg += f"🔗 <b><a href='{data.get('url')}'>BẤM VÀO ĐÂY ĐỂ THANH TOÁN</a></b>\n"
                if data.get("receiver"):
                    msg += f"📌 Tài khoản nhận: <code>{data.get('receiver')}</code>\n"
                if data.get("bank_type"):
                    msg += f"🏦 Ngân hàng: <b>{data.get('bank_type')}</b>\n"
                if data.get("amount"):
                     msg += f"💰 Số tiền: <b>{data.get('amount'):,} VND</b>"

            await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)

        else:
            err_code = data.get('err_code')
            err_msg = data.get('err_msg')
            err_user_msg = "Giao dịch thất bại"
            suggestion = "Vui lòng thử lại sau."

            if err_code == 70:
                err_user_msg = "⛔ KÊNH NÀY ĐANG BẢO TRÌ"
                suggestion = "Hệ thống đang hết tài khoản nhận tiền.\n👉 Vui lòng chọn <b>Nạp Ngân Hàng</b> hoặc <b>USDT</b>."
            elif err_code == 57:
                err_user_msg = "🔐 Lỗi bảo mật (Checksum)"
                suggestion = "Vui lòng báo Admin kiểm tra lại Secret Key."
            elif err_code == 1:
                err_user_msg = "⚠️ Số tiền không hợp lệ"
                suggestion = "Số tiền nạp quá nhỏ.\n👉 Vui lòng nạp tối thiểu <b>20.000 VND</b>."

            await update.message.reply_text(
                f"❌ <b>{err_user_msg}</b>\nCode: {err_code}\nLỗi: {err_msg}\n\n💡 <i>{suggestion}</i>", 
                parse_mode="HTML"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi kết nối: {str(e)}", parse_mode="HTML")

# ================== 4. GIAO DIỆN & HANDLER ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = STATE_NORMAL
    context.user_data['logged_ctv_code'] = None

    menu_keyboard = [
        [KeyboardButton("🍀 Giới Thiệu Group"), KeyboardButton("🎁 Nhận Giftcode")],
        [KeyboardButton("💰 Ưu Đãi & Khuyến Mãi"), KeyboardButton("💸 Nạp Tiền")],
        [KeyboardButton("🔍 Check Trạng Thái Lệnh"), KeyboardButton("🔒 Hướng Dẫn Nạp/Rút USDT")],
        [KeyboardButton("🕵️ Dịch Vụ Thanh Toán Ẩn Danh"), KeyboardButton("🤝 Đăng Ký CTV Ngay")],
        [KeyboardButton("👤 Tài Khoản Cá Nhân"), KeyboardButton("🔐 Đăng Nhập CTV (Báo Khách)")], 
    ]
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

    welcome_text = (
        "👋 <b>Xin chào Tân Thủ! Một ngày mới tuyệt vời để bắt đầu tại C168!!!</b>\n\n"
        "🎉 <b>THƯỞNG CHÀO MỪNG TÂN THỦ đã sẵn sàng.</b>\n"
        "Chỉ cần nạp đầu từ <b>100 điểm</b> liên tiếp là có thể đăng ký khuyến mãi với điểm thưởng vô cùng giá trị lên tới <b>12,776,000 VND</b>.\n\n"
        "🔥 <b>NẠP ĐẦU TẶNG 8.888K</b>\n"
        "🎫 <b>Mã Khuyến Mãi:</b> <code>ND01</code>\n\n"
        "🚀 <b>Đăng Ký Nhận Ngay 8.888 K – Chỉ Với 3 Bước Siêu Đơn Giản:</b>\n"
        "1️⃣ <b>B1:</b> Đăng ký tài khoản qua link chính thức duy nhất của bot:\n"
        "👉 <a href='https://c168c.cam/'><b>https://c168c.cam/</b></a>\n\n"
        "2️⃣ <b>B2:</b> Vào mục <b>Khuyến Mãi Tân Thủ</b>\n"
        "3️⃣ <b>B3:</b> Xác minh SĐT – Nhận thưởng tự động sau 1–15 phút nếu đủ điều kiện!\n\n"
        "💎 <i>Khuyến Mãi Hội Viên Mới Nạp Lần Đầu Thưởng 200%, Bạn Còn Chần Chờ Chi Nữa!!</i>\n\n"
        "🌟 <b>Nhanh Tay Tham Gia C168 Vô Vàn Sự Kiện Hấp Dẫn Được Cập Nhật Mỗi Ngày!</b>"
    )

    # --- ĐÃ SỬA: Gửi ẢNH thay vì VIDEO ---
    if os.path.exists(FILE_BANNER_START):
        try:
            with open(FILE_BANNER_START, 'rb') as f:
                await update.message.reply_photo(photo=f, caption=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
        except:
             await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_state = context.user_data.get('state', STATE_NORMAL)
    
    # === XỬ LÝ QUAY LẠI ===
    if text == BTN_BACK_MAIN or text == "🔙 Quay lại":
        await start(update, context)
        return

    # --- 1. ĐĂNG NHẬP CTV ---
    if text == "🔐 Đăng Nhập CTV (Báo Khách)":
        context.user_data['state'] = STATE_WAITING_ID
        kb_back = [[KeyboardButton(BTN_BACK_MAIN)]]
        await update.message.reply_text("👤 <b>Vui lòng nhập ID Cộng Tác Viên:</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(kb_back, resize_keyboard=True))
        return

    if user_state == STATE_WAITING_ID:
        accounts = load_ctv_accounts()
        if text in accounts:
            context.user_data['temp_id'] = text
            context.user_data['state'] = STATE_WAITING_PASS
            await update.message.reply_text(f"✅ ID hợp lệ: <b>{text}</b>\n🔑 <b>Vui lòng nhập Mật Khẩu:</b>", parse_mode="HTML")
        else: 
            await update.message.reply_text("❌ ID không tồn tại! Vui lòng nhập lại hoặc gõ /start để thoát.")
        return

    if user_state == STATE_WAITING_PASS:
        saved_id = context.user_data.get('temp_id')
        accounts = load_ctv_accounts()
        if text == accounts.get(saved_id):
            context.user_data['state'] = STATE_LOGGED_IN; context.user_data['logged_ctv_code'] = saved_id
            kb = [[KeyboardButton("📊 Xem Thống Kê"), KeyboardButton("📞 Lấy File Đối Soát")], [KeyboardButton("❌ Đăng Xuất")]]
            await update.message.reply_text(f"🎉 <b>ĐĂNG NHẬP THÀNH CÔNG!</b>\nXin chào CTV: <b>{saved_id}</b>\n\n📝 <b>CÚ PHÁP BÁO KHÁCH:</b>\n<code>/F TênKhách - MãCTV - SốTiền</code>\n🔍 Check trạng thái: <code>/check ref_id</code>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        else: await update.message.reply_text("❌ Mật khẩu sai! Vui lòng nhập lại.")
        return

    if user_state == STATE_LOGGED_IN:
        current_ctv = context.user_data.get('logged_ctv_code')
        if text == "❌ Đăng Xuất": await start(update, context); return
        elif text == "📊 Xem Thống Kê":
            sl, tien = dem_so_khach(current_ctv)
            await update.message.reply_text(f"📊 <b>THỐNG KÊ CỦA BẠN ({current_ctv})</b>\n▬▬▬▬▬▬▬▬▬▬▬▬▬\n👥 Tổng khách đã báo: <b>{sl}</b>\n💵 Tổng tiền nạp: <b>{tien:,} k</b>", parse_mode="HTML")
            return
        elif text == "📞 Lấy File Đối Soát": await update.message.reply_text("📞 <b>LIÊN HỆ ADMIN ĐỐI SOÁT</b>\n\n👉 Telegram: <a href='https://t.me/Bez_api'><b>@Bez_api</b></a>", parse_mode="HTML", disable_web_page_preview=True); return
        if not text.startswith('/'): await update.message.reply_text("💡 Dùng menu bên dưới hoặc gõ lệnh <code>/F ...</code> để báo khách.", parse_mode="HTML"); return

    # --- 2. NẠP TIỀN ---
    if text == "💸 Nạp Tiền":
        kb = [
            [KeyboardButton("🪙 Nạp USDT"), KeyboardButton("🏦 Nạp Ngân Hàng")],
            [KeyboardButton("📱 Nạp Momo"), KeyboardButton("🟢 Nạp ZaloPay")],
            [KeyboardButton("💳 Nạp ViettelPay"), KeyboardButton("🎟 Nạp Thẻ Cào")],
            [KeyboardButton(BTN_BACK_MAIN)]
        ]
        in_price, out_price = await get_usdt_rates()
        rate_text = f"\n💹 Tỷ giá USDT hiện tại:\nNạp: 1 USDT ≈ {in_price:,} VND\nRút: 1 USDT ≈ {out_price:,} VND" if in_price else ""
        await update.message.reply_text(
            f"💰 <b>Chọn phương thức nạp tiền</b>{rate_text}",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
            parse_mode="HTML"
        )
        return

    deposit_types = {
        "🪙 Nạp USDT": "usdt", "🏦 Nạp Ngân Hàng": "bank",
        "📱 Nạp Momo": "momo", "🟢 Nạp ZaloPay": "zalo",
        "💳 Nạp ViettelPay": "viettelpay", "🎟 Nạp Thẻ Cào": "card"
    }

    if text in deposit_types:
        dep_type = deposit_types[text]
        context.user_data['deposit_type'] = dep_type
        context.user_data['state'] = STATE_WAITING_DEPOSIT_AMOUNT
        prompt = "💰 Nhập số tiền nạp (VND):" if dep_type != "card" else "💰 Nhập mệnh giá thẻ (VND):"
        kb_back = [[KeyboardButton(BTN_BACK_MAIN)]]
        await update.message.reply_text(prompt, reply_markup=ReplyKeyboardMarkup(kb_back, resize_keyboard=True))
        return

    if user_state == STATE_WAITING_DEPOSIT_AMOUNT:
        try:
            amount_str = text.replace(",", "").replace(".", "").replace("k", "000").strip()
            amount = int(amount_str)
            if amount < 10000:
                await update.message.reply_text("⚠️ Số tiền tối thiểu là 10.000 VND!")
                return

            dep_type = context.user_data.get('deposit_type')
            context.user_data['deposit_amount'] = amount

            if dep_type == "usdt":
                context.user_data['state'] = STATE_WAITING_NETWORK
                kb_net = [[KeyboardButton("BSC"), KeyboardButton("TRON")], [KeyboardButton(BTN_BACK_MAIN)]]
                await update.message.reply_text("🔗 Chọn network:", reply_markup=ReplyKeyboardMarkup(kb_net, resize_keyboard=True))
            elif dep_type == "card":
                context.user_data['state'] = STATE_WAITING_CARD_TELCO
                kb_telco = [[KeyboardButton("Viettel"), KeyboardButton("Mobifone"), KeyboardButton("Vinaphone")], [KeyboardButton(BTN_BACK_MAIN)]]
                await update.message.reply_text("🎟 Chọn nhà mạng thẻ:", reply_markup=ReplyKeyboardMarkup(kb_telco, resize_keyboard=True))
            else:
                await create_deposit_order(update, context, dep_type, amount)
                context.user_data['state'] = STATE_NORMAL
        except ValueError:
            await update.message.reply_text("⚠️ Vui lòng nhập số tiền hợp lệ (chỉ số)!")
        return

    if user_state == STATE_WAITING_NETWORK:
        network = text.strip().upper()
        if network not in ["BSC", "TRON"]:
            await update.message.reply_text("⚠️ Chỉ hỗ trợ BSC hoặc TRON!")
            return
        amount = context.user_data.get('deposit_amount')
        await create_deposit_order(update, context, "usdt", amount, network=network)
        context.user_data['state'] = STATE_NORMAL
        return

    if user_state == STATE_WAITING_CARD_TELCO:
        telco_map = {"Viettel": "viettel", "Mobifone": "mobifone", "Vinaphone": "vinaphone"}
        if text not in telco_map:
            await update.message.reply_text("⚠️ Vui lòng chọn nhà mạng hợp lệ!")
            return
        context.user_data['card_telco'] = telco_map[text]
        context.user_data['state'] = STATE_WAITING_CARD_SERIAL
        kb_back = [[KeyboardButton(BTN_BACK_MAIN)]]
        await update.message.reply_text("🔢 Nhập số serial thẻ:", reply_markup=ReplyKeyboardMarkup(kb_back, resize_keyboard=True))
        return

    if user_state == STATE_WAITING_CARD_SERIAL:
        context.user_data['card_serial'] = text.strip()
        context.user_data['state'] = STATE_WAITING_CARD_CODE
        kb_back = [[KeyboardButton(BTN_BACK_MAIN)]]
        await update.message.reply_text("🔑 Nhập mã thẻ (PIN/code):", reply_markup=ReplyKeyboardMarkup(kb_back, resize_keyboard=True))
        return

    if user_state == STATE_WAITING_CARD_CODE:
        card_code = text.strip()
        amount = context.user_data.get('deposit_amount')
        telco = context.user_data.get('card_telco')
        await create_deposit_order(update, context, "card", amount, card_telco=telco, card_serial=context.user_data.get('card_serial'), card_code=card_code)
        context.user_data['state'] = STATE_NORMAL
        return

    if text == "🔍 Check Trạng Thái Lệnh":
        await update.message.reply_text("Cách dùng: /check <ref_id>\nVí dụ: /check tg_6340716909_1770012000\n\nRef ID được gửi khi tạo lệnh nạp.")
        return

    # --- 3. NỘI DUNG INFO (FULL OPTION) ---
    msg_content = ""
    photo_path = None

    if text == "🍀 Giới Thiệu Group":
        msg_content = (
            "🌿 <b>CỘNG ĐỒNG XÔI MẶN - GIAO LƯU & NHẬN QUÀ</b> 🌿\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "💎 <b>Quyền lợi khi tham gia:</b>\n"
            "✅ Săn Giftcode độc quyền hằng ngày\n"
            "✅ Cập nhật kèo thơm & khuyến mãi mới nhất\n"
            "✅ Được Admin hỗ trợ ưu tiên 1:1\n"
            "✅ Giao lưu kinh nghiệm cùng các dân chơi\n\n"
            "🚀 <b>THAM GIA NGAY TẠI:</b>\n"
            "👉 <a href='https://t.me/congdongxoiman'><b>t.me/congdongxoiman</b></a>\n\n"
            "<i>⚠️ Lưu ý: Môi trường văn minh, vui lòng không spam!</i>"
        )
        photo_path = FILE_BANNER_INTRO

    elif text == "🎁 Nhận Giftcode":
        msg_content = (
            "🎁 <b>KHO GIFTCODE & SỰ KIỆN</b> 🎁\n\n"
            "🔔 Mã thưởng được phát <b>MỖI NGÀY</b> tại Group chính thức.\n\n"
            "👉 <b>Vào lấy code ngay:</b> \n"
            "🔗 <a href='https://hupcode.xo.je'>https://hupcode.xo.je</a>\n\n"
            "<i>💡 Mẹo: Bật thông báo Group để không bỏ lỡ code xịn nhé!</i>"
        )
    elif text == "💰 Ưu Đãi & Khuyến Mãi":
        msg_content = (
            "🧧 <b>SIÊU BÃO KHUYẾN MÃI TẾT 2026</b> 🧧\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "🔥 <b>DÀNH CHO TÂN THỦ:</b>\n"
            "• 💎 Thưởng nạp đầu lên tới <b>150%</b>\n"
            "• 🎰 Tặng Free Spin trải nghiệm\n\n"
            "🔥 <b>ƯU ĐÃI HẰNG NGÀY:</b>\n"
            "• 🐟 <b>Bắn Cá / Slot:</b> Hoàn trả <b>1.2%</b> không giới hạn\n"
            "• 🎲 <b>Casino:</b> Thưởng nạp lại <b>50%</b> + Quà VIP\n"
            "• ⚽ <b>Thể Thao / Đá Gà:</b> Bảo hiểm thua cược\n\n"
            "💰 <b>ĐẶC BIỆT:</b> Làm CTV kiếm thu nhập thụ động trọn đời!\n\n"
            "👉 <i>Chi tiết xem tại Group:</i> <a href='https://t.me/congdongxoiman'>t.me/congdongxoiman</a>"
        )
    elif text == "🔒 Hướng Dẫn Nạp/Rút USDT":
        msg_content = (
            "📥 <b>HƯỚNG DẪN NẠP USDT BẰNG BINANCE</b>\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "1️⃣ <b>Bước 1:</b> Ở giao diện chính của <b>BINANCE</b> chọn mục <b>Tài sản</b> ➝ chọn <b>Gửi</b>.\n\n"
            "2️⃣ <b>Bước 2:</b> Chọn <b>Rút tiền trên chuỗi</b>.\n\n"
            "3️⃣ <b>Bước 3:</b> Chọn coin <b>USDT</b>.\n\n"
            "4️⃣ <b>Bước 4:</b> Nhập thông tin:\n"
            "   • <b>Địa chỉ ví:</b> (Lấy trên web/app game)\n"
            "   • <b>Mạng lưới:</b> TRC20 hoặc ERC20 (theo thông tin ví nhận)\n"
            "   • <b>Số tiền:</b> Nhập số muốn nạp ➝ Chọn <b>Rút</b>.\n\n"
            "5️⃣ <b>Bước 5:</b> Kiểm tra lại thông tin, ấn <b>Xác nhận</b> và xác minh 2 lớp để hoàn thành.\n\n"
            "🔒 <i>Hệ thống tự động duyệt sau 3-5 phút.</i>\n\n"
            "👉 <i>Inbox ngay Admin <a href='https://t.me/Bez_api'><b>@Bez_api</b></a> nếu cần hỗ trợ trung gian!</i>"
        )
        photo_path = FILE_ANH_NAP

    elif text == "🕵️ Dịch Vụ Thanh Toán Ẩn Danh":
        msg_content = (
            "🛡️ <b>DỊCH VỤ THANH TOÁN ẨN DANH & TIỀN MẶT</b> 🛡️\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "💡 <i>Quý khách thấy bất tiện khi nạp rút bằng tiền ảo USDT? Quý khách muốn bảo mật danh tính tuyệt đối?</i>\n\n"
            "🚀 <b>CHÚNG TÔI CUNG CẤP GIẢI PHÁP:</b>\n"
            "✅ <b>Bảo mật tuyệt đối:</b> Giao dịch qua các kênh thanh toán ẩn danh, không lộ danh tính.\n"
            "✅ <b>Hỗ trợ tiền mặt:</b> Có thể nhận/gửi tiền mặt trực tiếp tại các điểm giao dịch.\n"
            "✅ <b>Chi phí siêu rẻ:</b> Phí dịch vụ chỉ <b>0.1%</b> (cho 1 chiều Nạp hoặc Rút).\n\n"
            "👉 <b>LIÊN HỆ NGAY ADMIN ĐỂ ĐƯỢC HỖ TRỢ:</b>\n"
            "💬 Telegram: <a href='https://t.me/Bez_api'><b>@Bez_api</b></a>"
        )

    elif text == "🤝 Đăng Ký CTV Ngay":
        msg_content = (
            "🤝 <b>HỢP TÁC NHƯ Ý - KIẾM TIỀN TỶ </b> 🤝\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "💼 <b>CÔNG VIỆC:</b>\n"
            "• Chia sẻ link giới thiệu game tới bạn bè/cộng đồng.\n"
            "• Không cần vốn - Không cần CSKH.\n\n"
            "💰 <b>HOA HỒNG KHỦNG:</b>\n"
            "💵 <b>100.000 VNĐ</b> / 1 Khách nạp > 1 triệu.\n"
            "📉 <i>(Nếu khách chơi nhỏ/spam: 20k/khách)</i>\n\n"
            "📝 <b>QUY TRÌNH HỢP TÁC:</b>\n"
            "1️⃣ Liên hệ Admin nhận mã & link riêng.\n"
            "2️⃣ Được add vào nhóm làm việc riêng.\n"
            "3️⃣ <b>BÁO KHÁCH:</b> Khi có khách nạp, phải báo vào nhóm ngay để tính lương.\n\n"
            "🚀 <b>ĐĂNG KÝ NGAY:</b>\n"
            "👉 Telegram: <a href='https://t.me/Bez_api'><b>@Bez_api</b></a>"
        )
    elif text == "👤 Tài Khoản Cá Nhân":
        msg_content = (
            f"👤 <b>HỒ SƠ NGƯỜI DÙNG</b>\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"🆔 <b>ID Telegram:</b> <code>{update.effective_user.id}</code>\n"
            f"🏷 <b>Username:</b> @{update.effective_user.username or 'Không có'}\n"
            f"💼 <b>Trạng thái:</b> Thành viên\n"
            f"💰 <b>Số dư ví:</b> 0đ <i>(Đang đồng bộ...)</i>\n\n"
            "🛠 <i>Cần hỗ trợ tài khoản? Nhấn nút Báo Khách bên dưới!</i>"
        )
    elif text == "🔙 Quay lại":
        await start(update, context)
        return
    else:
        msg_content = "🤔 <b>Vui lòng chọn các nút bấm có sẵn trên menu nhé!</b> 👇"

    if photo_path and os.path.exists(photo_path):
        with open(photo_path, 'rb') as f:
            await context.bot.send_photo(update.effective_chat.id, photo=f, caption=msg_content, parse_mode="HTML")
    else:
        await context.bot.send_message(update.effective_chat.id, text=msg_content, parse_mode="HTML", disable_web_page_preview=True)

# ================== 5. ADMIN & MAIN ==================

async def command_bao_khach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state', STATE_NORMAL) != STATE_LOGGED_IN:
        await update.message.reply_text("⚠️ <b>LỖI:</b> Bạn phải Đăng nhập CTV trước!", parse_mode="HTML")
        return
    try:
        parts = update.message.text[3:].strip().split('-')
        if len(parts) < 3: raise ValueError
        ten, ma, tien = parts[0].strip(), parts[1].strip(), parts[2].strip()
        current_ctv = context.user_data.get('logged_ctv_code')
        if ma.lower() != current_ctv.lower():
             await update.message.reply_text(f"⚠️ Sai mã CTV! Bạn đang đăng nhập là <b>{current_ctv}</b>.", parse_mode="HTML")
             return
        luu_bao_khach(update.effective_user.id, ten, ma, tien)
        await update.message.reply_text(f"✅ <b>BÁO KHÁCH THÀNH CÔNG!</b>\n👤 Khách: <b>{ten}</b>\n💰 Nạp: <b>{tien}</b>\n📂 <i>Đã lưu hệ thống.</i>", parse_mode="HTML")
    except: await update.message.reply_text("⚠️ <b>SAI CÚ PHÁP!</b>\nVD: <code>/F Tuan - CTV01 - 500k</code>", parse_mode="HTML")

async def admin_them_ctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("⚠️ VD: /themctv tuananh 9999", parse_mode="HTML")
            return
        new_user, new_pass = args[0].strip(), args[1].strip()
        accounts = load_ctv_accounts()
        accounts[new_user] = new_pass
        save_ctv_accounts(accounts)
        await update.message.reply_text(f"✅ Đã thêm CTV: <b>{new_user}</b>", parse_mode="HTML")
    except: pass

async def admin_xoa_ctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        del_user = context.args[0].strip()
        accounts = load_ctv_accounts()
        if del_user in accounts:
            del accounts[del_user]
            save_ctv_accounts(accounts)
            await update.message.reply_text(f"🗑️ Đã xóa CTV: <b>{del_user}</b>", parse_mode="HTML")
    except: pass

async def admin_quan_ly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    accounts = load_ctv_accounts()
    msg = f"👑 <b>QUẢN TRỊ ADMIN</b>\n👥 Tổng CTV: {len(accounts)}\n\n"
    total = 0
    for ctv in accounts:
        sl, tien = dem_so_khach(ctv)
        total += tien
        msg += f"👤 {ctv}: {sl} khách | {tien:,}\n"
    msg += f"\n💰 <b>TỔNG DOANH THU: {total:,}</b>"
    await update.message.reply_text(msg, parse_mode="HTML")

async def admin_xuat_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    if os.path.exists(FILE_DATA_KHACH):
        with open(FILE_DATA_KHACH, 'rb') as f:
            await update.message.reply_document(f, filename="Doanh_Thu.csv")

async def command_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Cách dùng: /check <ref_id>")
        return
    ref_id = context.args[0].strip()
    headers = {"APIKEY": API_KEY}
    try:
        r = requests.get(f"{API_BASE_URL}/deposit?ref_id={ref_id}", headers=headers, timeout=10)
        data = r.json()
        if data.get("ref_id"):
            msg = f"🔍 <b>KẾT QUẢ TRA CỨU:</b>\nID: {ref_id}\nTrạng thái: <b>{data.get('status', 'Unknown').upper()}</b>\nSố tiền: {data.get('amount', 0):,} VND"
        else:
            msg = "❌ Không tìm thấy đơn hàng."
        await update.message.reply_text(msg, parse_mode="HTML")
    except: await update.message.reply_text("❌ Lỗi kiểm tra.")

async def admin_xem_chi_tiet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        if len(context.args) < 1:
            await update.message.reply_text("⚠️ Cách dùng: /chitiet <mã_ctv>\nVD: /chitiet ctv01", parse_mode="HTML")
            return
        target_ctv = context.args[0].strip().lower()
        if not os.path.exists(FILE_DATA_KHACH):
            await update.message.reply_text("📭 Chưa có dữ liệu.", parse_mode="HTML")
            return
        
        found_rows = []
        tong_tien_check = 0
        with open(FILE_DATA_KHACH, mode='r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            next(reader, None)
            for row in reader:
                if len(row) >= 5 and row[3].strip().lower() == target_ctv:
                    short_time = row[0][11:16]
                    found_rows.append(f"🕒 <code>{short_time}</code> | 👤 <b>{row[2]}</b> | 💰 {row[4]}")
                    try: tong_tien_check += int(''.join(filter(str.isdigit, row[4])))
                    except: pass
        
        if not found_rows: await update.message.reply_text(f"❌ CTV <b>{target_ctv}</b> chưa có khách nào.", parse_mode="HTML")
        else:
            msg = f"📄 <b>LỊCH SỬ GIAO DỊCH: {target_ctv.upper()}</b>\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n" + "\n".join(found_rows[-15:]) + f"\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n💵 <b>TỔNG CỘNG: {tong_tien_check:,}</b>"
            await update.message.reply_text(msg, parse_mode="HTML")
    except: pass

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await context.bot.send_message(update.effective_chat.id, "🧹 Đang dọn dẹp...", parse_mode="HTML")
    for i in range(1, 21): 
        try: await context.bot.delete_message(update.effective_chat.id, update.message.message_id - i)
        except: pass
    try: await context.bot.delete_message(update.effective_chat.id, msg.message_id)
    except: pass

def main():
    keep_alive()
    print("🚀 Bot đang khởi động...")
    app = ApplicationBuilder().token(TOKEN_BOT).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler(['xoa', 'cls'], clear_chat))
    app.add_handler(CommandHandler(['F', 'f'], command_bao_khach))
    app.add_handler(CommandHandler('check', command_check))
    app.add_handler(CommandHandler(['admin', 'quanly'], admin_quan_ly))
    app.add_handler(CommandHandler('themctv', admin_them_ctv))
    app.add_handler(CommandHandler('xoactv', admin_xoa_ctv))
    app.add_handler(CommandHandler('chitiet', admin_xem_chi_tiet))
    app.add_handler(CommandHandler(['xuatfile', 'export'], admin_xuat_file))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
