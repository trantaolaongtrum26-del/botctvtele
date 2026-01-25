import logging
import os
import csv
import json
import asyncio
from datetime import datetime
from keep_alive import keep_alive
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ================== CẤU HÌNH HỆ THỐNG ==================
TOKEN_BOT = '8269134409:AAFCc7tB1kdc0et_4pnH52SoG_RyCu-UX0w'
ID_ADMIN_CHINH = 8457924201  # ID Admin của bạn

# Tên các file dữ liệu
FILE_ANH_NAP = "huong-dan-nap-usdt-binance.jpg"
FILE_ANH_RUT = "huong-dan-nap-usdt.jpg"
FILE_BANNER = "banner.jpg"
FILE_DATA_KHACH = "danh_sach_bao_khach.csv"
FILE_TK_CTV = "taikhoan_ctv.json"

# Tài khoản mặc định nếu file chưa được tạo
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

# Trạng thái hội thoại
STATE_NORMAL = 0
STATE_WAITING_ID = 1
STATE_WAITING_PASS = 2
STATE_LOGGED_IN = 3

# ================== CÁC HÀM XỬ LÝ DỮ LIỆU ==================
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

# ================== CÁC CHỨC NĂNG ADMIN ==================
async def admin_them_ctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("⚠️ Cách dùng: /themctv <tên> <pass>\nVD: /themctv tuananh 9999", parse_mode="HTML")
            return
        new_user = args[0].strip()
        new_pass = args[1].strip()
        accounts = load_ctv_accounts()
        if new_user in accounts:
            await update.message.reply_text(f"⚠️ CTV <b>{new_user}</b> đã tồn tại!", parse_mode="HTML")
            return
        accounts[new_user] = new_pass
        save_ctv_accounts(accounts)
        await update.message.reply_text(f"✅ Đã thêm CTV: <b>{new_user}</b> - Mật khẩu: <b>{new_pass}</b>", parse_mode="HTML")
    except: await update.message.reply_text("❌ Lỗi hệ thống.")

async def admin_xoa_ctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        args = context.args
        if len(args) < 1:
            await update.message.reply_text("⚠️ Cách dùng: /xoactv <tên>\nVD: /xoactv tuananh", parse_mode="HTML")
            return
        del_user = args[0].strip()
        accounts = load_ctv_accounts()
        if del_user not in accounts:
            await update.message.reply_text(f"⚠️ Không tìm thấy CTV: <b>{del_user}</b>", parse_mode="HTML")
            return
        del accounts[del_user]
        save_ctv_accounts(accounts)
        await update.message.reply_text(f"🗑️ Đã xóa CTV: <b>{del_user}</b>", parse_mode="HTML")
    except: await update.message.reply_text("❌ Lỗi hệ thống.")

async def admin_quan_ly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: 
        await update.message.reply_text("⛔ <b>Bạn không có quyền truy cập Admin!</b>", parse_mode="HTML")
        return

    accounts = load_ctv_accounts()
    msg_report = f"👑 <b>BẢNG QUẢN TRỊ ADMIN</b> 👑\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n👥 Tổng số CTV: <b>{len(accounts)}</b> người\n\n📊 <b>CHI TIẾT HIỆU QUẢ:</b>\n"
    total_all_money = 0
    for ma_ctv in accounts:
        sl, tien = dem_so_khach(ma_ctv)
        total_all_money += tien
        icon = "🟢" if sl > 0 else "⚪"
        msg_report += f"{icon} <b>{ma_ctv}:</b> {sl} khách | {tien:,} k\n"

    msg_report += f"\n💰 <b>TỔNG DOANH THU HỆ THỐNG: {total_all_money:,} k</b>\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n➕ Thêm CTV: <code>/themctv user pass</code>\n➖ Xóa CTV: <code>/xoactv user</code>\n👀 Chi tiết: <code>/chitiet user</code>\n📥 Xuất File: <code>/xuatfile</code>"
    await update.message.reply_text(msg_report, parse_mode="HTML")

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

async def admin_xuat_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    if not os.path.exists(FILE_DATA_KHACH):
        await update.message.reply_text("📭 Chưa có dữ liệu nào để xuất.")
        return
    await update.message.reply_text("⏳ Đang gửi file dữ liệu...")
    try:
        with open(FILE_DATA_KHACH, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"Data_Bao_Khach_{datetime.now().strftime('%d-%m-%Y')}.csv",
                caption="📊 File thống kê doanh thu chi tiết."
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi gửi file: {e}")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    msg = await context.bot.send_message(update.effective_chat.id, "🧹 Đang dọn dẹp 20 tin nhắn gần nhất...", parse_mode="HTML")
    for i in range(1, 21): 
        try: await context.bot.delete_message(update.effective_chat.id, update.message.message_id - i)
        except: pass
    await asyncio.sleep(1)
    try: await context.bot.delete_message(update.effective_chat.id, msg.message_id)
    except: pass

# ================== MAIN START & MENU ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = STATE_NORMAL
    context.user_data['logged_ctv_code'] = None

    menu_keyboard = [
        [KeyboardButton("🍀 Giới Thiệu Group"), KeyboardButton("🎁 Nhận Giftcode")],
        [KeyboardButton("💰 Ưu Đãi & Khuyến Mãi"), KeyboardButton("🔒 Nạp/Rút USDT An Toàn")],
        [KeyboardButton("🕵️ Dịch Vụ Thanh Toán Ẩn Danh")], 
        [KeyboardButton("🤝 Đăng Ký CTV Ngay"), KeyboardButton("👤 Tài Khoản Cá Nhân")],
        [KeyboardButton("🔐 Đăng Nhập CTV (Báo Khách)")], 
    ]
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

    # NỘI DUNG CHÀO MỪNG ĐẦY ĐỦ
    welcome_text = (
        "👋 <b>Xin chào Tân Thủ! Một ngày mới tuyệt vời để bắt đầu tại 78win!!!</b>\n\n"
        "🎉 <b>THƯỞNG CHÀO MỪNG TÂN THỦ đã sẵn sàng.</b>\n"
        "Chỉ cần nạp đầu từ <b>100 điểm</b> liên tiếp là có thể đăng ký khuyến mãi với điểm thưởng vô cùng giá trị lên tới <b>12,776,000 VND</b>.\n\n"
        "🔥 <b>NẠP ĐẦU TẶNG 8.888K</b>\n"
        "🎫 <b>Mã Khuyến Mãi:</b> <code>ND01</code>\n\n"
        "🚀 <b>Đăng Ký Nhận Ngay 8.888 K – Chỉ Với 3 Bước Siêu Đơn Giản:</b>\n"
        "1️⃣ <b>B1:</b> Đăng ký tài khoản qua link chính thức duy nhất của bot:\n"
        "👉 <a href='https://78max.top'><b>https://78max.top</b></a>\n\n"
        "2️⃣ <b>B2:</b> Vào mục <b>Khuyến Mãi Tân Thủ</b>\n"
        "3️⃣ <b>B3:</b> Xác minh SĐT – Nhận thưởng tự động sau 1–15 phút nếu đủ điều kiện!\n\n"
        "💎 <i>Khuyến Mãi Hội Viên Mới Nạp Lần Đầu Thưởng 200%, Bạn Còn Chần Chờ Chi Nữa!!</i>\n\n"
        "🌟 <b>Nhanh Tay Tham Gia 78WIN Vô Vàn Sự Kiện Hấp Dẫn Được Cập Nhật Mỗi Ngày!</b>"
    )

    if os.path.exists(FILE_BANNER):
        with open(FILE_BANNER, 'rb') as f:
            await update.message.reply_photo(photo=f, caption=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)

async def command_bao_khach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state', STATE_NORMAL) != STATE_LOGGED_IN:
        await update.message.reply_text("⚠️ <b>LỖI:</b> Bạn phải Đăng nhập CTV trước mới dùng được lệnh này!", parse_mode="HTML")
        return
    try:
        parts = update.message.text[3:].strip().split('-')
        if len(parts) < 3: raise ValueError
        ten, ma, tien = parts[0].strip(), parts[1].strip(), parts[2].strip()
        current_ctv = context.user_data.get('logged_ctv_code')
        if ma.lower() != current_ctv.lower():
             await update.message.reply_text(f"⚠️ Bạn đang đăng nhập acc <b>{current_ctv}</b> nhưng lại báo cho <b>{ma}</b>. Vui lòng kiểm tra lại!", parse_mode="HTML")
             return
        luu_bao_khach(update.effective_user.id, ten, ma, tien)
        await update.message.reply_text(f"✅ <b>BÁO KHÁCH THÀNH CÔNG!</b>\n▬▬▬▬▬▬▬▬▬▬▬▬▬\n👤 Khách: <b>{ten}</b>\n🆔 Mã CTV: <b>{ma}</b>\n💰 Nạp: <b>{tien}</b>\n\n📂 <i>Đã lưu vào hệ thống đối soát.</i>", parse_mode="HTML")
    except: await update.message.reply_text("⚠️ <b>SAI CÚ PHÁP!</b>\n\nVui lòng nhập đúng mẫu:\n<code>/F TênKhách - MãCTV - SốTiền</code>\n\nVí dụ: <code>/F TuanAnh - CTV01 - 500k</code>", parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_state = context.user_data.get('state', STATE_NORMAL)
    
    # --- LOGIC ĐĂNG NHẬP ---
    if text == "🔐 Đăng Nhập CTV (Báo Khách)":
        context.user_data['state'] = STATE_WAITING_ID
        await update.message.reply_text("👤 <b>Vui lòng nhập ID Cộng Tác Viên:</b>", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return

    if user_state == STATE_WAITING_ID:
        accounts = load_ctv_accounts()
        if text in accounts:
            context.user_data['temp_id'] = text; context.user_data['state'] = STATE_WAITING_PASS
            await update.message.reply_text(f"✅ ID hợp lệ: <b>{text}</b>\n🔑 <b>Vui lòng nhập Mật Khẩu:</b>", parse_mode="HTML")
        else: await update.message.reply_text("❌ ID không tồn tại! Vui lòng nhập lại hoặc gõ /start để thoát.")
        return

    if user_state == STATE_WAITING_PASS:
        saved_id = context.user_data.get('temp_id')
        accounts = load_ctv_accounts()
        if text == accounts.get(saved_id):
            context.user_data['state'] = STATE_LOGGED_IN; context.user_data['logged_ctv_code'] = saved_id
            kb = [[KeyboardButton("📊 Xem Thống Kê"), KeyboardButton("📞 Lấy File Đối Soát")], [KeyboardButton("❌ Đăng Xuất")]]
            await update.message.reply_text(f"🎉 <b>ĐĂNG NHẬP THÀNH CÔNG!</b>\nXin chào CTV: <b>{saved_id}</b>\n\n📝 <b>CÚ PHÁP BÁO KHÁCH:</b>\n<code>/F TênKhách - MãCTV - SốTiền</code>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        else: await update.message.reply_text("❌ Mật khẩu sai! Vui lòng nhập lại.")
        return

    # --- MENU CTV ---
    if user_state == STATE_LOGGED_IN:
        current_ctv = context.user_data.get('logged_ctv_code')
        if text == "❌ Đăng Xuất": await start(update, context); return
        elif text == "📊 Xem Thống Kê":
            sl, tien = dem_so_khach(current_ctv)
            await update.message.reply_text(f"📊 <b>THỐNG KÊ CỦA BẠN ({current_ctv})</b>\n▬▬▬▬▬▬▬▬▬▬▬▬▬\n👥 Tổng khách đã báo: <b>{sl}</b>\n💵 Tổng tiền nạp: <b>{tien:,} k</b>", parse_mode="HTML")
            return
        elif text == "📞 Lấy File Đối Soát": await update.message.reply_text("📞 <b>LIÊN HỆ ADMIN ĐỐI SOÁT</b>\n\n👉 Telegram: <a href='https://t.me/crown66666'><b>@crown66666</b></a>", parse_mode="HTML", disable_web_page_preview=True); return
        if not text.startswith('/'): await update.message.reply_text("💡 Dùng menu bên dưới hoặc gõ lệnh <code>/F ...</code> để báo khách.", parse_mode="HTML"); return

    # --- MENU NGƯỜI DÙNG THƯỜNG (FULL NỘI DUNG) ---
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
    elif text == "🔒 Nạp/Rút USDT An Toàn":
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
            "👉 <i>Inbox ngay Admin <a href='https://t.me/crown66666'><b>@crown66666</b></a> nếu cần hỗ trợ trung gian!</i>"
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
            "💬 Telegram: <a href='https://t.me/crown66666'><b>@crown66666</b></a>"
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
            "👉 Telegram: <a href='https://t.me/crown66666'><b>@crown66666</b></a>"
        )
    elif text == "👤 Tài Khoản Cá Nhân":
        msg_content = (
            f"👤 <b>HỒ SƠ NGƯỜI DÙNG</b>\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"🆔 <b>ID Telegram:</b> <code>{update.effective_user.id}</code>\n"
            f"🏷 <b>Username:</b> @{update.effective_user.username or 'Không có'}\n"
            f"💼 <b>Trạng thái:</b> Thành viên\n"
            "💰 <b>Số dư ví:</b> 0đ <i>(Đang đồng bộ...)</i>\n\n"
            "🛠 <i>Cần hỗ trợ tài khoản? Nhấn nút Báo Khách bên dưới!</i>"
        )
    elif text == "📢 Báo Khách / Hỗ Trợ":
        msg_content = (
            "✅ <b>ĐÃ GỬI YÊU CẦU HỖ TRỢ!</b>\n\n"
            "Hệ thống đã ghi nhận yêu cầu của bạn.\n"
            "⏳ Admin sẽ phản hồi trong vòng <b>1-5 phút</b>.\n\n"
            "🔔 <i>Vui lòng chú ý tin nhắn chờ nhé!</i>"
        )
    else:
        msg_content = "🤔 <b>Vui lòng chọn các nút bấm có sẵn trên menu nhé!</b> 👇"

    if photo_path and os.path.exists(photo_path):
        with open(photo_path, 'rb') as f:
            await context.bot.send_photo(update.effective_chat.id, photo=f, caption=msg_content, parse_mode="HTML")
    else:
        await context.bot.send_message(update.effective_chat.id, text=msg_content, parse_mode="HTML", disable_web_page_preview=True)

def main():
    keep_alive()
    print("🚀 Bot đang khởi động...")
    app = ApplicationBuilder().token(TOKEN_BOT).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler(['xoa', 'cls'], clear_chat))
    app.add_handler(CommandHandler(['F', 'f'], command_bao_khach))
    app.add_handler(CommandHandler(['admin', 'quanly'], admin_quan_ly))
    app.add_handler(CommandHandler('themctv', admin_them_ctv))
    app.add_handler(CommandHandler('xoactv', admin_xoa_ctv))
    app.add_handler(CommandHandler('chitiet', admin_xem_chi_tiet))
    app.add_handler(CommandHandler(['xuatfile', 'export'], admin_xuat_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()



