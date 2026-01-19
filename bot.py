import logging
import os
import csv
import json
import asyncio
from datetime import datetime
from keep_alive import keep_alive
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

TOKEN_BOT = '8269134409:AAFCc7tB1kdc0et_4pnH52SoG_RyCu-UX0w'
ID_ADMIN_CHINH = 6340716909

FILE_ANH_NAP = "huong-dan-nap-usdt-binance.jpg"
FILE_ANH_RUT = "huong-dan-nap-usdt.jpg"
FILE_BANNER = "banner.jpg"
FILE_DATA_KHACH = "danh_sach_bao_khach.csv"
FILE_TK_CTV = "taikhoan_ctv.json"

DEFAULT_ACCOUNTS = {
    "ctv01": "123456",
    "admin": "admin888",
    "huydeptrai": "888888"
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

STATE_NORMAL = 0
STATE_WAITING_ID = 1
STATE_WAITING_PASS = 2
STATE_LOGGED_IN = 3

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
                    except:
                        pass
    return tong_khach, tong_tien

async def admin_them_ctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH:
        return
    
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
        await update.message.reply_text(f"✅ Đã thêm CTV: <b>{new_user}</b>\nMật khẩu: <b>{new_pass}</b>", parse_mode="HTML")
    except:
        await update.message.reply_text("❌ Lỗi hệ thống.")

async def admin_xoa_ctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH:
        return
        
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
    except:
        await update.message.reply_text("❌ Lỗi hệ thống.")

async def admin_quan_ly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: 
        await update.message.reply_text("⛔ <b>Bạn không có quyền truy cập Admin!</b>", parse_mode="HTML")
        return

    accounts = load_ctv_accounts()
    tong_so_ctv = len(accounts)
    msg_report = f"👑 <b>BẢNG QUẢN TRỊ ADMIN</b> 👑\n"
    msg_report += f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
    msg_report += f"👥 Tổng số CTV: <b>{tong_so_ctv}</b> người\n\n"
    msg_report += "📊 <b>CHI TIẾT HIỆU QUẢ:</b>\n"

    total_all_money = 0
    for ma_ctv in accounts:
        sl, tien = dem_so_khach(ma_ctv)
        total_all_money += tien
        icon = "🟢" if sl > 0 else "⚪"
        msg_report += f"{icon} <b>{ma_ctv}:</b> {sl} khách | {tien:,} k\n"

    msg_report += f"\n💰 <b>TỔNG DOANH THU HỆ THỐNG: {total_all_money:,} k</b>\n"
    msg_report += f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
    msg_report += f"➕ Thêm CTV: <code>/themctv user pass</code>\n"
    msg_report += f"➖ Xóa CTV: <code>/xoactv user</code>"
    
    await update.message.reply_text(msg_report, parse_mode="HTML")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await update.message.delete()
    except: pass
    
    status_msg = await context.bot.send_message(chat_id, "🧹 Đang dọn dẹp...", parse_mode="HTML")
    for i in range(1, 21): 
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id - i)
        except: pass
    await asyncio.sleep(1)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = STATE_NORMAL
    context.user_data['logged_ctv_code'] = None

    menu_keyboard = [
        [KeyboardButton("🍀 Giới Thiệu Group"), KeyboardButton("🎁 Nhận Giftcode")],
        [KeyboardButton("💰 Ưu Đãi & Khuyến Mãi"), KeyboardButton("🔒 Nạp/Rút USDT An Toàn")],
        [KeyboardButton("🤝 Đăng Ký CTV Ngay"), KeyboardButton("👤 Tài Khoản Cá Nhân")],
        [KeyboardButton("🔐 Đăng Nhập CTV (Báo Khách)")], 
    ]
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

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

    if os.path.exists(FILE_BANNER):
        with open(FILE_BANNER, 'rb') as f:
            await update.message.reply_photo(photo=f, caption=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)

async def command_bao_khach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state = context.user_data.get('state', STATE_NORMAL)
    if user_state != STATE_LOGGED_IN:
        await update.message.reply_text("⚠️ <b>LỖI:</b> Bạn phải Đăng nhập CTV trước!", parse_mode="HTML")
        return

    text = update.message.text
    try:
        content = text[3:].strip()
        parts = content.split('-')
        if len(parts) < 3: raise ValueError
        
        ten_khach = parts[0].strip()
        ma_ctv = parts[1].strip()
        so_tien = parts[2].strip()
        
        current_ctv = context.user_data.get('logged_ctv_code')
        if ma_ctv.lower() != current_ctv.lower():
             await update.message.reply_text(f"⚠️ Bạn đang đăng nhập acc <b>{current_ctv}</b> nhưng lại báo cho <b>{ma_ctv}</b>. Vui lòng kiểm tra lại!", parse_mode="HTML")
             return

        luu_bao_khach(update.effective_user.id, ten_khach, ma_ctv, so_tien)
        await update.message.reply_text(
            f"✅ <b>BÁO KHÁCH THÀNH CÔNG!</b>\n"
            f"👤 Khách: <b>{ten_khach}</b>\n🆔 CTV: <b>{ma_ctv}</b>\n💰 Nạp: <b>{so_tien}</b>\n\n"
            f"📂 <i>Đã lưu vào hệ thống đối soát.</i>",
            parse_mode="HTML"
        )
    except:
        await update.message.reply_text("⚠️ Sai cú pháp! VD: <code>/F Huy - ctv01 - 200</code>", parse_mode="HTML")

# ================== LỆNH MỚI: XEM CHI TIẾT CTV ==================
async def admin_xem_chi_tiet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền Admin
    if update.effective_user.id != ID_ADMIN_CHINH:
        return

    # 2. Lấy tên CTV từ lệnh gõ (VD: /chitiet ctv01)
    try:
        args = context.args
        if len(args) < 1:
            await update.message.reply_text("⚠️ Cách dùng: /chitiet <mã_ctv>\nVD: /chitiet ctv01", parse_mode="HTML")
            return
        
        target_ctv = args[0].strip().lower()
        
        # 3. Đọc file CSV để tìm dữ liệu
        if not os.path.exists(FILE_DATA_KHACH):
            await update.message.reply_text("📭 Chưa có dữ liệu nào.", parse_mode="HTML")
            return

        found_rows = []
        tong_tien_check = 0
        
        with open(FILE_DATA_KHACH, mode='r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            next(reader, None) # Bỏ qua tiêu đề
            for row in reader:
                # row[3] là Mã CTV
                if len(row) >= 5 and row[3].strip().lower() == target_ctv:
                    # Format: ThờiGian - TênKhách - Tiền
                    # Lấy giờ phút thôi cho ngắn (row[0] là full ngày giờ)
                    short_time = row[0][11:16] # Cắt lấy HH:MM
                    found_rows.append(f"🕒 <code>{short_time}</code> | 👤 <b>{row[2]}</b> | 💰 {row[4]}")
                    
                    # Cộng tổng tiền để check
                    try:
                        tien_clean = ''.join(filter(str.isdigit, row[4]))
                        tong_tien_check += int(tien_clean)
                    except: pass
        
        # 4. Gửi kết quả
        if not found_rows:
            await update.message.reply_text(f"❌ CTV <b>{target_ctv}</b> chưa có khách nào.", parse_mode="HTML")
        else:
            # Chỉ lấy 15 giao dịch gần nhất để tránh tin nhắn quá dài bị lỗi
            last_rows = found_rows[-15:] 
            
            msg = f"📄 <b>LỊCH SỬ GIAO DỊCH: {target_ctv.upper()}</b>\n"
            msg += f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            msg += "\n".join(last_rows)
            msg += f"\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            msg += f"💵 <b>TỔNG CỘNG: {tong_tien_check:,}</b>"
            
            await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Lỗi xem chi tiết: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra khi đọc dữ liệu.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_state = context.user_data.get('state', STATE_NORMAL)
    
    if text == "🔐 Đăng Nhập CTV (Báo Khách)":
        context.user_data['state'] = STATE_WAITING_ID
        await update.message.reply_text("👤 <b>Nhập ID Cộng Tác Viên:</b>", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return

    if user_state == STATE_WAITING_ID:
        accounts = load_ctv_accounts()
        if text in accounts:
            context.user_data['temp_id'] = text
            context.user_data['state'] = STATE_WAITING_PASS
            await update.message.reply_text(f"✅ ID <b>{text}</b> hợp lệ.\n🔑 <b>Nhập Mật Khẩu:</b>", parse_mode="HTML")
        else:
            await update.message.reply_text("❌ ID sai! Nhập lại hoặc gõ /start để thoát.")
        return

    if user_state == STATE_WAITING_PASS:
        saved_id = context.user_data.get('temp_id')
        accounts = load_ctv_accounts()
        if text == accounts.get(saved_id):
            context.user_data['state'] = STATE_LOGGED_IN
            context.user_data['logged_ctv_code'] = saved_id
            kb_ctv = [[KeyboardButton("📊 Xem Thống Kê"), KeyboardButton("📞 Lấy File Đối Soát")], [KeyboardButton("❌ Đăng Xuất")]]
            await update.message.reply_text(
                f"🎉 <b>ĐĂNG NHẬP THÀNH CÔNG!</b>\nXin chào CTV: <b>{saved_id}</b>\n\n"
                f"📝 <b>CÚ PHÁP BÁO KHÁCH:</b>\n"
                f"<code>/F TênKhách - MãCTV - SốTiền</code>\n",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(kb_ctv, resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Sai mật khẩu!")
        return

    if user_state == STATE_LOGGED_IN:
        current_ctv = context.user_data.get('logged_ctv_code')
        if text == "❌ Đăng Xuất":
            await start(update, context)
            return
        elif text == "📊 Xem Thống Kê":
            sl, tien = dem_so_khach(current_ctv)
            await update.message.reply_text(f"📊 <b>{current_ctv}</b>: {sl} khách | {tien:,} k", parse_mode="HTML")
            return
        elif text == "📞 Lấy File Đối Soát":
            await update.message.reply_text("📞 Liên hệ Admin: @crown66666", parse_mode="HTML")
            return
        if not text.startswith('/'):
            await update.message.reply_text("💡 Dùng lệnh <code>/F ...</code> để báo khách.", parse_mode="HTML")
            return

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

    chat_id = update.effective_chat.id
    if photo_path and os.path.exists(photo_path):
        with open(photo_path, 'rb') as f:
            await context.bot.send_photo(chat_id, photo=f, caption=msg_content, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id, text=msg_content, parse_mode="HTML", disable_web_page_preview=True)

def main():
    keep_alive()
    print("🚀 Bot running...")
    app = ApplicationBuilder().token(TOKEN_BOT).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('xoa', clear_chat))
    app.add_handler(CommandHandler('cls', clear_chat))
    app.add_handler(CommandHandler('F', command_bao_khach))
    app.add_handler(CommandHandler('f', command_bao_khach))
    
    app.add_handler(CommandHandler('admin', admin_quan_ly))
    app.add_handler(CommandHandler('quanly', admin_quan_ly))
    app.add_handler(CommandHandler('chitiet', admin_xem_chi_tiet)) 
    
    app.add_handler(CommandHandler('themctv', admin_them_ctv))
    app.add_handler(CommandHandler('xoactv', admin_xoa_ctv))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

