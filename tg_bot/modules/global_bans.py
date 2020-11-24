import html
import time
from datetime import datetime
from io import BytesIO
from typing import List

from telegram import Bot, Update, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.global_bans_sql as sql
from tg_bot import (
    dispatcher,
    OWNER_ID,
    SUDO_USERS,
    DEV_USERS,
    SUPPORT_USERS,
    SARDEGNA_USERS,
    WHITELIST_USERS,
    STRICT_GBAN,
    GBAN_LOGS,
    sw,
)
from tg_bot.modules.helper_funcs.chat_status import (
    user_admin,
    is_user_admin,
    support_plus,
)
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "Pengguna adalah administrator obrolan",
    "Obrolan tidak ditemukan",
    "Tidak cukup hak untuk membatasi/tidak membatasi anggota obrolan",
    "Peserta_pengguna",
    "Peer_id_invalid",
    "Obrolan grup telah dinonaktifkan",
    "Perlu mengundang pengguna untuk menendang dari grup dasar",
    "Chat_admin_required",
    "Hanya pembuat grup dasar yang dapat menendang administrator grup",
    "Channel_private",
    "Tidak dalam obrolan",
    "Tidak dapat menghapus pemilik obrolan",
}

UNGBAN_ERRORS = {
    "Pengguna adalah administrator obrolan",
    "Obrolan tidak ditemukan",
    "Tidak cukup hak untuk membatasi/tidak membatasi anggota obrolan",
    "User_not_participant",
    "Metode hanya tersedia untuk obrolan grup super dan saluran",
    "Tidak dalam obrolan",
    "Channel_private",
    "Chat_admin_required",
    "Peer_id_invalid",
    "Pengguna tidak ditemukan",
}


@run_async
@support_plus
def gban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return

    if int(user_id) in DEV_USERS:
        message.reply_text(
            "Pengguna itu adalah bagian dari Serikat\nSaya tidak bisa bertindak melawan kita sendiri."
        )
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text(
            "Aku memata-matai, dengan mata kecilku ...! Mengapa kalian saling menyerang?"
        )
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text(
            "OOOH seseorang mencoba memberi Negara Sakura! *meraih popcorn*"
        )
        return

    if int(user_id) in SARDEGNA_USERS:
        message.reply_text("Itu Sardegna! Mereka tidak bisa dilarang!")
        return

    if int(user_id) in WHITELIST_USERS:
        message.reply_text("Itu adalah Neptunia! Mereka tidak bisa dilarang!")
        return
    
    if int(user_id) in (777000, 1087968824):
        message.reply_text("Hah, kenapa saya gban Telegram bot?")
        return
    
    if user_id == bot.id:
        message.reply_text("Kamu uhh ... ingin aku bunuh diri?")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message == "Pengguna tidak ditemukan":
            message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
            return ""
        else:
            return

    if user_chat.type != "private":
        message.reply_text("Itu bukan pengguna!")
        return

    if sql.is_user_gbanned(user_id):

        if not reason:
            message.reply_text(
                "Pengguna ini sudah diblokir; Saya akan mengubah alasannya, tetapi Anda belum memberi saya satu pun..."
            )
            return

        old_reason = sql.update_gban_reason(
            user_id, user_chat.username or user_chat.first_name, reason
        )
        if old_reason:
            message.reply_text(
                "Pengguna ini sudah diblokir, karena alasan berikut:\n"
                "<code>{}</code>\n"
                "Saya telah pergi dan memperbaruinya dengan alasan baru Anda!".format(
                    html.escape(old_reason)
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            message.reply_text(
                "Pengguna ini sudah diblokir, tetapi tidak ada alasan yang ditetapkan; Saya telah pergi dan memperbaruinya!"
            )

        return

    message.reply_text("On it!")

    start_time = time.time()
    datetime_fmt = "%H:%M - %d-%m-%Y"
    current_time = datetime.utcnow().strftime(datetime_fmt)

    if chat.type != "private":
        chat_origin = "<b>{} ({})</b>\n".format(html.escape(chat.title), chat.id)
    else:
        chat_origin = "<b>{}</b>\n".format(chat.id)

    log_message = (
        f"#GBANNED\n"
        f"<b>Berasal dari:</b> {chat_origin}\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna yang Dilarang:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
        f"<b>ID Pengguna yang Dilarang:</b> {user_chat.id}\n"
        f"<b>Event Stamp:</b> {current_time}"
    )

    if reason:
        if chat.type == chat.SUPERGROUP and chat.username:
            log_message += f'\n<b>Alasan:</b> <a href="http://telegram.me/{chat.username}/{message.message_id}">{reason}</a>'
        else:
            log_message += f"\n<b>Alasan:</b> {reason}"

    if GBAN_LOGS:
        try:
            log = bot.send_message(GBAN_LOGS, log_message, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            log = bot.send_message(
                GBAN_LOGS,
                log_message
                + "\n\nPemformatan telah dinonaktifkan karena kesalahan yang tidak terduga.",
            )

    else:
        send_to_list(bot, SUDO_USERS + SUPPORT_USERS, log_message, html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    gbanned_chats = 0

    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.kick_chat_member(chat_id, user_id)
            gbanned_chats += 1

        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text(f"Tidak bisa memberi karena: {excp.message}")
                if GBAN_LOGS:
                    bot.send_message(
                        GBAN_LOGS,
                        f"Tidak bisa memberi karena {excp.message}",
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    send_to_list(
                        bot,
                        SUDO_USERS + SUPPORT_USERS,
                        f"Tidak bisa memberi karena: {excp.message}",
                    )
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    if GBAN_LOGS:
        log.edit_text(
            log_message + f"\n<b>Obrolan terpengaruh:</b> {gbanned_chats}",
            parse_mode=ParseMode.HTML,
        )
    else:
        send_to_list(
            bot,
            SUDO_USERS + SUPPORT_USERS,
            f"Gban selesai! (Pengguna dilarang masuk {gbanned_chats} obrolan)",
        )

    end_time = time.time()
    gban_time = round((end_time - start_time), 2)

    if gban_time > 60:
        gban_time = round((gban_time / 60), 2)
        message.reply_text(
            f"Selesai! Gban ini terpengaruh {gbanned_chats} obrolan, Lihat {gban_time} menit"
        )
    else:
        message.reply_text(
            f"Selesai! Gban ini terpengaruh {gbanned_chats} obrolan, Lihat {gban_time} detik"
        )

    try:
        bot.send_message(
            user_id,
            "Anda telah diblokir secara global dari semua grup di mana saya memiliki izin administratif."
            "Jika menurut Anda ini adalah kesalahan, Anda dapat mengajukan banding di master saya.",
            parse_mode=ParseMode.HTML,
        )
    except:
        pass  # bot probably blocked by user


@run_async
@support_plus
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != "private":
        message.reply_text("Itu bukan pengguna!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("Pengguna ini tidak dilarang!")
        return

    message.reply_text(f"Saya akan memberi {user_chat.first_name} kesempatan kedua, secara global.")

    start_time = time.time()
    datetime_fmt = "%H:%M - %d-%m-%Y"
    current_time = datetime.utcnow().strftime(datetime_fmt)

    if chat.type != "private":
        chat_origin = f"<b>{html.escape(chat.title)} ({chat.id})</b>\n"
    else:
        chat_origin = f"<b>{chat.id}</b>\n"

    log_message = (
        f"#UNGBANNED\n"
        f"<b>Berasal dari:</b> {chat_origin}\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna yang Tidak Dicekal:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
        f"<b>ID Pengguna yang Tidak Dicekal:</b> {user_chat.id}\n"
        f"<b>Event Stamp:</b> {current_time}"
    )

    if GBAN_LOGS:
        try:
            log = bot.send_message(GBAN_LOGS, log_message, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            log = bot.send_message(
                GBAN_LOGS,
                log_message
                + "\n\nPemformatan telah dinonaktifkan karena kesalahan yang tidak terduga.",
            )
    else:
        send_to_list(bot, SUDO_USERS + SUPPORT_USERS, log_message, html=True)

    chats = get_all_chats()
    ungbanned_chats = 0

    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == "kicked":
                bot.unban_chat_member(chat_id, user_id)
                ungbanned_chats += 1

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text(f"Tidak dapat membatalkan gban karena: {excp.message}")
                if GBAN_LOGS:
                    bot.send_message(
                        GBAN_LOGS,
                        f"Tidak dapat membatalkan gban karena: {excp.message}",
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    bot.send_message(
                        OWNER_ID, f"Tidak dapat membatalkan gban karena: {excp.message}"
                    )
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    if GBAN_LOGS:
        log.edit_text(
            log_message + f"\n<b>Obrolan terpengaruh:</b> {ungbanned_chats}",
            parse_mode=ParseMode.HTML,
        )
    else:
        send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "un-gban selesai!")

    end_time = time.time()
    ungban_time = round((end_time - start_time), 2)

    if ungban_time > 60:
        ungban_time = round((ungban_time / 60), 2)
        message.reply_text(f"Blokir orang telah dibatalkan. Lihat {ungban_time} menit")
    else:
        message.reply_text(f"Blokir orang telah dibatalkan. Lihat {ungban_time} detik")


@run_async
@support_plus
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text(
            "Tidak ada pengguna yang dilarang! Anda lebih baik dari yang saya harapkan..."
        )
        return

    banfile = "Persetan dengan orang-orang ini.\n"
    for user in banned_users:
        banfile += f"[x] {user['name']} - {user['user_id']}\n"
        if user["reason"]:
            banfile += f"Alasan: {user['reason']}\n"

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="gbanlist.txt",
            caption="Berikut adalah daftar pengguna yang diblokir saat ini.",
        )


def check_and_ban(update, user_id, should_message=True):

    chat = update.effective_chat  # type: Optional[Chat]
    sw_ban = sw.get_ban(int(user_id))
    if sw_ban:
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_markdown(
                "**Pengguna ini terdeteksi sebagai bot spam oleh SpamWatch dan telah dihapus!**"
            )
            return
        else:
            return

    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_text(
                "Peringatan: Pengguna ini diblokir secara global.\n"
                "*melarang mereka dari sini*.\n"
                "Appeal chat: PM My Master"
            )


@run_async
def enforce_gban(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if (
        sql.does_chat_gban(update.effective_chat.id)
        and update.effective_chat.get_member(bot.id).can_restrict_members
    ):
        user = update.effective_user
        chat = update.effective_chat
        msg = update.effective_message

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
def gbanstat(bot: Bot, update: Update, args: List[str]):
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "Saya telah mengaktifkan gbans di grup ini. Ini akan membantu melindungi Anda "
                "dari spammer, karakter yang tidak menyenangkan, dan troll terbesar."
            )
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "Saya telah menonaktifkan gban di grup ini. GBans tidak akan mempengaruhi pengguna Anda "
                "lagi. Anda akan kurang terlindungi dari troll dan spammer "
                "bagaimanapun juga!"
            )
    else:
        update.effective_message.reply_text(
            "Beri saya beberapa argumen untuk memilih pengaturan! on/off, yes/no!\n\n"
            "Pengaturan Anda saat ini adalah: {}\n"
            "Saat True, semua gbans yang terjadi juga akan terjadi di grup Anda. "
            "Ketika Salah, mereka tidak akan melakukannya, meninggalkan Anda dengan kemungkinan belas kasihan "
            "si pengirim spam.".format(sql.does_chat_gban(update.effective_chat.id))
        )


def __stats__():
    return f"{sql.num_gbanned_users()} gbanned users."


def __user_info__(user_id):
    if user_id in (777000, 1087968824):
        return ""


    is_gbanned = sql.is_user_gbanned(user_id)

    text = "Dilarang secara globa: <b>{}</b>"
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += f"\n<b>Alasan:</b> {html.escape(user.reason)}"
        text += "\n<b>Appeal Chat:</b> PM My Master"
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return f"Obrolan ini berlaku *gbans*: `{sql.does_chat_gban(chat_id)}`."


__help__ = """
*Admin saja:*
 - /gbanstat <on/off/yes/no>: Akan menonaktifkan efek larangan global pada grup Anda, atau mengembalikan pengaturan Anda saat ini.

Gbans, juga dikenal sebagai larangan global, digunakan oleh pemilik bot untuk melarang pelaku spam di semua grup. Ini membantu melindungi \
Anda dan grup Anda dengan menghapus pembanjir spam secepat mungkin. Mereka dapat dinonaktifkan untuk grup Anda dengan menelepon \
/gbanstat
Catatan: Anda dapat mengajukan banding gbans atau bertanya pada gbans di My Master

Saya juga mengintegrasikan API @Spamwatch ke dalam gbans untuk menghapus Spammer sebanyak mungkin dari ruang obrolan Anda!
*Apa itu SpamWatch?*
SpamWatch mempertahankan daftar larangan besar yang terus diperbarui dari robot spam, troll, pengirim spam bitcoin, dan karakter yang tidak menyenangkan[.](https://telegra.ph/file/ac12a2c6b831dd005015b.jpg)
Saya akan terus membantu melarang spammer keluar dari grup Anda secara otomatis. Jadi, Anda tidak perlu khawatir spammer menyerbu grup Anda.
"""

GBAN_HANDLER = CommandHandler("gban", gban, pass_args=True)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, pass_args=True)
GBAN_LIST = CommandHandler("gbanlist", gbanlist)

GBAN_STATUS = CommandHandler(
    "gbanstat", gbanstat, pass_args=True, filters=Filters.group
)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

__mod_name__ = "Global Bans"
__handlers__ = [GBAN_HANDLER, UNGBAN_HANDLER, GBAN_LIST, GBAN_STATUS]

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
    __handlers__.append((GBAN_ENFORCER, GBAN_ENFORCE_GROUP))
