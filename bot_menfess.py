import os
import html
import time
from datetime import datetime
import pytz
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

# Mengambil data dari Variables di Railway
API_TOKEN = os.environ.get('API_TOKEN', 'ISI_TOKEN_BOT_ANDA')
MOD_GROUP_ID = int(os.environ.get('MOD_GROUP_ID', '-100111111111'))
PUBLIC_GROUP_ID = int(os.environ.get('PUBLIC_GROUP_ID', '-100222222222'))
PUBLIC_GROUP_LINK = os.environ.get('PUBLIC_GROUP_LINK', 'https://t.me/username_grup')
OWNER_ID = int(os.environ.get('OWNER_ID', '123456789'))
CHANNEL_ID = os.environ.get('CHANNEL_ID', '@username_channel')
CHANNEL_LINK = os.environ.get('CHANNEL_LINK', 'https://t.me/username_channel')

bot = telebot.TeleBot(API_TOKEN)
USERS_FILE = "users.txt"

def make_quote(text):
    return f"<blockquote>{text}</blockquote>"

def save_user(user_id):
    user_str = str(user_id)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write(user_str + "\n")
        return
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    if user_str not in users:
        with open(USERS_FILE, "a") as f:
            f.write(user_str + "\n")

def get_all_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def check_membership(user_id):
    if user_id == OWNER_ID:
        return True, True
    
    in_channel = True
    in_group = True
    
    try:
        member_ch = bot.get_chat_member(CHANNEL_ID, user_id)
        in_channel = member_ch.status in ['creator', 'administrator', 'member']
    except Exception:
        in_channel = True

    try:
        member_gr = bot.get_chat_member(PUBLIC_GROUP_ID, user_id)
        in_group = member_gr.status in ['creator', 'administrator', 'member']
    except Exception:
        in_group = True

    return in_channel, in_group

def get_join_markup(in_channel=False, in_group=False):
    markup = InlineKeyboardMarkup(row_width=1)
    if not in_channel:
        markup.add(InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    if not in_group:
        markup.add(InlineKeyboardButton("👥 Join Grup Utama", url=PUBLIC_GROUP_LINK))
    markup.add(InlineKeyboardButton("🔄 Cek Keanggotaan", callback_data="check_sub"))
    return markup

def get_single_channel_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    return markup

def build_post_link(chat_id, message_id):
    try:
        chat_info = bot.get_chat(chat_id)
        if chat_info.username:
            return f"https://t.me/{chat_info.username}/{message_id}"
    except Exception:
        pass
    clean_id = str(chat_id).replace("-100", "")
    return f"https://t.me/c/{clean_id}/{message_id}"

# 0. Command /gcast khusus Owner
@bot.message_handler(commands=['gcast'], func=lambda m: m.from_user.id == OWNER_ID)
def handle_gcast(message):
    if not message.reply_to_message:
        bot.reply_to(
            message,
            make_quote("⚠️ Balas (reply) sebuah pesan, foto, atau video dengan perintah <code>/gcast</code> untuk menyiarkannya ke semua pengguna."),
            parse_mode="HTML"
        )
        return

    users = get_all_users()
    if not users:
        bot.reply_to(message, make_quote("Belum ada data pengguna yang tersimpan."), parse_mode="HTML")
        return

    status_msg = bot.reply_to(
        message,
        make_quote(f"⏳ Memulai siaran (GCAST) ke <b>{len(users)}</b> pengguna..."),
        parse_mode="HTML"
    )

    sukses = 0
    gagal = 0
    for uid in users:
        try:
            bot.copy_message(
                chat_id=int(uid),
                from_chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id
            )
            sukses += 1
            time.sleep(0.05)
        except Exception:
            gagal += 1

    hasil_teks = (
        f"✅ <b>GCAST SELESAI</b>\n"
        f"• <b>Berhasil terkirim:</b> {sukses} pengguna\n"
        f"• <b>Gagal / Blokir bot:</b> {gagal} pengguna"
    )
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        text=make_quote(hasil_teks),
        parse_mode="HTML"
    )

# 1. Pesan Start + Wajib Join Channel & Grup Utama
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == 'private':
        user_id = message.from_user.id
        save_user(user_id)

        if message.from_user.username:
            sapaan = f"@{html.escape(message.from_user.username)}"
        else:
            sapaan = html.escape(message.from_user.first_name or "Kak")

        in_channel, in_group = check_membership(user_id)

        if not in_channel or not in_group:
            teks_wajib = (
                f"Halo {sapaan}, sebelum mengirim menfess, kamu wajib bergabung ke Channel dan Grup Utama kami terlebih dahulu menggunakan tombol di bawah ini.\n\n"
                f"Setelah bergabung, tekan tombol <b>🔄 Cek Keanggotaan</b>."
            )
            bot.reply_to(
                message,
                make_quote(teks_wajib),
                parse_mode="HTML",
                reply_markup=get_join_markup(in_channel, in_group)
            )
            return

        teks = f"Halo {sapaan}, Silahkan drop teks, foto, atau video menfess kamu disini"
        bot.reply_to(
            message,
            make_quote(teks),
            parse_mode="HTML",
            reply_markup=get_single_channel_markup()
        )

# 1b. Tombol Cek Keanggotaan
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def handle_check_subscription(call):
    user_id = call.from_user.id
    save_user(user_id)

    if call.from_user.username:
        sapaan = f"@{html.escape(call.from_user.username)}"
    else:
        sapaan = html.escape(call.from_user.first_name or "Kak")

    in_channel, in_group = check_membership(user_id)

    if not in_channel or not in_group:
        belum = []
        if not in_channel:
            belum.append("Channel")
        if not in_group:
            belum.append("Grup Utama")
        daftar_belum = " & ".join(belum)

        bot.answer_callback_query(
            call.id,
            f"❌ Kamu belum bergabung ke {daftar_belum}! Silakan join dulu lalu klik cek lagi.",
            show_alert=True
        )
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=get_join_markup(in_channel, in_group)
            )
        except Exception:
            pass
    else:
        bot.answer_callback_query(call.id, "✅ Terverifikasi! Kamu sudah bergabung.")
        teks = f"Halo {sapaan}, Silahkan drop teks, foto, atau video menfess kamu disini"
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=make_quote(teks),
            parse_mode="HTML",
            reply_markup=get_single_channel_markup()
        )

# 2. Menangkap menfess dari chat pribadi (private)
@bot.message_handler(content_types=['text', 'photo', 'video'], func=lambda m: m.chat.type == 'private')
def handle_menfess(message):
    user_id = message.from_user.id
    save_user(user_id)

    if message.content_type == 'text' and message.text.startswith('/'):
        return

    in_channel, in_group = check_membership(user_id)
    if not in_channel or not in_group:
        teks_blokir = (
            f"❌ <b>Menfess belum bisa dikirim!</b>\n"
            f"Kamu wajib bergabung ke Channel dan Grup Utama terlebih dahulu menggunakan tombol di bawah ini, lalu tekan <b>🔄 Cek Keanggotaan</b>:"
        )
        bot.reply_to(
            message,
            make_quote(teks_blokir),
            parse_mode="HTML",
            reply_markup=get_join_markup(in_channel, in_group)
        )
        return

    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    full_name = html.escape(f"{first_name} {last_name}".strip())
    username = f"@{html.escape(message.from_user.username)}" if message.from_user.username else "Tidak ada username"

    tz_wib = pytz.timezone('Asia/Jakarta')
    waktu_kirim = datetime.fromtimestamp(message.date, tz_wib).strftime('%d-%m-%Y %H:%M:%S WIB')

    copied_msg = bot.copy_message(
        chat_id=MOD_GROUP_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )

    info_pengirim = make_quote(
        f"📩 <b>DATA PENGIRIM MENFESS</b>\n"
        f"• <b>Nama:</b> {full_name}\n"
        f"• <b>Username:</b> {username}\n"
        f"• <b>ID:</b> <code>{user_id}</code>\n"
        f"• <b>Waktu:</b> {waktu_kirim}"
    )

    markup = InlineKeyboardMarkup(row_width=2)
    btn_approve = InlineKeyboardButton("✅ Post ke Grup", callback_data=f"acc_{copied_msg.message_id}_{user_id}")
    btn_reject = InlineKeyboardButton("❌ Tolak", callback_data=f"rej_{copied_msg.message_id}_{user_id}")
    btn_reply = InlineKeyboardButton("💬 Reply Pengirim", callback_data=f"rep_{copied_msg.message_id}_{user_id}")
    markup.add(btn_approve, btn_reject)
    markup.add(btn_reply)

    bot.send_message(
        chat_id=MOD_GROUP_ID,
        text=info_pengirim,
        reply_to_message_id=copied_msg.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

    bot.reply_to(
        message,
        make_quote("Menfess kamu sudah masuk ke antrean admin!"),
        parse_mode="HTML",
        reply_markup=get_single_channel_markup()
    )

# 3. Menangani klik tombol ACC, Tolak, dan Reply di Grup PV
@bot.callback_query_handler(func=lambda call: call.message.chat.id == MOD_GROUP_ID)
def handle_moderation(call):
    admin_name = html.escape(call.from_user.first_name)
    parts = call.data.split("_")
    action = parts[0]
    target_msg_id = int(parts[1])
    sender_user_id = int(parts[2])

    old_text_escaped = html.escape(call.message.text)

    if action == "acc":
        try:
            posted_msg = bot.copy_message(
                chat_id=PUBLIC_GROUP_ID,
                from_chat_id=MOD_GROUP_ID,
                message_id=target_msg_id
            )
            
            try:
                bot.pin_chat_message(
                    chat_id=PUBLIC_GROUP_ID,
                    message_id=posted_msg.message_id,
                    disable_notification=True
                )
                status_pin = "(Berhasil di-post & disematkan)"
            except Exception:
                status_pin = "(Berhasil di-post, gagal pin — cek izin Pin Messages bot)"

            # Membuat link postingan & mengirim notifikasi ke pengirim asli
            post_link = build_post_link(PUBLIC_GROUP_ID, posted_msg.message_id)
            try:
                notif_markup = InlineKeyboardMarkup(row_width=1)
                notif_markup.add(InlineKeyboardButton("🔗 Lihat Postingan Menfess", url=post_link))
                teks_notif = (
                    f"✅ <b>Menfess kamu telah di-ACC oleh admin!</b>\n"
                    f"Lihat postinganmu di grup utama melalui tombol di bawah ini atau salin link berikut:\n"
                    f"<code>{post_link}</code>"
                )
                bot.send_message(
                    chat_id=sender_user_id,
                    text=make_quote(teks_notif),
                    parse_mode="HTML",
                    reply_markup=notif_markup
                )
            except Exception:
                pass

            new_text = make_quote(f"{old_text_escaped}\n\n✅ <b>Status:</b> Di-ACC oleh {admin_name} {status_pin}")
            bot.edit_message_text(
                chat_id=MOD_GROUP_ID,
                message_id=call.message.message_id,
                text=new_text,
                parse_mode="HTML",
                reply_markup=None
            )
            bot.answer_callback_query(call.id, "Berhasil diposting, disematkan & link dikirim ke pengirim!")
        except Exception:
            bot.answer_callback_query(call.id, "Gagal memposting. Pastikan bot admin di grup utama.", show_alert=True)

    elif action == "rej":
        new_text = make_quote(f"{old_text_escaped}\n\n❌ <b>Status:</b> Ditolak oleh {admin_name}")
        bot.edit_message_text(
            chat_id=MOD_GROUP_ID,
            message_id=call.message.message_id,
            text=new_text,
            parse_mode="HTML",
            reply_markup=None
        )
        bot.answer_callback_query(call.id, "Menfess ditolak.")

    elif action == "rep":
        prompt_text = make_quote(
            f"✍️ Ketik balasan Anda untuk ID <code>{sender_user_id}</code> (bisa berupa teks, foto, atau video):"
        )
        bot.send_message(
            chat_id=MOD_GROUP_ID,
            text=prompt_text,
            reply_to_message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=ForceReply(selective=True)
        )
        bot.answer_callback_query(call.id, "Silakan ketik balasan Anda.")

# 4. Menangkap balasan dari admin di Grup PV dan mengirimkannya ke pengirim asli
@bot.message_handler(
    content_types=['text', 'photo', 'video'],
    func=lambda m: m.chat.type in ['group', 'supergroup'] and m.chat.id == MOD_GROUP_ID and m.reply_to_message is not None
)
def handle_admin_reply(message):
    replied = message.reply_to_message
    if replied.from_user.id == bot.get_me().id and "Ketik balasan Anda untuk ID" in (replied.text or ""):
        try:
            target_id_str = replied.text.split("untuk ID ")[1].split(" ")[0]
            target_user_id = int(target_id_str)

            if message.content_type == 'text':
                teks_balasan = make_quote(f"💬 <b>Balasan Admin:</b>\n{html.escape(message.text)}")
                bot.send_message(target_user_id, teks_balasan, parse_mode="HTML")
            elif message.content_type == 'photo':
                caption_balasan = make_quote(f"💬 <b>Balasan Admin:</b>\n{html.escape(message.caption or '')}")
                bot.send_photo(target_user_id, message.photo[-1].file_id, caption=caption_balasan, parse_mode="HTML")
            elif message.content_type == 'video':
                caption_balasan = make_quote(f"💬 <b>Balasan Admin:</b>\n{html.escape(message.caption or '')}")
                bot.send_video(target_user_id, message.video.file_id, caption=caption_balasan, parse_mode="HTML")

            bot.reply_to(
                message,
                make_quote("✅ Balasan berhasil dikirim ke pengirim."),
                parse_mode="HTML"
            )
        except Exception:
            bot.reply_to(
                message,
                make_quote("❌ Gagal mengirim balasan (pengirim mungkin telah memblokir bot)."),
                parse_mode="HTML"
            )

print("Bot menfess v3 (Dual Force-Sub & Auto-Link ACC) berjalan...")
bot.infinity_polling()
