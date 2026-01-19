import logging
import os  # <--- Dùng để kiểm tra file ảnh
from keep_alive import keep_alive
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ================== CẤU HÌNH & TÊN FILE ẢNH ==================
TOKEN_BOT = '8269134409:AAFCc7tB1kdc0et_4pnH52SoG_RyCu-UX0w'

# Tên file ảnh (Chắc chắn rằng các file này nằm cùng thư mục với file code)
FILE_ANH_NAP = "huong-dan-nap-usdt-binance.jpg"
FILE_ANH_RUT = "huong-dan-nap-usdt.jpg"
FILE_BANNER = "banner.jpg"  # <--- File ảnh Banner

# ================== LOGGING ==================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== MENU CHÍNH (START) ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # --- KHỞI TẠO BÀN PHÍM MENU ---
    menu_keyboard = [
        [KeyboardButton("🍀 Giới Thiệu Group"), KeyboardButton("🎁 Nhận Giftcode")],
        [KeyboardButton("💰 Ưu Đãi & Khuyến Mãi"), KeyboardButton("🔒 Nạp/Rút USDT An Toàn")],
        [KeyboardButton("🤝 Đăng Ký CTV Ngay"), KeyboardButton("👤 Tài Khoản Cá Nhân")],
        [KeyboardButton("📢 Báo Khách / Hỗ Trợ")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        menu_keyboard,
        resize_keyboard=True,
        one_time_keyboard=False, # Để False để menu luôn hiện
        input_field_placeholder="👇 Chọn tính năng bên dưới..."
    )

    # --- NỘI DUNG CHÀO MỪNG ---
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
        "💎 <i>Khuyến Mãi Hội Viên Mới Nạp Lần Đầu Thưởng 200%, Bạn Còn Chần Chờ Chi Nữa!!</i>\n\n"
        "🌟 <b>Nhanh Tay Tham Gia 78WIN Vô Vàn Sự Kiện Hấp Dẫn Được Cập Nhật Mỗi Ngày!</b>"
    )

    # --- GỬI ẢNH BANNER KÈM TEXT ---
    if os.path.exists(FILE_BANNER):
        with open(FILE_BANNER, 'rb') as f:
            await update.message.reply_photo(
                photo=f,
                caption=welcome_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
    else:
        # Nếu không thấy ảnh banner thì gửi text không
        await update.message.reply_text(
            f"⚠️ Lỗi: Không tìm thấy file '{FILE_BANNER}'.\n\n" + welcome_text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

# ================== XỬ LÝ MENU (BUTTON CLICK) ==================
async def handle_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # --- KHÔNG CÒN LỆNH XÓA TIN NHẮN CŨ Ở ĐÂY NỮA ---

    msg_content = ""
    photo_path = None # Biến để lưu đường dẫn ảnh nếu cần gửi ảnh
    
    # --- 1. GIỚI THIỆU GROUP ---
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

    # --- 2. NHẬN GIFTCODE ---
    elif text == "🎁 Nhận Giftcode":
        msg_content = (
            "🎁 <b>KHO GIFTCODE & SỰ KIỆN</b> 🎁\n\n"
            "🔔 Mã thưởng được phát <b>MỖI NGÀY</b> tại Group chính thức.\n\n"
            "👉 <b>Vào lấy code ngay:</b> \n"
            "🔗 <a href='https://hupcode.xo.je'>https://hupcode.xo.je</a>\n\n"
            "<i>💡 Mẹo: Bật thông báo Group để không bỏ lỡ code xịn nhé!</i>"
        )

    # --- 3. KHUYẾN MÃI ---
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

    # --- 4. NẠP RÚT (CÓ ẢNH) ---
    elif text == "🔒 Nạp/Rút USDT An Toàn":
        msg_content = (
            "📥 <b>HƯỚNG DẪN NẠP USDT BẰNG BINANCE</b>\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "1️⃣ <b>Bước 1:</b> Ở giao diện chính BINANCE chọn <b>Tài sản</b> ➝ chọn <b>Gửi</b>.\n"
            "2️⃣ <b>Bước 2:</b> Chọn <b>Rút tiền trên chuỗi</b> ➝ Chọn <b>USDT</b>.\n"
            "3️⃣ <b>Bước 3:</b> Nhập thông tin:\n"
            "   • <b>Mạng lưới:</b> TRC20 hoặc ERC20\n"
            "   • <b>Số tiền:</b> Nhập số muốn nạp ➝ Chọn <b>Rút</b>.\n\n"
            "4️⃣ <b>Bước 4:</b> Xác nhận 2 lớp để hoàn thành.\n\n"
            "📤 <b>RÚT TIỀN:</b> Hệ thống tự động 24/7 (3-10 phút).\n\n"
            "👉 <i>Inbox ngay Admin <a href='https://t.me/crown66666'><b>@crown66666</b></a> nếu cần hỗ trợ trung gian!</i>"
        )
        photo_path = FILE_ANH_NAP # Gán ảnh để tý gửi

    # --- 5. ĐĂNG KÝ CTV ---
    elif text == "🤝 Đăng Ký CTV Ngay":
        msg_content = (
            "🤝 <b>HỢP TÁC NHƯ Ý - KIẾM TIỀN TỶ </b> 🤝\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "💼 <b>CÔNG VIỆC:</b> Chia sẻ link giới thiệu game.\n"
            "💰 <b>HOA HỒNG KHỦNG:</b>\n"
            "💵 <b>100.000 VNĐ</b> / 1 Khách nạp > 1 triệu.\n\n"
            "📝 <b>QUY TRÌNH:</b>\n"
            "1️⃣ Liên hệ Admin nhận mã.\n"
            "2️⃣ Vào nhóm làm việc riêng.\n"
            "3️⃣ <b>BÁO KHÁCH:</b> Có khách nạp phải báo ngay.\n\n"
            "🚀 <b>ĐĂNG KÝ NGAY:</b>\n"
            "👉 Telegram: <a href='https://t.me/crown66666'><b>@crown66666</b></a>"
        )

    # --- 6. TÀI KHOẢN ---
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

    # --- 7. BÁO KHÁCH ---
    elif text == "📢 Báo Khách / Hỗ Trợ":
        msg_content = (
            "✅ <b>ĐÃ GỬI YÊU CẦU HỖ TRỢ!</b>\n\n"
            "Hệ thống đã ghi nhận yêu cầu của bạn.\n"
            "⏳ Admin sẽ phản hồi trong vòng <b>1-5 phút</b>.\n\n"
            "🔔 <i>Vui lòng chú ý tin nhắn chờ nhé!</i>"
        )

    # --- FALLBACK ---
    else:
        msg_content = "🤔 <b>Vui lòng chọn các nút bấm có sẵn trên menu nhé!</b> 👇"

    # --- BƯỚC 2: GỬI TIN NHẮN MỚI NGAY LẬP TỨC ---
    chat_id = update.effective_chat.id

    # Nếu có ảnh thì gửi ảnh
    if photo_path and os.path.exists(photo_path):
        with open(photo_path, 'rb') as f:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=f,
                caption=msg_content,
                parse_mode="HTML"
            )
    else:
        # Nếu không có ảnh (hoặc file lỗi) thì gửi text
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg_content,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

# ================== MAIN ==================
def main():
    keep_alive()
    print("🚀 Bot 78Win Assistant đang khởi động...")
    app = ApplicationBuilder().token(TOKEN_BOT).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_click))

    print("✅ Bot đã sẵn sàng phục vụ!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
