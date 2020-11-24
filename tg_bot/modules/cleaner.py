import html

from typing import List

from telegram import Bot, Update, ParseMode
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async

from tg_bot import ALLOW_EXCL, dispatcher, CustomCommandHandler
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import (
    user_admin,
    bot_can_delete,
    dev_plus,
    connection_status,
)
from tg_bot.modules.sql import cleaner_sql as sql

if ALLOW_EXCL:
    CMD_STARTERS = ("/", "!")
else:
    CMD_STARTERS = "/"

BLUE_TEXT_CLEAN_GROUP = 15
CommandHandlerList = (CommandHandler, CustomCommandHandler, DisableAbleCommandHandler)
command_list = [
    "cleanbluetext",
    "ignorecleanbluetext",
    "unignorecleanbluetext",
    "listcleanbluetext",
    "ignoreglobalcleanbluetext",
    "unignoreglobalcleanbluetext" "start",
    "help",
    "settings",
    "donate",
]

for handler_list in dispatcher.handlers:
    for handler in dispatcher.handlers[handler_list]:
        if any(isinstance(handler, cmd_handler) for cmd_handler in CommandHandlerList):
            command_list += handler.command


@run_async
def clean_blue_text_must_click(bot: Bot, update: Update):

    chat = update.effective_chat
    message = update.effective_message

    if chat.get_member(bot.id).can_delete_messages:
        if sql.is_enabled(chat.id):
            fst_word = message.text.strip().split(None, 1)[0]

            if len(fst_word) > 1 and any(
                fst_word.startswith(start) for start in CMD_STARTERS
            ):

                command = fst_word[1:].split("@")
                chat = update.effective_chat

                ignored = sql.is_command_ignored(chat.id, command[0])
                if ignored:
                    return

                if command[0] not in command_list:
                    message.delete()


@run_async
@connection_status
@bot_can_delete
@user_admin
def set_blue_text_must_click(bot: Bot, update: Update, args: List[str]):

    chat = update.effective_chat
    message = update.effective_message

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no":
            sql.set_cleanbt(chat.id, False)
            reply = "Pembersihan bluetext telah dinonaktifkan untuk <b>{}</b>".format(
                html.escape(chat.title)
            )
            message.reply_text(reply, parse_mode=ParseMode.HTML)

        elif val == "yes" or val == "on":
            sql.set_cleanbt(chat.id, True)
            reply = "Pembersihan Bluetext telah diaktifkan untuk <b>{}</b>".format(
                html.escape(chat.title)
            )
            message.reply_text(reply, parse_mode=ParseMode.HTML)

        else:
            reply = "Argumen tidak valid. Nilai yang diterima adalah 'yes', 'on', 'no', 'off'"
            message.reply_text(reply)
    else:
        clean_status = sql.is_enabled(chat.id)
        if clean_status:
            clean_status = "Enabled"
        else:
            clean_status = "Disabled"
        reply = "Pembersihan teks teks untuk file <b>{}</b> : <b>{}</b>".format(
            chat.title, clean_status
        )
        message.reply_text(reply, parse_mode=ParseMode.HTML)


@run_async
@user_admin
def add_bluetext_ignore(bot: Bot, update: Update, args: List[str]):

    message = update.effective_message
    chat = update.effective_chat

    if len(args) >= 1:
        val = args[0].lower()
        added = sql.chat_ignore_command(chat.id, val)
        if added:
            reply = "<b>{}</b> telah ditambahkan ke daftar abaikan pembersih bluetext.".format(
                args[0]
            )
        else:
            reply = "Perintah sudah diabaikan."
        message.reply_text(reply, parse_mode=ParseMode.HTML)

    else:
        reply = "Tidak ada perintah yang diberikan untuk diabaikan."
        message.reply_text(reply)


@run_async
@user_admin
def remove_bluetext_ignore(bot: Bot, update: Update, args: List[str]):

    message = update.effective_message
    chat = update.effective_chat

    if len(args) >= 1:
        val = args[0].lower()
        removed = sql.chat_unignore_command(chat.id, val)
        if removed:
            reply = "<b>{}</b> telah dihapus dari daftar abaikan pembersih bluetext.".format(
                args[0]
            )
        else:
            reply = "Perintah tidak diabaikan saat ini."
        message.reply_text(reply, parse_mode=ParseMode.HTML)

    else:
        reply = "Tidak ada perintah yang diberikan untuk diabaikan."
        message.reply_text(reply)


@run_async
@user_admin
def add_bluetext_ignore_global(bot: Bot, update: Update, args: List[str]):

    message = update.effective_message

    if len(args) >= 1:
        val = args[0].lower()
        added = sql.global_ignore_command(val)
        if added:
            reply = "<b>{}</b> telah ditambahkan ke daftar abaikan pembersih bluetext global.".format(
                args[0]
            )
        else:
            reply = "Perintah sudah diabaikan."
        message.reply_text(reply, parse_mode=ParseMode.HTML)

    else:
        reply = "Tidak ada perintah yang diberikan untuk diabaikan."
        message.reply_text(reply)


@run_async
@dev_plus
def remove_bluetext_ignore_global(bot: Bot, update: Update, args: List[str]):

    message = update.effective_message

    if len(args) >= 1:
        val = args[0].lower()
        removed = sql.global_unignore_command(val)
        if removed:
            reply = "<b>{}</b> telah dihapus dari daftar abaikan pembersih bluetext global.".format(
                args[0]
            )
        else:
            reply = "Perintah tidak diabaikan saat ini."
        message.reply_text(reply, parse_mode=ParseMode.HTML)

    else:
        reply = "Tidak ada perintah yang diberikan untuk diabaikan."
        message.reply_text(reply)


@run_async
@dev_plus
def bluetext_ignore_list(bot: Bot, update: Update):

    message = update.effective_message
    chat = update.effective_chat

    global_ignored_list, local_ignore_list = sql.get_all_ignored(chat.id)
    text = ""

    if global_ignored_list:
        text = "Perintah berikut saat ini diabaikan secara global dari pembersihan bluetext :\n"

        for x in global_ignored_list:
            text += f" - <code>{x}</code>\n"

    if local_ignore_list:
        text += "\nPerintah berikut saat ini diabaikan secara lokal dari pembersihan bluetext :\n"

        for x in local_ignore_list:
            text += f" - <code>{x}</code>\n"

    if text == "":
        text = "Saat ini tidak ada perintah yang diabaikan dari pembersihan bluetext."
        message.reply_text(text)
        return

    message.reply_text(text, parse_mode=ParseMode.HTML)
    return


__help__ = """
 - /cleanbluetext <on/off/yes/no> - perintah bersih setelah mengirim
 - /ignorecleanbluetext <word> - mencegah pembersihan otomatis perintah
 - /unignorecleanbluetext <word> - hapus mencegah pembersihan otomatis dari perintah
 - /listcleanbluetext - daftar perintah yang saat ini masuk daftar putih
"""

SET_CLEAN_BLUE_TEXT_HANDLER = CommandHandler(
    "cleanbluetext", set_blue_text_must_click, pass_args=True
)
ADD_CLEAN_BLUE_TEXT_HANDLER = CommandHandler(
    "ignorecleanbluetext", add_bluetext_ignore, pass_args=True
)
REMOVE_CLEAN_BLUE_TEXT_HANDLER = CommandHandler(
    "unignorecleanbluetext", remove_bluetext_ignore, pass_args=True
)
ADD_CLEAN_BLUE_TEXT_GLOBAL_HANDLER = CommandHandler(
    "ignoreglobalcleanbluetext", add_bluetext_ignore_global, pass_args=True
)
REMOVE_CLEAN_BLUE_TEXT_GLOBAL_HANDLER = CommandHandler(
    "unignoreglobalcleanbluetext", remove_bluetext_ignore_global, pass_args=True
)
LIST_CLEAN_BLUE_TEXT_HANDLER = CommandHandler("listcleanbluetext", bluetext_ignore_list)
CLEAN_BLUE_TEXT_HANDLER = MessageHandler(
    Filters.command & Filters.group, clean_blue_text_must_click
)

dispatcher.add_handler(SET_CLEAN_BLUE_TEXT_HANDLER)
dispatcher.add_handler(ADD_CLEAN_BLUE_TEXT_HANDLER)
dispatcher.add_handler(REMOVE_CLEAN_BLUE_TEXT_HANDLER)
dispatcher.add_handler(ADD_CLEAN_BLUE_TEXT_GLOBAL_HANDLER)
dispatcher.add_handler(REMOVE_CLEAN_BLUE_TEXT_GLOBAL_HANDLER)
dispatcher.add_handler(LIST_CLEAN_BLUE_TEXT_HANDLER)
dispatcher.add_handler(CLEAN_BLUE_TEXT_HANDLER, BLUE_TEXT_CLEAN_GROUP)

__mod_name__ = "Bluetext Cleaning"
__handlers__ = [
    SET_CLEAN_BLUE_TEXT_HANDLER,
    ADD_CLEAN_BLUE_TEXT_HANDLER,
    REMOVE_CLEAN_BLUE_TEXT_HANDLER,
    ADD_CLEAN_BLUE_TEXT_GLOBAL_HANDLER,
    REMOVE_CLEAN_BLUE_TEXT_GLOBAL_HANDLER,
    LIST_CLEAN_BLUE_TEXT_HANDLER,
    (CLEAN_BLUE_TEXT_HANDLER, BLUE_TEXT_CLEAN_GROUP),
]
