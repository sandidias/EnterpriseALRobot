import html
import re
from typing import List

from telegram import Bot, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async

import tg_bot.modules.sql.blacklist_sql as sql
from tg_bot import dispatcher, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import (
    user_admin,
    user_not_admin,
    connection_status,
)
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.misc import split_message

BLACKLIST_GROUP = 11


@run_async
@connection_status
def blacklist(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message
    chat = update.effective_chat

    update_chat_title = chat.title
    message_chat_title = update.effective_message.chat.title

    if update_chat_title == message_chat_title:
        base_blacklist_string = "Current <b>blacklisted</b> words:\n"
    else:
        base_blacklist_string = (
            f"Current <b>blacklisted</b> words in <b>{update_chat_title}</b>:\n"
        )

    all_blacklisted = sql.get_chat_blacklist(chat.id)

    filter_list = base_blacklist_string

    if len(args) > 0 and args[0].lower() == "copy":
        for trigger in all_blacklisted:
            filter_list += f"<code>{html.escape(trigger)}</code>\n"
    else:
        for trigger in all_blacklisted:
            filter_list += f" - <code>{html.escape(trigger)}</code>\n"

    split_text = split_message(filter_list)
    for text in split_text:
        if text == base_blacklist_string:
            if update_chat_title == message_chat_title:
                msg.reply_text("Tidak ada pesan yang masuk daftar hitam di sini!")
            else:
                msg.reply_text(
                    f"Tidak ada pesan dalam daftar hitam <b>{update_chat_title}</b>!",
                    parse_mode=ParseMode.HTML,
                )
            return
        msg.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
@connection_status
@user_admin
def add_blacklist(bot: Bot, update: Update):
    msg = update.effective_message
    chat = update.effective_chat
    words = msg.text.split(None, 1)

    if len(words) > 1:
        text = words[1]
        to_blacklist = list(
            set(trigger.strip() for trigger in text.split("\n") if trigger.strip())
        )

        for trigger in to_blacklist:
            sql.add_to_blacklist(chat.id, trigger.lower())

        if len(to_blacklist) == 1:
            msg.reply_text(
                f"Ditambahkan <code>{html.escape(to_blacklist[0])}</code> ke daftar hitam!",
                parse_mode=ParseMode.HTML,
            )

        else:
            msg.reply_text(
                f"Ditambahkan <code>{len(to_blacklist)}</code> pemicu ke daftar hitam.",
                parse_mode=ParseMode.HTML,
            )

    else:
        msg.reply_text(
            "Beri tahu saya kata-kata yang ingin Anda hapus dari daftar hitam."
        )


@run_async
@connection_status
@user_admin
def unblacklist(bot: Bot, update: Update):
    msg = update.effective_message
    chat = update.effective_chat
    words = msg.text.split(None, 1)

    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(
            set(trigger.strip() for trigger in text.split("\n") if trigger.strip())
        )
        successful = 0

        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat.id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                msg.reply_text(
                    f"Dihapus <code>{html.escape(to_unblacklist[0])}</code> dari daftar hitam!",
                    parse_mode=ParseMode.HTML,
                )
            else:
                msg.reply_text("Ini bukan pemicu yang masuk daftar hitam...!")

        elif successful == len(to_unblacklist):
            msg.reply_text(
                f"Dihapus <code>{successful}</code> pemicu dari daftar hitam.",
                parse_mode=ParseMode.HTML,
            )

        elif not successful:
            msg.reply_text(
                "Tidak satu pun dari pemicu ini ada, jadi tidak dihapus.",
                parse_mode=ParseMode.HTML,
            )

        else:
            msg.reply_text(
                f"Dihapus <code>{successful}</code> pemicu dari daftar hitam."
                f" {len(to_unblacklist) - successful} tidak ada, jadi tidak dihapus.",
                parse_mode=ParseMode.HTML,
            )
    else:
        msg.reply_text(
            "Beri tahu saya kata-kata yang ingin Anda hapus dari daftar hitam."
        )


@run_async
@connection_status
@user_not_admin
def del_blacklist(bot: Bot, update: Update):
    chat = update.effective_chat
    message = update.effective_message
    to_match = extract_text(message)

    if not to_match:
        return

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Pesan untuk dihapus tidak ditemukan":
                    pass
                else:
                    LOGGER.exception("Kesalahan saat menghapus pesan daftar hitam.")
            break


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "There are {} blacklisted words.".format(blacklisted)


def __stats__():
    return "{} blacklist triggers, across {} chats.".format(
        sql.num_blacklist_filters(), sql.num_blacklist_filter_chats()
    )


__help__ = """
Daftar hitam digunakan untuk menghentikan pemicu tertentu diucapkan dalam kelompok. Setiap kali pemicu disebutkan, \
pesan tersebut akan segera dihapus. Kombo yang bagus terkadang memasangkan ini dengan filter peringatan!

*NOTE:* daftar hitam tidak mempengaruhi admin grup

 - /blacklist: Lihat kata-kata dalam daftar hitam saat ini.

*Hanya Admin:*
 - /addblacklist <triggers>: Tambahkan pemicu ke daftar hitam. Setiap baris dianggap satu pemicu, jadi menggunakan yang berbeda\
baris akan memungkinkan Anda menambahkan beberapa pemicu.
 - /unblacklist <triggers>: Hapus pemicu dari daftar hitam. Logika baris baru yang sama berlaku di sini, jadi Anda bisa menghapus \
beberapa pemicu sekaligus.
 - /rmblacklist <triggers>: Sama seperti di atas.
"""

BLACKLIST_HANDLER = DisableAbleCommandHandler(
    "blacklist", blacklist, pass_args=True, admin_ok=True
)
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist)
UNBLACKLIST_HANDLER = CommandHandler(["unblacklist", "rmblacklist"], unblacklist)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.group,
    del_blacklist,
    edited_updates=True,
)
dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)

__mod_name__ = "Word Blacklists"
__handlers__ = [
    BLACKLIST_HANDLER,
    ADD_BLACKLIST_HANDLER,
    UNBLACKLIST_HANDLER,
    (BLACKLIST_DEL_HANDLER, BLACKLIST_GROUP),
]
