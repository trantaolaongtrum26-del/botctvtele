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
    "admin": "admin888"
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
                    except: pass
    return tong_khach, tong_tien

async def admin_them_ctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("⚠️ VD: /themctv tuananh 9999", parse_mode="HTML")
            return
        new_user = args[0].strip()
        new_pass = args[1].strip()
        accounts = load_ctv_accounts()
        if new_user in accounts:
            await update.message.reply_text(f"⚠️ CTV <b>{new_user}</b> đã tồn tại!", parse_mode="HTML")
            return
        accounts[new_user] = new_pass
        save_ctv_accounts(accounts)
        await update.message.reply_text(f"✅ Đã thêm CTV: <b>{new_user}</b> - Pass: <b>{new_pass}</b>", parse_mode="HTML")
    except: await update.message.reply_text("❌ Lỗi.")

async def admin_xoa_ctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        args = context.args
        if len(args) < 1:
            await update.message.reply_text("⚠️ VD: /xoactv tuananh", parse_mode="HTML")
            return
        del_user = args[0].strip()
        accounts = load_ctv_accounts()
        if del_user not in accounts:
            await update.message.reply_text(f"⚠️ Không tìm thấy: {del_user}", parse_mode="HTML")
            return
        del accounts[del_user]
        save_ctv_accounts(accounts)
        await update.message.reply_text(f"🗑️ Đã xóa CTV: <b>{del_user}</b>", parse_mode="HTML")
    except: await update.message.reply_text("❌ Lỗi.")

async def admin_quan_ly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: 
        await update.message.reply_text("⛔ Không có quyền!", parse_mode="HTML")
        return

    accounts = load_ctv_accounts()
    msg_report = f"👑 <b>QUẢN TRỊ ADMIN</b> 👑\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n👥 Tổng CTV: <b>{len(accounts)}</b>\n\n📊 <b>HIỆU QUẢ:</b>\n"
    total_all = 0
    for ma_ctv in accounts:
        sl, tien = dem_so_khach(ma_ctv)
        total_all += tien
        icon = "🟢" if sl > 0 else "⚪"
        msg_report += f"{icon} <b>{ma_ctv}:</b> {sl} khách | {tien:,} k\n"

    msg_report += f"\n💰 <b>TỔNG DOANH THU: {total_all:,} k</b>\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n➕ Thêm: <code>/themctv user pass</code>\n➖ Xóa: <code>/xoactv user</code>\n👀 Chi tiết: <code>/chitiet user</code>\n📥 Xuất File: <code>/xuatfile</code>"
    await update.message.reply_text(msg_report, parse_mode="HTML")

async def admin_xem_chi_tiet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN_CHINH: return
    try:
        if len(context.args) < 1:
            await update.message.reply_text("⚠️ VD: /chitiet ctv01", parse_mode="HTML")
            return
        target_ctv = context.args[0].strip().lower()
        if not os.path.exists(FILE_DATA_KHACH): return
        
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
        
        if not found_rows: await update.message.reply_text(f"❌ CTV {target_ctv} chưa có khách.", parse_mode="HTML")
        else:
            msg = f"📄 <b>CHI TIẾT: {target_ctv.upper()}</b>\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n" + "\n".join(found_rows[-15:]) + f"\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n💵 <b>TỔNG: {tong_tien_check:,}</b>"
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
    msg = await context.bot.send_message(update.effective_chat.id, "🧹 Đang dọn dẹp...")
    for i in range(1, 21): 
        try: await context.bot.delete_message(update.effective_chat.id, update.message.message_id - i)
        except: pass
    await asyncio.sleep(1)
    try: await context.bot.delete_message(update.effective_chat.id, msg.message_id)
    except: pass

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

    welcome_text = (
        "👋 <b>Xin chào Tân Thủ! Một ngày mới tuyệt vời để bắt đầu tại 78win!!!</b>\n\n"
        "🎉 <b>THƯỞNG CHÀO MỪNG TÂN THỦ</b> đã sẵn sàng.\n"
        "Chỉ cần nạp đầu từ <b>100 điểm</b> liên tiếp là có thể đăng ký khuyến mãi...\n"
        "👉 <a href='https://78max.top'><b>https://78max.top</b></a>"
    )

    if os.path.exists(FILE_BANNER):
        with open(FILE_BANNER, 'rb') as f:
            await update.message.reply_photo(photo=f, caption=welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)

async def command_bao_khach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state', STATE_NORMAL) != STATE_LOGGED_IN:
        await update.message.reply_text("⚠️ Cần đăng nhập CTV!", parse_mode="HTML")
        return
    try:
        parts = update.message.text[3:].strip().split('-')
        if len(parts) < 3: raise ValueError
        ten, ma, tien = parts[0].strip(), parts[1].strip(), parts[2].strip()
        
        current_ctv = context.user_data.get('logged_ctv_code')
        if ma.lower() != current_ctv.lower():
             await update.message.reply_text(f"⚠️ Bạn đang login <b>{current_ctv}</b> nhưng báo cho <b>{ma}</b>!", parse_mode="HTML")
             return
        luu_bao_khach(update.effective_user.id, ten, ma, tien)
        await update.message.reply_text(f"✅ <b>THÀNH CÔNG!</b>\n👤 {ten} | 🆔 {ma} | 💰 {tien}", parse_mode="HTML")
    except: await update.message.reply_text("⚠️ Sai mẫu: <code>/F Tên - Mã - Tiền</code>", parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_state = context.user_data.get('state', STATE_NORMAL)
    
    if text == "🔐 Đăng Nhập CTV (Báo Khách)":
        context.user_data['state'] = STATE_WAITING_ID
        await update.message.reply_text("👤 <b>Nhập ID CTV:</b>", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return

    if user_state == STATE_WAITING_ID:
        accounts = load_ctv_accounts()
        if text in accounts:
            context.user_data['temp_id'] = text
            context.user_data['state'] = STATE_WAITING_PASS
            await update.message.reply_text("🔑 <b>Nhập Mật Khẩu:</b>", parse_mode="HTML")
        else: await update.message.reply_text("❌ ID sai!")
        return

    if user_state == STATE_WAITING_PASS:
        saved_id = context.user_data.get('temp_id')
        accounts = load_ctv_accounts()
        if text == accounts.get(saved_id):
            context.user_data['state'] = STATE_LOGGED_IN
            context.user_data['logged_ctv_code'] = saved_id
            kb = [[KeyboardButton("📊 Xem Thống Kê"), KeyboardButton("📞 Lấy File Đối Soát")], [KeyboardButton("❌ Đăng Xuất")]]
            await update.message.reply_text(f"🎉 <b>LOGIN THÀNH CÔNG: {saved_id}</b>\nBáo khách: <code>/F Tên - {saved_id} - Tiền</code>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        else: await update.message.reply_text("❌ Sai mật khẩu!")
        return

    if user_state == STATE_LOGGED_IN:
        current_ctv = context.user_data.get('logged_ctv_code')
        if text == "❌ Đăng Xuất": await start(update, context); return
        elif text == "📊 Xem Thống Kê":
            sl, tien = dem_so_khach(current_ctv)
            await update.message.reply_text(f"📊 <b>{current_ctv}</b>: {sl} khách | {tien:,} k", parse_mode="HTML")
            return
        elif text == "📞 Lấy File Đối Soát": await update.message.reply_text("📞 LH Admin: @crown66666", parse_mode="HTML"); return
        if not text.startswith('/'): await update.message.reply_text("💡 Dùng lệnh <code>/F ...</code>", parse_mode="HTML"); return

    msg_content = ""
    photo_path = None

    if text == "🍀 Giới Thiệu Group":
        msg_content = "🌿 <b>CỘNG ĐỒNG XÔI MẶN</b>\n👉 <a href='https://t.me/congdongxoiman'>t.me/congdongxoiman</a>"
    elif text == "🎁 Nhận Giftcode":
        msg_content = "🎁 <b>KHO GIFTCODE</b>\n👉 <a href='https://hupcode.xo.je'>hupcode.xo.je</a>"
    elif text == "💰 Ưu Đãi & Khuyến Mãi":
        msg_content = "🧧 <b>KHUYẾN MÃI</b>\n• Nạp đầu 150%\n• Hoàn trả 1.2%..."
    elif text == "🔒 Nạp/Rút USDT An Toàn":
        msg_content = "📥 <b>HƯỚNG DẪN NẠP USDT</b>\n1. Vào Binance -> Gửi\n2. Chọn TRC20\n3. Nhập ví Game\n👉 Admin: @crown66666"
        photo_path = FILE_ANH_NAP
    elif text == "🕵️ Dịch Vụ Thanh Toán Ẩn Danh":
        msg_content = (
            "🛡️ <b>DỊCH VỤ THANH TOÁN ẨN DANH & TIỀN MẶT</b> 🛡️\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "💡 <i>Quý khách thấy bất tiện khi nạp rút bằng tiền ảo USDT? Quý khách muốn bảo mật danh tính tuyệt đối?</i>\n\n"
            "🚀 <b>CHÚNG TÔI CUNG CẤP GIẢI PHÁP:</b>\n"
            "✅ <b>Bảo mật tuyệt đối:</b> Giao dịch qua các kênh thanh toán ẩn danh.\n"
            "✅ <b>Hỗ trợ tiền mặt:</b> Có thể nhận/gửi tiền mặt trực tiếp tại các điểm giao dịch.\n"
            "✅ <b>Chi phí siêu rẻ:</b> Phí dịch vụ chỉ <b>0.1%</b> (cho 1 chiều Nạp hoặc Rút).\n\n"
            "👉 <b>LIÊN HỆ NGAY ADMIN ĐỂ ĐƯỢC HỖ TRỢ:</b>\n"
            "💬 Telegram: <a href='https://t.me/crown66666'><b>@crown66666</b></a>"
        )
    elif text == "🤝 Đăng Ký CTV Ngay":
        msg_content = "🤝 <b>TUYỂN DỤNG CTV</b>\n💰 100k/khách nạp đầu.\n👉 Admin: @crown66666"
    elif text == "👤 Tài Khoản Cá Nhân":
        msg_content = f"👤 ID: <code>{update.effective_user.id}</code>\n@{update.effective_user.username}"
    elif text == "📢 Báo Khách / Hỗ Trợ":
        msg_content = "✅ Đã gửi hỗ trợ."
    else:
        msg_content = "🤔 Chọn menu bên dưới."

    if photo_path and os.path.exists(photo_path):
        with open(photo_path, 'rb') as f:
            await context.bot.send_photo(update.effective_chat.id, photo=f, caption=msg_content, parse_mode="HTML")
    else:
        await context.bot.send_message(update.effective_chat.id, text=msg_content, parse_mode="HTML", disable_web_page_preview=True)

def main():
    keep_alive()
    print("🚀 Bot running...")
    app = ApplicationBuilder().token(TOKEN_BOT).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler(['xoa', 'cls'], clear_chat))
    app.add_handler(CommandHandler(['F', 'f'], command_bao_khach))
    app.add_handler(CommandHandler(['admin', 'quanly'], admin_quan_ly))
    app.add_handler(CommandHandler('themctv', admin_them_ctv))
    app.add_handler(CommandHandler('xoactv', admin_xoa_ctv))
    app.add_handler(CommandHandler('chitiet', admin_xem_chi_tiet))
    app.add_handler(CommandHandler(['xuatfile', 'export'], admin_xuat_file)) # <--- LỆNH MỚI
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
