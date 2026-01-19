import logging
import os
import csv
import asyncio
from datetime import datetime
from keep_alive import keep_alive
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ================== CẤU HÌNH & TÊN FILE ==================
TOKEN_BOT = '8269134409:AAFCc7tB1kdc0et_4pnH52SoG_RyCu-UX0w'

# Tên file ảnh (Phải có trong thư mục)
FILE_ANH_NAP = "huong-dan-nap-usdt-binance.jpg"
FILE_ANH_RUT = "huong-dan-nap-usdt.jpg"
FILE_BANNER = "banner.jpg"
FILE_DATA_KHACH = "danh_sach_bao_khach.csv" # File lưu dữ liệu báo khách

# --- DANH SÁCH TÀI KHOẢN CTV (ID : Mật Khẩu) ---
# Bạn có thể thêm nhiều tài khoản vào đây
CTV_ACCOUNTS = {
    "ctv01": "123456",
    "admin": "admin888",
    "huydeptrai": "888888"
}

# ================== LOGGING ==================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== TRẠNG THÁI HỘI THOẠI ==================
STATE_NORMAL = 0
STATE_WAITING_ID = 1
STATE_WAITING_PASS = 2
STATE_LOGGED_IN = 3

# ================== HÀM HỖ TRỢ CSV (LƯU & ĐỌC FILE) ==================
def luu_bao_khach(telegram_id, username_khach, ma_ctv, so_tien):
    file_exists = os.path.isfile(FILE_DATA_KHACH)
    # Dùng utf-8-sig để Excel mở không bị lỗi font tiếng Việt
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
        next(reader, None) # Bỏ qua dòng tiêu đề
        for row in reader:
            if len(row) >= 5:
                # row[3] là Mã CTV, row[4] là Số tiền
                if row[3].strip().lower() == ma_ctv_can_tim.lower():
                    tong_khach += 1
                    try:
                        # Xóa chữ cái hoặc dấu phẩy nếu có để cộng tiền
                        tien_clean = ''.join(filter(str.isdigit, row[4]))
                        tong_tien += int(tien_clean)
                    except:
                        pass
    return tong_khach, tong_tien

# ================== LỆNH XÓA TIN NHẮN THỦ CÔNG ==================
async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_msg_id = update.message.message_id
    
    # Xóa lệnh người dùng vừa gõ
    try:
        await update.message.delete()
    except:
        pass

    status_msg = await context.bot.send_message(chat_id, "🧹 Đang dọn dẹp 20 tin nhắn gần nhất...", parse_mode="HTML")
    
    # Vòng lặp xóa 20 tin nhắn cũ
    for i in range(1, 21): 
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=current_msg_id - i)
        except Exception:
            pass 
            
    await context.bot.edit_message_text("✅ <b>Đã dọn dẹp xong!</b>", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
    await asyncio.sleep(2)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
    except:
        pass

# ================== MENU CHÍNH (START) ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reset trạng thái về bình thường
    context.user_data['state'] = STATE_NORMAL
    context.user_data['logged_ctv_code'] = None

    menu_keyboard = [
        [KeyboardButton("🍀 Giới Thiệu Group"), KeyboardButton("🎁 Nhận Giftcode")],
        [KeyboardButton("💰 Ưu Đãi & Khuyến Mãi"), KeyboardButton("🔒 Nạp/Rút USDT An Toàn")],
        [KeyboardButton("🤝 Đăng Ký CTV Ngay"), KeyboardButton("👤 Tài Khoản Cá Nhân")],
        [KeyboardButton("🔐 Đăng Nhập CTV (Báo Khách)")], 
    ]
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

    # Nội dung chào mừng
    welcome_text = (
        "👋 <b>Xin chào Tân Thủ! Một ngày mới tuyệt vời để bắt đầu tại 78win!!!</b>\n\n"
        "🎉 <b>THƯỞNG CHÀO MỪNG TÂN THỦ</b> đã sẵn sàng.\n"
        "Chỉ cần nạp đầu từ <b>100 điểm</b> liên tiếp là có thể đăng ký khuyến mãi với điểm thưởng vô cùng giá trị lên tới <b>12,776,000 VND</b>.\n\n"
        "🔥 <b>NẠP ĐẦU TẶNG 8.888K</b>\n"
        "🎫 <b>Mã Khuyến Mãi:</b> <code>ND01</code>\n\n"
        "🚀 <b>Đăng Ký Nhận Ngay 8.888 K – Chỉ Với 3 Bước Siêu Đơn Giản:</b>\n"
        "1️⃣ <b>B1:</b> Đăng ký tài khoản qua link chính thức duy nhất của bot:\n"
        "👉 <a href='https://78max.top'><b>https://78max.top</b></a>\n\n"
        "2️⃣ <b>B2:</b> Vào mục <b>Khuyến Mãi Tân Thủ</b>\n"
        "3️⃣ <b>B3:</b> Xác minh SĐT – Nhận thưởng tự động sau 1–15 phút nếu đủ điều kiện!\n\n"
        "💎 <i>Khuyến Mãi Hội Viên Mới Nạp Lần Đầu Thưởng 200%...</i>"
    )

    if os.path.exists(FILE_BANNER):
        with open(FILE_BANNER, 'rb') as f:
            await update.message.reply_photo(photo=f, caption=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)

# ================== XỬ LÝ LỆNH /F (BÁO KHÁCH) ==================
async def command_bao_khach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kiểm tra login
    user_state = context.user_data.get('state', STATE_NORMAL)
    if user_state != STATE_LOGGED_IN:
        await update.message.reply_text("⚠️ <b>LỖI:</b> Bạn phải Đăng nhập CTV trước mới dùng được lệnh này!", parse_mode="HTML")
        return

    text = update.message.text
    try:
        # Cú pháp: /F Tên - Mã - Tiền
        # Cắt bỏ 3 ký tự đầu (/F )
        content = text[3:].strip()
        parts = content.split('-')
        
        if len(parts) < 3:
            raise ValueError("Thiếu thông tin")
        
        ten_khach = parts[0].strip()
        ma_ctv = parts[1].strip()
        so_tien = parts[2].strip()
        
        telegram_id = update.effective_user.id
        luu_bao_khach(telegram_id, ten_khach, ma_ctv, so_tien)
        
        await update.message.reply_text(
            f"✅ <b>BÁO KHÁCH THÀNH CÔNG!</b>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"👤 Khách: <b>{ten_khach}</b>\n"
            f"🆔 Mã CTV: <b>{ma_ctv}</b>\n"
            f"💰 Nạp: <b>{so_tien}</b>\n\n"
            f"📂 <i>Đã lưu vào hệ thống đối soát.</i>",
            parse_mode="HTML"
        )
        
    except Exception:
        await update.message.reply_text(
            "⚠️ <b>SAI CÚ PHÁP!</b>\n\n"
            "Vui lòng nhập đúng mẫu:\n"
            "<code>/F TênKhách - MãCTV - SốTiền</code>\n\n"
            "Ví dụ: <code>/F TuanAnh - CTV01 - 500k</code>",
            parse_mode="HTML"
        )

# ================== XỬ LÝ LOGIC TIN NHẮN & NÚT BẤM ==================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_state = context.user_data.get('state', STATE_NORMAL)
    
    # --- 1. QUY TRÌNH ĐĂNG NHẬP ---
    if text == "🔐 Đăng Nhập CTV (Báo Khách)":
        context.user_data['state'] = STATE_WAITING_ID
        await update.message.reply_text("👤 <b>Nhập ID Cộng Tác Viên:</b>", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return

    if user_state == STATE_WAITING_ID:
        if text in CTV_ACCOUNTS:
            context.user_data['temp_id'] = text
            context.user_data['state'] = STATE_WAITING_PASS
            await update.message.reply_text(f"✅ ID <b>{text}</b> hợp lệ.\n🔑 <b>Nhập Mật Khẩu:</b>", parse_mode="HTML")
        else:
            await update.message.reply_text("❌ ID sai! Nhập lại hoặc gõ /start để thoát.")
        return

    if user_state == STATE_WAITING_PASS:
        saved_id = context.user_data.get('temp_id')
        if text == CTV_ACCOUNTS.get(saved_id):
            context.user_data['state'] = STATE_LOGGED_IN
            context.user_data['logged_ctv_code'] = saved_id
            
            # Menu dành riêng cho CTV
            kb_ctv = [
                [KeyboardButton("📊 Xem Thống Kê"), KeyboardButton("📞 Lấy File Đối Soát")],
                [KeyboardButton("❌ Đăng Xuất")]
            ]
            await update.message.reply_text(
                f"🎉 <b>ĐĂNG NHẬP THÀNH CÔNG!</b>\nHello CTV: <b>{saved_id}</b>\n\n"
                f"📝 <b>CÚ PHÁP BÁO KHÁCH:</b>\n"
                f"<code>/F TênKhách - MãCTV - SốTiền</code>\n"
                f"VD: <code>/F Huy - {saved_id} - 200</code>",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(kb_ctv, resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Sai mật khẩu! Nhập lại.")
        return

    # --- 2. MENU CỦA CTV ĐÃ ĐĂNG NHẬP ---
    if user_state == STATE_LOGGED_IN:
        current_ctv = context.user_data.get('logged_ctv_code')

        if text == "❌ Đăng Xuất":
            await start(update, context) # Về menu chính
            return

        elif text == "📊 Xem Thống Kê":
            sl, tien = dem_so_khach(current_ctv)
            await update.message.reply_text(
                f"📊 <b>THỐNG KÊ: {current_ctv}</b>\n"
                f"-------------------\n"
                f"👥 Khách đã báo: <b>{sl}</b>\n"
                f"💵 Tổng tiền: <b>{tien:,}</b>\n\n"
                f"<i>(Số liệu từ file hệ thống)</i>",
                parse_mode="HTML"
            )
            return

        elif text == "📞 Lấy File Đối Soát":
            await update.message.reply_text(
                "📞 <b>LIÊN HỆ ADMIN</b>\n"
                "Nhắn tin Admin để nhận file Excel.\n"
                "👉 <a href='https://t.me/crown66666'><b>@crown66666</b></a>",
                parse_mode="HTML", disable_web_page_preview=True
            )
            return
        
        if not text.startswith('/'):
            await update.message.reply_text("💡 Hãy dùng lệnh <code>/F ...</code> để báo khách.", parse_mode="HTML")
            return

    # --- 3. MENU NGƯỜI DÙNG THƯỜNG (CHƯA LOGIN) ---
    msg_content = ""
    photo_path = None

    if text == "🍀 Giới Thiệu Group":
        msg_content = (
            "🌿 <b>CỘNG ĐỒNG XÔI MẶN</b> 🌿\n\n"
            "✅ Săn Giftcode độc quyền\n"
            "✅ Cập nhật kèo thơm\n"
            "👉 <a href='https://t.me/congdongxoiman'><b>t.me/congdongxoiman</b></a>"
        )
    elif text == "🎁 Nhận Giftcode":
        msg_content = (
            "🎁 <b>KHO GIFTCODE</b> 🎁\n\n"
            "👉 <b>Lấy code ngay:</b> \n"
            "🔗 <a href='https://hupcode.xo.je'>https://hupcode.xo.je</a>"
        )
    elif text == "💰 Ưu Đãi & Khuyến Mãi":
        msg_content = (
            "🧧 <b>KHUYẾN MÃI TẾT 2026</b> 🧧\n\n"
            "• Nạp đầu tặng <b>150%</b>\n"
            "• Hoàn trả <b>1.2%</b> vô tận\n"
            "👉 Xem tại: <a href='https://t.me/congdongxoiman'>Group Telegram</a>"
        )
    elif text == "🔒 Nạp/Rút USDT An Toàn":
        msg_content = (
            "📥 <b>HƯỚNG DẪN NẠP USDT</b>\n"
            "1️⃣ Vào Binance -> Ví -> Gửi.\n"
            "2️⃣ Chọn mạng lưới TRC20/ERC20.\n"
            "3️⃣ Nhập ví lấy trên Game.\n\n"
            "👉 <i>Cần hỗ trợ: <a href='https://t.me/crown66666'>@crown66666</a></i>"
        )
        photo_path = FILE_ANH_NAP
    elif text == "🤝 Đăng Ký CTV Ngay":
        msg_content = (
            "🤝 <b>TUYỂN DỤNG ĐẠI LÝ/CTV</b>\n"
            "💰 Hoa hồng: 100k/khách nạp đầu.\n"
            "👉 Liên hệ Admin nhận Code CTV: <a href='https://t.me/crown66666'><b>@crown66666</b></a>"
        )
    elif text == "👤 Tài Khoản Cá Nhân":
        msg_content = (
            f"👤 <b>ID Của Bạn:</b> <code>{update.effective_user.id}</code>\n"
            f"🏷 <b>Username:</b> @{update.effective_user.username}\n"
            "🛠 Cần hỗ trợ? Nhấn nút Báo Khách!"
        )
    elif text == "📢 Báo Khách / Hỗ Trợ":
        msg_content = "✅ Đã gửi yêu cầu! Admin sẽ phản hồi sau 1-5 phút."
    else:
        msg_content = "🤔 Vui lòng chọn menu bên dưới."

    # Gửi tin nhắn
    chat_id = update.effective_chat.id
    if photo_path and os.path.exists(photo_path):
        with open(photo_path, 'rb') as f:
            await context.bot.send_photo(chat_id, photo=f, caption=msg_content, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id, text=msg_content, parse_mode="HTML", disable_web_page_preview=True)

# ================== MAIN ==================
def main():
    keep_alive()
    print("🚀 Bot đang khởi động...")
    app = ApplicationBuilder().token(TOKEN_BOT).build()

    # Các lệnh hệ thống
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('xoa', clear_chat))
    app.add_handler(CommandHandler('cls', clear_chat))
    
    # Lệnh Báo Khách
    app.add_handler(CommandHandler('F', command_bao_khach))
    app.add_handler(CommandHandler('f', command_bao_khach))

    # Xử lý tin nhắn text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot đã sẵn sàng phục vụ!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
