import html
from typing import List

import requests
from telegram import Bot, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, TOKEN
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_promote,
    user_admin,
    can_pin,
    connection_status,
)
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.log_channel import loggable


@run_async
@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
def promote(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    log_message = ""

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return log_message

    try:
        user_member = chat.get_member(user_id)
    except:
        return log_message

    if user_member.status == "administrator" or user_member.status == "creator":
        message.reply_text("Bagaimana maksud saya untuk mempromosikan seseorang yang sudah menjadi admin?")
        return log_message

    if user_id == bot.id:
        message.reply_text("Saya tidak dapat mempromosikan diri saya sendiri! Dapatkan admin untuk melakukannya untuk saya.")
        return log_message

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    try:
        bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=bot_member.can_change_info,
            can_post_messages=bot_member.can_post_messages,
            can_edit_messages=bot_member.can_edit_messages,
            can_delete_messages=bot_member.can_delete_messages,
            can_invite_users=bot_member.can_invite_users,
            # can_promote_members=bot_member.can_promote_members,
            can_restrict_members=bot_member.can_restrict_members,
            can_pin_messages=bot_member.can_pin_messages,
        )
    except BadRequest as err:
        if err.message == "User_not_mutual_contact":
            message.reply_text("Saya tidak dapat mempromosikan seseorang yang tidak ada di grup.")
            return log_message
        else:
            message.reply_text("Terjadi kesalahan saat mempromosikan.")
            return log_message

    bot.sendMessage(
        chat.id,
        f"Sucessfully promoted <b>{user_member.user.first_name or user_id}</b>!",
        parse_mode=ParseMode.HTML,
    )

    log_message += (
        f"<b>{html.escape(chat.title)}:</b>\n"
        "#PROMOTED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
    )

    return log_message


@run_async
@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
def demote(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    log_message = ""

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return log_message

    try:
        user_member = chat.get_member(user_id)
    except:
        return log_message

    if user_member.status == "creator":
        message.reply_text("Orang ini MENCIPTAKAN obrolan, bagaimana cara saya menurunkannya?")
        return log_message

    if not user_member.status == "administrator":
        message.reply_text("Tidak dapat menurunkan apa yang tidak dipromosikan!")
        return log_message

    if user_id == bot.id:
        message.reply_text("Saya tidak bisa menurunkan diri! Dapatkan admin untuk melakukannya untuk saya.")
        return log_message

    try:
        bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
        )

        bot.sendMessage(
            chat.id,
            f"Sucessfully demoted <b>{user_member.user.first_name or user_id}</b>!",
            parse_mode=ParseMode.HTML,
        )

        log_message += (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#DEMOTED\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>Pengguna:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
        )

        return log_message
    except BadRequest:
        message.reply_text(
            "Tidak bisa menurunkan. Saya mungkin bukan admin, atau status admin diangkat oleh orang lain"
            "pengguna, jadi saya tidak bisa menindaklanjutinya!"
        )
        return log_message


# Until the library releases the method
@run_async
@connection_status
@bot_admin
@can_promote
@user_admin
def set_title(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    message = update.effective_message

    user_id, title = extract_user_and_text(message, args)
    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return

    if user_member.status == "creator":
        message.reply_text(
            "Orang ini MENCIPTAKAN obrolan, bagaimana saya dapat menyetel judul khusus untuknya?"
        )
        return

    if not user_member.status == "administrator":
        message.reply_text(
            "Tidak dapat menyetel judul untuk non-admin!\nPromosikan mereka terlebih dahulu untuk menyetel judul khusus!"
        )
        return

    if user_id == bot.id:
        message.reply_text(
            "Saya tidak dapat menetapkan judul saya sendiri! Dapatkan orang yang menjadikan saya admin untuk melakukannya untuk saya."
        )
        return

    if not title:
        message.reply_text("Menyetel judul kosong tidak akan menghasilkan apa-apa!")
        return

    if len(title) > 16:
        message.reply_text(
            "Panjang judul lebih dari 16 karakter.\nPotong menjadi 16 karakter."
        )

    result = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/setChatAdministratorCustomTitle"
        f"?chat_id={chat.id}"
        f"&user_id={user_id}"
        f"&custom_title={title}"
    )
    status = result.json()["ok"]

    if status is True:
        bot.sendMessage(
            chat.id,
            f"Sucessfully set title for <code>{user_member.user.first_name or user_id}</code> "
            f"to <code>{title[:16]}</code>!",
            parse_mode=ParseMode.HTML,
        )
    else:
        description = result.json()["description"]
        if (
            description
            == "Permintaan Buruk: tidak cukup hak untuk mengubah judul khusus pengguna"
        ):
            message.reply_text(
                "Saya tidak dapat menyetel judul khusus untuk admin yang tidak saya promosikan!"
            )


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin(bot: Bot, update: Update, args: List[str]) -> str:
    user = update.effective_user
    chat = update.effective_chat

    is_group = chat.type != "private" and chat.type != "channel"
    prev_message = update.effective_message.reply_to_message

    is_silent = True
    if len(args) >= 1:
        is_silent = not (
            args[0].lower() == "notify"
            or args[0].lower() == "loud"
            or args[0].lower() == "violent"
        )

    if prev_message and is_group:
        try:
            bot.pinChatMessage(
                chat.id, prev_message.message_id, disable_notification=is_silent
            )
        except BadRequest as excp:
            if excp.message == "Chat_not_modified":
                pass
            else:
                raise
        log_message = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#PINNED\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}"
        )

        return log_message


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        else:
            raise

    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNPINNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}"
    )

    return log_message


@run_async
@bot_admin
@user_admin
def invite(bot: Bot, update: Update):
    chat = update.effective_chat

    if chat.username:
        update.effective_message.reply_text(chat.username)
    elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            update.effective_message.reply_text(invitelink)
        else:
            update.effective_message.reply_text(
                "Saya tidak memiliki akses ke tautan undangan, coba ubah izin saya!"
            )
    else:
        update.effective_message.reply_text(
            "Saya hanya dapat memberi Anda tautan undangan untuk supergrup dan saluran, maaf!"
        )


@run_async
@connection_status
def adminlist(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user

    chat_id = chat.id
    update_chat_title = chat.title
    message_chat_title = update.effective_message.chat.title

    administrators = bot.getChatAdministrators(chat_id)

    if update_chat_title == message_chat_title:
        chat_name = "this chat"
    else:
        chat_name = update_chat_title

    text = f"Admins in *{chat_name}*:"

    for admin in administrators:
        user = admin.user
        name = f"[{user.first_name + (user.last_name or '')}](tg://user?id={user.id})"
        text += f"\n - {name}"

    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def __chat_settings__(chat_id, user_id):
    return "You are *admin*: `{}`".format(
        dispatcher.bot.get_chat_member(chat_id, user_id).status
        in ("administrator", "creator")
    )


__help__ = """
 - /adminlist: daftar admin dalam obrolan

*Admin only:*
 - /pin: diam-diam pin pesan yang dibalas - tambahkan 'nyaring' atau 'beri tahu' untuk memberi pemberitahuan kepada pengguna.
 - /unpin: melepas pesan yang saat ini disematkan
 - /invitelink: mendapat invitelink
 - /promote: menaikkan jabatan pengguna
 - /demote: menurunkan jabatan pengguna
 - /settitle: menetapkan judul khusus untuk admin yang dipromosikan bot
"""

ADMINLIST_HANDLER = DisableAbleCommandHandler(["adminlist", "admins"], adminlist)

PIN_HANDLER = CommandHandler("pin", pin, pass_args=True, filters=Filters.group)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=Filters.group)

INVITE_HANDLER = DisableAbleCommandHandler("invitelink", invite, filters=Filters.group)

PROMOTE_HANDLER = CommandHandler("promote", promote, pass_args=True)
DEMOTE_HANDLER = CommandHandler("demote", demote, pass_args=True)

SET_TITLE_HANDLER = CommandHandler("settitle", set_title, pass_args=True)

dispatcher.add_handler(ADMINLIST_HANDLER)
dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(SET_TITLE_HANDLER)

__mod_name__ = "Admin"
__command_list__ = ["adminlist", "admins", "invitelink"]
__handlers__ = [
    ADMINLIST_HANDLER,
    PIN_HANDLER,
    UNPIN_HANDLER,
    INVITE_HANDLER,
    PROMOTE_HANDLER,
    DEMOTE_HANDLER,
    SET_TITLE_HANDLER,
]
