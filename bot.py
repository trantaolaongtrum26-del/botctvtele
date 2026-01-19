import logging
import os
import csv  # <--- Thư viện lưu file Excel/CSV
from datetime import datetime
from keep_alive import keep_alive
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ================== CẤU HÌNH & TÊN FILE ==================
TOKEN_BOT = '8269134409:AAFCc7tB1kdc0et_4pnH52SoG_RyCu-UX0w'

FILE_ANH_NAP = "huong-dan-nap-usdt-binance.jpg"
FILE_ANH_RUT = "huong-dan-nap-usdt.jpg"
FILE_BANNER = "banner.jpg"
FILE_DATA_KHACH = "danh_sach_bao_khach.csv" # <--- File lưu dữ liệu báo khách

# --- CẤU HÌNH TÀI KHOẢN CTV (ID : Mật khẩu) ---
# Bạn thêm tài khoản CTV vào đây
CTV_ACCOUNTS = {
    "ctv01": "123456",
    "ctv02": "admin123",
    "huydeptrai": "888888"
}

# ================== LOGGING ==================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== CÁC TRẠNG THÁI HỘI THOẠI ==================
# Dùng để kiểm tra xem người dùng đang làm gì
STATE_NORMAL = 0
STATE_WAITING_ID = 1
STATE_WAITING_PASS = 2
STATE_LOGGED_IN = 3

# ================== HÀM HỖ TRỢ CSV ==================
def luu_bao_khach(telegram_id, username_khach, ma_ctv, so_tien):
    file_exists = os.path.isfile(FILE_DATA_KHACH)
    with open(FILE_DATA_KHACH, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Nếu file chưa có thì viết tiêu đề
        if not file_exists:
            writer.writerow(['ThoiGian', 'TelegramID_CTV', 'TenKhach', 'MaCTV', 'SoTien'])
        
        # Ghi dữ liệu
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), telegram_id, username_khach, ma_ctv, so_tien])

def dem_so_khach(ma_ctv_can_tim):
    if not os.path.exists(FILE_DATA_KHACH):
        return 0, 0 # 0 khách, 0 tiền
    
    tong_khach = 0
    tong_tien = 0
    
    with open(FILE_DATA_KHACH, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader, None) # Bỏ qua tiêu đề
        for row in reader:
            if len(row) >= 4:
                # row[3] là Mã CTV, row[4] là Số tiền
                if row[3].strip().lower() == ma_ctv_can_tim.lower():
                    tong_khach += 1
                    try:
                        tong_tien += int(row[4])
                    except:
                        pass
    return tong_khach, tong_tien

# ================== MENU CHÍNH ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reset trạng thái về bình thường
    context.user_data['state'] = STATE_NORMAL
    
    menu_keyboard = [
        [KeyboardButton("🍀 Giới Thiệu Group"), KeyboardButton("🎁 Nhận Giftcode")],
        [KeyboardButton("💰 Ưu Đãi & Khuyến Mãi"), KeyboardButton("🔒 Nạp/Rút USDT An Toàn")],
        [KeyboardButton("🤝 Đăng Ký CTV Ngay"), KeyboardButton("👤 Tài Khoản Cá Nhân")],
        [KeyboardButton("🔐 Đăng Nhập CTV (Báo Khách)")], # <--- Nút mới
    ]
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

    welcome_text = (
        "👋 <b>Xin chào! Chào mừng đến với Bot Hỗ Trợ 78Win.</b>\n\n"
        "👇 Chọn tính năng bên dưới:"
    )
    
    if os.path.exists(FILE_BANNER):
        with open(FILE_BANNER, 'rb') as f:
            await update.message.reply_photo(photo=f, caption=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

# ================== XỬ LÝ LOGIC CHÍNH ==================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_state = context.user_data.get('state', STATE_NORMAL)
    chat_id = update.effective_chat.id

    # --- 1. XỬ LÝ ĐĂNG NHẬP ---
    if text == "🔐 Đăng Nhập CTV (Báo Khách)":
        context.user_data['state'] = STATE_WAITING_ID
        await update.message.reply_text("👤 <b>Vui lòng nhập ID Cộng Tác Viên:</b>", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return

    # Nếu đang đợi nhập ID
    if user_state == STATE_WAITING_ID:
        # Kiểm tra ID có tồn tại trong danh sách không
        if text in CTV_ACCOUNTS:
            context.user_data['temp_id'] = text # Lưu tạm ID
            context.user_data['state'] = STATE_WAITING_PASS
            await update.message.reply_text(f"✅ ID hợp lệ: <b>{text}</b>\n🔑 <b>Vui lòng nhập Mật Khẩu:</b>", parse_mode="HTML")
        else:
            await update.message.reply_text("❌ ID không tồn tại! Vui lòng nhập lại hoặc gõ /start để thoát.")
        return

    # Nếu đang đợi nhập PASS
    if user_state == STATE_WAITING_PASS:
        saved_id = context.user_data.get('temp_id')
        correct_pass = CTV_ACCOUNTS.get(saved_id)
        
        if text == correct_pass:
            # Đăng nhập thành công
            context.user_data['state'] = STATE_LOGGED_IN
            context.user_data['logged_ctv_code'] = saved_id # Lưu mã CTV chính thức
            
            # Hiển thị menu CTV
            kb_ctv = [
                [KeyboardButton("📊 Xem Thống Kê"), KeyboardButton("📞 Lấy File Đối Soát")],
                [KeyboardButton("❌ Đăng Xuất")]
            ]
            await update.message.reply_text(
                f"🎉 <b>ĐĂNG NHẬP THÀNH CÔNG!</b>\n"
                f"Xin chào CTV: <b>{saved_id}</b>\n\n"
                f"📝 <b>CÚ PHÁP BÁO KHÁCH:</b>\n"
                f"Gõ lệnh theo mẫu sau:\n"
                f"<code>/F TênKhách - MãCTV - SốTiền</code>\n\n"
                f"Ví dụ: <code>/F huydeptrai - {saved_id} - 100</code>\n\n"
                f"👇 Chọn chức năng bên dưới:",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(kb_ctv, resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Mật khẩu sai! Vui lòng nhập lại.")
        return

    # --- 2. XỬ LÝ KHI ĐÃ ĐĂNG NHẬP (MENU CTV) ---
    if user_state == STATE_LOGGED_IN:
        current_ctv = context.user_data.get('logged_ctv_code')

        if text == "❌ Đăng Xuất":
            context.user_data['state'] = STATE_NORMAL
            context.user_data['logged_ctv_code'] = None
            await start(update, context) # Quay về menu chính
            return

        elif text == "📊 Xem Thống Kê":
            sl_khach, tong_tien = dem_so_khach(current_ctv)
            await update.message.reply_text(
                f"📊 <b>THỐNG KÊ CỦA BẠN ({current_ctv})</b>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"👥 Tổng khách đã báo: <b>{sl_khach}</b>\n"
                f"💵 Tổng tiền nạp: <b>{tong_tien:,} k</b>\n\n"
                f"<i>Dữ liệu được trích xuất từ hệ thống.</i>",
                parse_mode="HTML"
            )
            return

        elif text == "📞 Lấy File Đối Soát":
            await update.message.reply_text(
                "📞 <b>LIÊN HỆ ADMIN ĐỐI SOÁT</b>\n\n"
                "Vui lòng nhắn tin trực tiếp cho Admin để nhận file Excel chi tiết.\n"
                "👉 Telegram: <a href='https://t.me/crown66666'><b>@crown66666</b></a>",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            return
        
        # Nếu chat linh tinh khi đang đăng nhập nhưng không phải lệnh /F
        if not text.startswith('/'):
            await update.message.reply_text("💡 Dùng menu bên dưới hoặc gõ lệnh <code>/F ...</code> để báo khách.", parse_mode="HTML")
            return

    # --- 3. XỬ LÝ MENU NGƯỜI DÙNG THƯỜNG (CHƯA ĐĂNG NHẬP) ---
    # (Phần code cũ của bạn)
    if text == "🍀 Giới Thiệu Group":
        await update.message.reply_text("Nội dung giới thiệu...", parse_mode="HTML")
    elif text == "🎁 Nhận Giftcode":
        await update.message.reply_text("Nội dung giftcode...", parse_mode="HTML")
    elif text == "💰 Ưu Đãi & Khuyến Mãi":
        await update.message.reply_text("Nội dung khuyến mãi...", parse_mode="HTML")
    elif text == "🔒 Nạp/Rút USDT An Toàn":
        if os.path.exists(FILE_ANH_NAP):
            with open(FILE_ANH_NAP, 'rb') as f:
                await update.message.reply_photo(photo=f, caption="Hướng dẫn nạp...", parse_mode="HTML")
        else:
            await update.message.reply_text("Hướng dẫn nạp...", parse_mode="HTML")
    elif text == "🤝 Đăng Ký CTV Ngay":
         await update.message.reply_text("Hướng dẫn đăng ký CTV...", parse_mode="HTML")
    elif text == "👤 Tài Khoản Cá Nhân":
         await update.message.reply_text(f"ID: {update.effective_user.id}", parse_mode="HTML")
    # Các nút khác bạn tự điền tiếp như code cũ...

# ================== XỬ LÝ LỆNH /F (BÁO KHÁCH) ==================
async def command_bao_khach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kiểm tra xem đã đăng nhập chưa
    user_state = context.user_data.get('state', STATE_NORMAL)
    if user_state != STATE_LOGGED_IN:
        await update.message.reply_text("⚠️ Bạn cần đăng nhập CTV để sử dụng lệnh này!")
        return

    text = update.message.text # Lấy toàn bộ tin nhắn: /F huy - ctv01 - 100
    try:
        # Bỏ phần "/F " ở đầu và tách chuỗi
        content = text[3:].strip() # Lấy phần sau chữ /F
        parts = content.split('-') # Tách bằng dấu gạch ngang
        
        if len(parts) != 3:
            raise ValueError("Sai định dạng")
        
        ten_khach = parts[0].strip()
        ma_ctv = parts[1].strip()
        so_tien = parts[2].strip()
        
        # Lưu vào file CSV
        telegram_id = update.effective_user.id
        luu_bao_khach(telegram_id, ten_khach, ma_ctv, so_tien)
        
        await update.message.reply_text(
            f"✅ <b>BÁO KHÁCH THÀNH CÔNG!</b>\n\n"
            f"👤 Khách: <b>{ten_khach}</b>\n"
            f"🆔 CTV: <b>{ma_ctv}</b>\n"
            f"💰 Nạp: <b>{so_tien}</b>\n\n"
            f"<i>Dữ liệu đã được lưu vào hệ thống.</i>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        await update.message.reply_text(
            "⚠️ <b>SAI CÚ PHÁP!</b>\n\n"
            "Vui lòng nhập đúng định dạng:\n"
            "<code>/F TênKhách - MãCTV - SốTiền</code>\n\n"
            "Ví dụ: <code>/F TuanAnh - CTV01 - 500</code>\n"
            "(Lưu ý dấu gạch ngang ở giữa)",
            parse_mode="HTML"
        )

# ================== LỆNH XÓA (Giữ nguyên của bạn) ==================
async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await update.message.delete() # Xóa lệnh user
        msg = await context.bot.send_message(chat_id, "🧹 Đang dọn dẹp...")
        # Code xóa lặp lại ở đây... (như code cũ)
        await context.bot.delete_message(chat_id, msg.message_id)
    except:
        pass

# ================== MAIN ==================
def main():
    keep_alive()
    print("🚀 Bot đang khởi động...")
    app = ApplicationBuilder().token(TOKEN_BOT).build()

    # --- Đăng ký lệnh ---
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('xoa', clear_chat))
    
    # --- Đăng ký lệnh báo khách /F ---
    # Lệnh này sẽ bắt các tin nhắn bắt đầu bằng /F hoặc /f
    app.add_handler(CommandHandler('F', command_bao_khach))
    app.add_handler(CommandHandler('f', command_bao_khach))

    # --- Đăng ký xử lý tin nhắn (Menu & Login) ---
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot đã sẵn sàng!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
