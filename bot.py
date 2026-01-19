import logging
import os  # <--- QUAN TRỌNG: Thư viện để tìm file trong máy
from keep_alive import keep_alive
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ================== CẤU HÌNH & TÊN FILE ẢNH ==================
TOKEN_BOT = '8269134409:AAFCc7tB1kdc0et_4pnH52SoG_RyCu-UX0w'

# Tên file ảnh nằm trong cùng thư mục với file code bot.py
# Bạn hãy chắc chắn tên file ở đây khớp 100% với tên file bạn lưu trong máy
FILE_ANH_NAP = "huong-dan-nap-usdt-binance.jpg"
FILE_ANH_RUT = "huong-dan-nap-usdt.jpg"

# ================== LOGGING ==================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== MENU CHÍNH ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = user.first_name or "Bạn"

    menu_keyboard = [
        [KeyboardButton("🍀 Giới Thiệu Group"), KeyboardButton("🎁 Nhận Giftcode")],
        [KeyboardButton("💰 Ưu Đãi & Khuyến Mãi"), KeyboardButton("🔒 Nạp/Rút USDT An Toàn")],
        [KeyboardButton("🤝 Đăng Ký CTV Ngay"), KeyboardButton("👤 Tài Khoản Cá Nhân")],
        [KeyboardButton("📢 Báo Khách / Hỗ Trợ")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        menu_keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="👇 Chọn tính năng bên dưới..."
    )

    welcome_text = (
        f"👋 Xin chào <b>{first_name}</b>!\n\n"
        "🌟 <b>Chào mừng đến với C168 Assistant</b> 🌟\n"
        "<i>Trợ lý ảo hỗ trợ kết nối, nhận thưởng & CSKH 24/7.</i>\n\n"
        "👇 <b>BẠN CẦN HỖ TRỢ GÌ HÔM NAY?</b>\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "• 🎁 <b>Giftcode:</b> Nhận mã thưởng mỗi ngày\n"
        "• 🤝 <b>Hợp tác:</b> Kiếm tiền cùng hệ thống CTV\n"
        "• 🔒 <b>Nạp Rút:</b> Hướng dẫn an toàn, bảo mật\n"
        "• 🆘 <b>Hỗ trợ:</b> Kết nối Admin siêu tốc\n\n"
        "<i>Vui lòng chọn nút chức năng bên dưới menu!</i> 👇"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# ================== XỬ LÝ MENU ==================
async def handle_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # --- 1. GIỚI THIỆU GROUP ---
    if text == "🍀 Giới Thiệu Group":
        gioithieu_text = (
            "🌿 <b>CỘNG ĐỒNG C168 - GIAO LƯU & NHẬN QUÀ</b> 🌿\n"
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
        await update.message.reply_text(gioithieu_text, parse_mode="HTML", disable_web_page_preview=True)

    # --- 2. NHẬN GIFTCODE ---
    elif text == "🎁 Nhận Giftcode":
        giftcode_text = (
            "🎁 <b>KHO GIFTCODE & SỰ KIỆN</b> 🎁\n\n"
            "🔔 Mã thưởng được phát <b>MỖI NGÀY</b> tại Group chính thức.\n\n"
            "👉 <b>Vào lấy code ngay:</b> \n"
            "🔗 <a href='https://hupcode.xo.je'>https://hupcode.xo.je</a>\n\n"
            "<i>💡 Mẹo: Bật thông báo Group để không bỏ lỡ code xịn nhé!</i>"
        )
        await update.message.reply_text(giftcode_text, parse_mode="HTML", disable_web_page_preview=True)

    # --- 3. KHUYẾN MÃI ---
    elif text == "💰 Ưu Đãi & Khuyến Mãi":
        khuyenmai_text = (
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
        await update.message.reply_text(khuyenmai_text, parse_mode="HTML", disable_web_page_preview=True)

    # --- PHẦN NẠP RÚT (DÙNG ẢNH TRONG MÁY) ---
    elif text == "🔒 Nạp/Rút USDT An Toàn":
        
        # --- Phần 1: Hướng dẫn Nạp ---
        caption_nap = (
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
            "🔒 <i>Hệ thống tự động duyệt sau 3-5 phút.</i>"
        )
        
        # Xử lý gửi ảnh từ máy tính (Ảnh Nạp)
        if os.path.exists(FILE_ANH_NAP):
            with open(FILE_ANH_NAP, 'rb') as f:
                await update.message.reply_photo(photo=f, caption=caption_nap, parse_mode="HTML")
        else:
            await update.message.reply_text(
                f"⚠️ Lỗi: Không tìm thấy file ảnh '{FILE_ANH_NAP}' trong thư mục. Vui lòng kiểm tra lại tên file.",
                parse_mode="HTML"
            )

        # --- Phần 2: Hướng dẫn Rút ---
        caption_rut = (
            "📤 <b>RÚT TIỀN & PHƯƠNG THỨC KHÁC</b>\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "⚙️ <b>Trạng thái:</b> Hệ thống rút tiền tự động hoạt động 24/7.\n\n"
            "📝 <b>Lưu ý quan trọng:</b>\n"
            "• Kiểm tra kỹ địa chỉ ví nhận tiền.\n"
            "• Quét mã QR hoặc Sao chép chính xác (như hình).\n"
            "• Thời gian xử lý: 3 - 10 phút.\n\n"
            "🔔 <i>Nếu cần hỗ trợ trung gian/tiền mặt, vui lòng liên hệ Admin.</i>"
        )
        
        # Xử lý gửi ảnh từ máy tính (Ảnh Rút)
        if os.path.exists(FILE_ANH_RUT):
            with open(FILE_ANH_RUT, 'rb') as f:
                await update.message.reply_photo(photo=f, caption=caption_rut, parse_mode="HTML")
        else:
             await update.message.reply_text(
                f"⚠️ Lỗi: Không tìm thấy file ảnh '{FILE_ANH_RUT}' trong thư mục.",
                parse_mode="HTML"
            )

        # --- Phần 3: Chốt đơn ---
        await update.message.reply_text(
            "⚠️ <b>GIẢI PHÁP THANH TOÁN ẨN DANH</b> ⚠️\n\n"
            "🚀 <b>DỊCH VỤ TRUNG GIAN ĐỘC QUYỀN:</b>\n"
            "✅ Phí siêu rẻ: Chỉ <b>0.1%</b>\n"
            "✅ Bảo mật tuyệt đối danh tính\n\n"
            "👉 <i>Inbox ngay Admin <a href='https://t.me/crown66666'><b>@crown66666</b></a> để được hỗ trợ!</i>",
            parse_mode="HTML"
        )

    # --- 5. ĐĂNG KÝ CTV ---
    elif text == "🤝 Đăng Ký CTV Ngay":
        ctv_text = (
            "🤝 <b>HỢP TÁC ĐẠI LÝ - KIẾM TIỀN TỶ</b> 🤝\n"
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
        await update.message.reply_text(ctv_text, parse_mode="HTML", disable_web_page_preview=True)

    # --- 6. TÀI KHOẢN ---
    elif text == "👤 Tài Khoản Cá Nhân":
        user_info = (
            f"👤 <b>HỒ SƠ NGƯỜI DÙNG</b>\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"🆔 <b>ID Telegram:</b> <code>{update.effective_user.id}</code>\n"
            f"🏷 <b>Username:</b> @{update.effective_user.username or 'Không có'}\n"
            f"💼 <b>Trạng thái:</b> Thành viên\n"
            "💰 <b>Số dư ví:</b> 0đ <i>(Đang đồng bộ...)</i>\n\n"
            "🛠 <i>Cần hỗ trợ tài khoản? Nhấn nút Báo Khách bên dưới!</i>"
        )
        await update.message.reply_text(user_info, parse_mode="HTML")

    # --- 7. BÁO KHÁCH / HỖ TRỢ ---
    elif text == "📢 Báo Khách / Hỗ Trợ":
        support_text = (
            "✅ <b>ĐÃ GỬI YÊU CẦU HỖ TRỢ!</b>\n\n"
            "Hệ thống đã ghi nhận yêu cầu của bạn.\n"
            "⏳ Admin sẽ phản hồi trong vòng <b>1-5 phút</b>.\n\n"
            "🔔 <i>Vui lòng chú ý tin nhắn chờ nhé!</i>"
        )
        await update.message.reply_text(support_text, parse_mode="HTML")

    # --- FALLBACK ---
    else:
        await update.message.reply_text(
            "🤔 <b>Tôi chưa hiểu ý bạn lắm...</b>\n\n"
            "Vui lòng chọn các nút bấm có sẵn trên menu nhé! 👇",
            reply_markup=update.message.reply_markup,
            parse_mode="HTML"
        )

# ================== MAIN ==================
def main():
    keep_alive()
    print("🚀 Bot C168 Assistant đang khởi động...")
    app = ApplicationBuilder().token(TOKEN_BOT).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_click))

    print("✅ Bot đã sẵn sàng phục vụ!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()