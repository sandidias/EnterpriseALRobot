import html
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

from tg_bot import SARDEGNA_USERS, WHITELIST_USERS, dispatcher
from tg_bot.modules.helper_funcs.chat_status import (
    bot_admin, can_restrict, connection_status, is_user_admin, user_admin,
    user_admin_no_reply)
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, MessageHandler, CallbackQueryHandler, run_async
from telegram.utils.helpers import mention_html, escape_markdown
from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql
from tg_bot.modules.connection import connected
from tg_bot.modules.helper_funcs.alternate import send_message
FLOOD_GROUP = 3

@connection_status
@run_async
@loggable
def check_flood(bot: Bot, update: Update) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    if not user:  # ignore channels
        return ""

    # ignore admins and whitelists
    if (is_user_admin(chat, user.id) or user.id in WHITELIST_USERS or user.id in SARDEGNA_USERS):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            chat.kick_member(user.id)
            execstrings = ("Banned")
            tag = "BANNED"
        elif getmode == 2:
            chat.kick_member(user.id)
            chat.unban_member(user.id)
            execstrings = ("Ditendang")
            tag = "DITENDANG"
        elif getmode == 3:
            bot.restrict_chat_member(chat.id, user.id, can_send_messages=False)
            execstrings = ("Dibisukan")
            tag = "TERBISU"
        elif getmode == 4:
            bantime = extract_time(msg, getvalue)
            chat.kick_member(user.id, until_date=bantime)
            execstrings = ("Dilarang untuk {}".format(getvalue))
            tag = "TBAN"
        elif getmode == 5:
            mutetime = extract_time(msg, getvalue)
            bot.restrict_chat_member(
                chat.id, user.id, until_date=mutetime, can_send_messages=False
            )
            execstrings = ("Dibisukan untuk {}".format(getvalue))
            tag = "TMUTE"
        send_message(update.effective_message, "Hebat, saya suka meninggalkan flood untuk bencana alam tetapi Anda, "
                       "Anda hanya mengecewakan {}!".format(execstrings))

        return "<b>{}:</b>" \
               "\n#{}" \
               "\n<b>Pengguna:</b> {}" \
               "\nFlooded ini grup.".format(tag, html.escape(chat.title),
                                             mention_html(user.id, user.first_name))

    except BadRequest:
        msg.reply_text("Saya tidak bisa membatasi orang di sini, beri saya izin dulu! Sampai saat itu, saya akan menonaktifkan anti-flood.")
        sql.set_flood(chat.id, 0)
        return "<b>{}:</b>" \
               "\n#INFO" \
               "\nTidak memiliki cukup izin untuk membatasi pengguna jadi nonaktifkan secara otomatisd anti-flood".format(chat.title)

@run_async
@user_admin_no_reply
@bot_admin
def flood_button(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    match = re.match(r"unmute_flooder\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat = update.effective_chat.id
        try:
            bot.restrict_chat_member(chat.id, user.id, can_send_messages=True)
            update.effective_message.edit_text(
                f"Disuarakan oleh {mention_html(user.id, user.first_name)}.",
                parse_mode="HTML")
        except:
            pass


@run_async
@connection_status
@user_admin
@can_restrict
@loggable
def set_flood(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    
    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, "Perintah ini dimaksudkan untuk digunakan dalam grup bukan di PM")
            return ""
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat_id, 0)
            if conn:
                text = message.reply_text("Antiflood telah dinonaktifkan di {}.".format(chat_name))
            else:
                text = message.reply_text("Antiflood telah dinonaktifkan.")
            

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat_id, 0)
                if conn:
                    text = message.reply_text("Antiflood telah dinonaktifkan di {}.".format(chat_name))
                else:
                    text = message.reply_text("Antiflood telah dinonaktifkan.")
                return "<b>{}:</b>" \
                       "\n#SETFLOOD" \
                       "\n<b>Admin:</b> {}" \
                       "\nDisable antiflood.".format(html.escape(chat_name), mention_html(user.id, user.first_name))

            elif amount <= 3:
                send_message(update.effective_message, "Antiflood harus salah satunya 0 (dinonaktifkan) atau angka lebih dari 3!")
                return ""

            else:
                sql.set_flood(chat_id, amount)
                if conn:
                    text = message.reply_text("Anti-flood telah disetel ke {} dalam obrolan: {}".format(amount, chat_name))
                else:
                    text = message.reply_text("Berhasil diperbarui anti-flood batas untuk {}!".format(amount))
                
                return "<b>{}:</b>" \
                       "\n#SETFLOOD" \
                       "\n<b>Admin:</b> {}" \
                       "\nSetel antiflood ke <code>{}</code>.".format(html.escape(chat_name),
                                                                    mention_html(user.id, user.first_name), amount)

        else:
            message.reply_text("Argumen tidak valid, harap gunakan angka, 'off' atau 'no'")
    else:
        message.reply_text(("gunakan `/setflood angka` untuk mengaktifkan anti-flood.\nAtau gunakan `/setflood off` untuk mematikan antiflood!."), parse_mode="markdown")
    return ""


@connection_status
@run_async
def flood(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message

    conn = connected(bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, "Perintah ini dimaksudkan untuk digunakan dalam grup bukan di PM")
            return
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        if conn:
            text = msg.reply_text("Saya tidak memaksakan pengendalian flood apa pun {}!".format(chat_name))
        else:
            text = msg.reply_text("Saya tidak memaksakan pengendalian flood di sini!")
        
    else:
        if conn:
            text = msg.reply_text("Saya saat ini membatasi anggota setelah {} pesan berurutan di {}.".format(limit, chat_name))
        else:
            text = msg.reply_text("Saya saat ini membatasi anggota setelah {} pesan berurutan.".format(limit))
        


@run_async
@user_admin
def set_flood_mode(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    conn = connected(bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(update.effective_message, "Perintah ini dimaksudkan untuk digunakan dalam grup bukan di PM")
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() == 'ban':
            settypeflood = ('ban')
            sql.set_flood_strength(chat_id, 1, "0")
        elif args[0].lower() == 'kick':
            settypeflood = ('kick')
            sql.set_flood_strength(chat_id, 2, "0")
        elif args[0].lower() == 'mute':
            settypeflood = ('mute')
            sql.set_flood_strength(chat_id, 3, "0")
        elif args[0].lower() == 'tban':
            if len(args) == 1:
                teks = update.effective_message, """Sepertinya Anda mencoba menyetel nilai waktu untuk antiflood tetapi Anda tidak menentukan waktu; Coba, `/setfloodmode tban <nilai waktu>`.

Contoh nilai waktu: 4m = 4 menit, 3h = 3 jam, 6d = 6 hari, 5w = 5 minggu."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = ("tban for {}".format(args[1]))
            sql.set_flood_strength(chat_id, 4, str(args[1]))
        elif args[0].lower() == 'tmute':
            if len(args) == 1:
                teks = update.effective_message, """Sepertinya Anda mencoba menyetel nilai waktu untuk antiflood tetapi Anda tidak menentukan waktu; Coba, `/setfloodmode tmute <timevalue>`.

Contoh nilai waktu: 4m = 4 menit, 3h = 3 jam, 6d = 6 hari, 5w = 5 minggu."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = ("tmute for {}".format(args[1]))
            sql.set_flood_strength(chat_id, 5, str(args[1]))
        else:
            send_message(update.effective_message, "Saya hanya mengerti ban/kick/mute/tban/tmute!")
            return
        if conn:
            text = msg.reply_text("Melebihi batas flood yang berurutan akan berakibat {} dalam {}!".format(settypeflood, chat_name))
        else:
            text = msg.reply_text("Melebihi batas flood yang berurutan akan berakibat {}!".format(settypeflood))
        
        return "<b>{}:</b>\n" \
                "<b>Admin:</b> {}\n" \
                "Telah mengubah mode antiflood. Pengguna akan {}.".format(settypeflood, html.escape(chat.title),
                                                                            mention_html(user.id, user.first_name))
    else:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            settypeflood = ('ban')
        elif getmode == 2:
            settypeflood = ('kick')
        elif getmode == 3:
            settypeflood = ('mute')
        elif getmode == 4:
            settypeflood = ('tban for {}'.format(getvalue))
        elif getmode == 5:
            settypeflood = ('tmute for {}'.format(getvalue))
        if conn:
            text = msg.reply_text("Mengirim lebih banyak pesan daripada batas banjir akan mengakibatkan {} dalam {}.".format(settypeflood, chat_name))
        else:
            text = msg.reply_text("Mengirim pesan lebih dari batas banjir akan menghasilkan {}.".format(settypeflood))
        
    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "Tidak memaksakan pengendalian flood."
    else:
        return "Antiflood telah diatur ke`{}`.".format(limit)




__help__ = """
Antiflood memungkinkan Anda mengambil tindakan terhadap pengguna yang mengirim lebih dari x pesan secara berurutan. Melebihi banjir set \
akan mengakibatkan pembatasan pengguna itu.

 Ini akan membisukan pengguna jika mereka mengirim lebih dari 10 pesan berturut-turut, bot diabaikan.
 • `/flood`*:* Dapatkan pengaturan pengendalian banjir saat ini

• *Khusus admin:*
 • `/setflood <int/'no'/'off'>`*:* mengaktifkan atau menonaktifkan pengendalian flood
 *Example:* `/setflood 10`
 • `/setfloodmode <ban/kick/mute/tban/tmute> <value>`*:* Tindakan yang harus dilakukan ketika pengguna telah melebihi batas flood. ban/kick/mute/tmute/tban

• *Catatan:*
 • Nilai harus diisi untuk tban and tmute!!
 Bisa jadi:
 `5m` = 5 menit
 `6h` = 6 jam
 `3d` = 3 hari
 `1w` = 1 minggu
 """

__mod_name__ = "Anti-Flood"

FLOOD_BAN_HANDLER = MessageHandler(
    Filters.all & ~Filters.status_update & Filters.group, check_flood)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, pass_args = True, filters=Filters.group)
SET_FLOOD_MODE_HANDLER = CommandHandler("setfloodmode", set_flood_mode, pass_args = True, filters=Filters.group)
FLOOD_QUERY_HANDLER = CallbackQueryHandler(
    flood_button, pattern=r"unmute_flooder")
FLOOD_HANDLER = CommandHandler("flood", flood, filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(FLOOD_QUERY_HANDLER)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(SET_FLOOD_MODE_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)

__handlers__ = [(FLOOD_BAN_HANDLER, FLOOD_GROUP), SET_FLOOD_HANDLER,
                FLOOD_HANDLER, SET_FLOOD_MODE_HANDLER]
