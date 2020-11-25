import html
from typing import List

from telegram import Bot, Update, ParseMode, MAX_MESSAGE_LENGTH
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.userinfo_sql as sql
from tg_bot import dispatcher, SUDO_USERS, DEV_USERS
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user


@run_async
def about_me(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    user_id = extract_user(message, args)

    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_me_info(user.id)

    if info:
        update.effective_message.reply_text(
            f"*{user.first_name}*:\n{escape_markdown(info)}",
            parse_mode=ParseMode.MARKDOWN,
        )
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        update.effective_message.reply_text(
            f"{username} belum menyetel pesan info tentang diri mereka sendiri!"
        )
    else:
        update.effective_message.reply_text(
            "Anda belum menyetel pesan info tentang diri Anda!"
        )


@run_async
def set_about_me(bot: Bot, update: Update):
    message = update.effective_message
    user_id = message.from_user.id
    if user_id in (777000, 1087968824):
        message.reply_text("Jangan atur info untuk bot Telegram!")
        return
    if message.reply_to_message:
        repl_message = message.reply_to_message
        repl_user_id = repl_message.from_user.id
        if repl_user_id == bot.id and (user_id in SUDO_USERS or user_id in DEV_USERS):
            user_id = repl_user_id

    text = message.text
    info = text.split(None, 1)

    if len(info) == 2:
        if len(info[1]) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_me_info(user_id, info[1])
            if user_id == bot.id:
                message.reply_text("Memperbarui info saya!")
            else:
                message.reply_text("Memperbarui info Anda!")
        else:
            message.reply_text(
                "Info harus kurang dari {} karakter! Kamu punya {}.".format(
                    MAX_MESSAGE_LENGTH // 4, len(info[1])
                )
            )


@run_async
def about_bio(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    user_id = extract_user(message, args)
    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_bio(user.id)

    if info:
        update.effective_message.reply_text(
            "*{}*:\n{}".format(user.first_name, escape_markdown(info)),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif message.reply_to_message:
        username = user.first_name
        update.effective_message.reply_text(
            f"{username} belum ada pesan tentang diri mereka sendiri!"
        )
    else:
        update.effective_message.reply_text(
            "Anda belum memiliki set bio tentang diri Anda sendiri!"
        )


@run_async
def set_about_bio(bot: Bot, update: Update):
    message = update.effective_message
    sender_id = update.effective_user.id

    if message.reply_to_message:
        repl_message = message.reply_to_message
        user_id = repl_message.from_user.id
        if user_id in (777000, 1087968824):
            message.reply_text("Jangan setel bio untuk bot Telegram!")
            return
        
        if user_id == message.from_user.id:
            message.reply_text(
                "Ha, Anda tidak dapat mengatur biografi Anda sendiri! Anda berada di bawah belas kasihan orang lain di sini..."
            )
            return

        if (
            user_id == bot.id
            and sender_id not in SUDO_USERS
            and sender_id not in DEV_USERS
        ):
            message.reply_text(
                "Emm ... ya, saya hanya mempercayai pengguna sudo atau pengembang untuk mengatur bio saya."
            )
            return

        text = message.text
        bio = text.split(
            None, 1
        )  # use python's maxsplit to only remove the cmd, hence keeping newlines.

        if len(bio) == 2:
            if len(bio[1]) < MAX_MESSAGE_LENGTH // 4:
                sql.set_user_bio(user_id, bio[1])
                message.reply_text(
                    "Biografi {} diperbarui!".format(repl_message.from_user.first_name)
                )
            else:
                message.reply_text(
                    "Biografi harus kurang dari {} karakter! Anda mencoba untuk mengatur {}.".format(
                        MAX_MESSAGE_LENGTH // 4, len(bio[1])
                    )
                )
    else:
        message.reply_text("Balas pesan seseorang untuk menyetel biografi mereka!")


def __user_info__(user_id):
    bio = html.escape(sql.get_user_bio(user_id) or "")
    me = html.escape(sql.get_user_me_info(user_id) or "")
    if bio and me:
        return f"\n<b>Tentang pengguna:</b>\n{me}\n<b>Apa yang dikatakan orang lain:</b>\n{bio}\n"
    elif bio:
        return f"\n<b>Apa yang dikatakan orang lain:</b>\n{bio}\n"
    elif me:
        return f"\n<b>Tentang pengguna:</b>\n{me}\n"
    else:
        return "\n"


__help__ = """
 - /setbio <teks>: sambil membalas, akan menyimpan bio pengguna lain
 - /bio: akan mendapatkan bio Anda atau pengguna lain. Ini tidak dapat diatur sendiri.
 - /setme <teks>: akan mengatur info Anda
 - /me: akan mendapatkan info Anda atau pengguna lain
"""

SET_BIO_HANDLER = DisableAbleCommandHandler("setbio", set_about_bio)
GET_BIO_HANDLER = DisableAbleCommandHandler("bio", about_bio, pass_args=True)

SET_ABOUT_HANDLER = DisableAbleCommandHandler("setme", set_about_me)
GET_ABOUT_HANDLER = DisableAbleCommandHandler("me", about_me, pass_args=True)

dispatcher.add_handler(SET_BIO_HANDLER)
dispatcher.add_handler(GET_BIO_HANDLER)
dispatcher.add_handler(SET_ABOUT_HANDLER)
dispatcher.add_handler(GET_ABOUT_HANDLER)

__mod_name__ = "Bios and Abouts"
__command_list__ = ["setbio", "bio", "setme", "me"]
__handlers__ = [SET_BIO_HANDLER, GET_BIO_HANDLER, SET_ABOUT_HANDLER, GET_ABOUT_HANDLER]
