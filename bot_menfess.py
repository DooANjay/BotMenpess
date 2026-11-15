import os
import html
from datetime import datetime
import pytz
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

# Mengambil data dari Variables di Railway
API_TOKEN = os.environ.get('API_TOKEN', 'ISI_TOKEN_BOT_ANDA')
MOD_GROUP_ID = int(os.environ.get('MOD_GROUP_ID', '-100111111111'))
PUBLIC_GROUP_ID = int(os.environ.get('PUBLIC_GROUP_ID', '-100222222222'))

bot = telebot.TeleBot(API_TOKEN)

def make_quote(text):
    return f"<blockquote>{text}</blockquote>"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == 'private':
        # Mengambil @username pengirim, jika tidak punya username akan memakai nama depan
        if message.from_user.username:
            sapaan = f"@{html.escape(message.from_user.username)}"
        else:
            sapaan = html.escape(message.from_user.first_name or "Kak")

        teks = f"Halo {sapaan}, Silahkan drop teks, foto, atau video menfess kamu disini"
        bot.reply_to(message, make_quote(teks), parse_mode="HTML")

# 1. Menangkap menfess dari chat pribadi (private)
@bot.message_handler(content_types=['text', 'photo', 'video'], func=lambda m: m.chat.type == 'private')
def handle_menfess(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    full_name = html.escape(f"{first_name} {last_name}".strip())
    username = f"@{html.escape(message.from_user.username)}" if message.from_user.username else "Tidak ada username"

    tz_wib = pytz.timezone('Asia/Jakarta')
    waktu_kirim = datetime.fromtimestamp(message.date, tz_wib).strftime('%d-%m-%Y %H:%M:%S WIB')

    # Menyalin pesan/video ASLI ke Grup PV (tetap tersimpan di grup PV)
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
        parse_mode="HTML"
    )

# 2. Menangani klik tombol ACC, Tolak, dan Reply di Grup PV
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
            # Meneruskan HANYA pesan/video asli ke Grup Utama
            posted_msg = bot.copy_message(
                chat_id=PUBLIC_GROUP_ID,
                from_chat_id=MOD_GROUP_ID,
                message_id=target_msg_id
            )
            
            # Langsung menyematkan (PIN) pesan menfess di Grup Utama
            try:
                bot.pin_chat_message(
                    chat_id=PUBLIC_GROUP_ID,
                    message_id=posted_msg.message_id,
                    disable_notification=True
                )
                status_pin = "(Berhasil di-post & disematkan)"
            except Exception:
                status_pin = "(Berhasil di-post, gagal pin — cek izin Pin Messages bot)"

            new_text = make_quote(f"{old_text_escaped}\n\n✅ <b>Status:</b> Di-ACC oleh {admin_name} {status_pin}")
            bot.edit_message_text(
                chat_id=MOD_GROUP_ID,
                message_id=call.message.message_id,
                text=new_text,
                parse_mode="HTML",
                reply_markup=None
            )
            bot.answer_callback_query(call.id, "Berhasil diposting & disematkan!")
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

# 3. Menangkap balasan dari admin di Grup PV dan mengirimkannya ke pengirim asli
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

print("Bot menfess berjalan...")
bot.infinity_polling()

