import html
from typing import List

from telegram import Bot, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER, DEV_USERS, SUDO_USERS, SARDEGNA_USERS
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import (
    bot_admin,
    user_admin,
    is_user_ban_protected,
    can_restrict,
    is_user_admin,
    is_user_in_chat,
    connection_status,
)
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable, gloggable


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Saya ragu itu adalah pengguna.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Pengguna tidak ditemukan":
            message.reply_text("Sepertinya tidak dapat menemukan orang ini.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Oh ya, larang diriku sendiri, baka!")
        return log_message

    # dev users to bypass whitelist protection incase of abuse
    if is_user_ban_protected(chat, user_id, member) and user not in DEV_USERS:
        message.reply_text("Pengguna ini memiliki kekebalan - Saya tidak bisa mencekal mereka.")
        return log_message

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#DILARANG\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna:</b> {mention_html(member.user.id, member.user.first_name)}"
    )
    if reason:
        log += "\n<b>Alasan:</b> {}".format(reason)

    try:
        chat.kick_member(user_id)
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            "Pengguna yang dilarang {}.".format(
                mention_html(member.user.id, member.user.first_name)
            ),
            parse_mode=ParseMode.HTML,
        )
        return log

    except BadRequest as excp:
        if excp.message == "Pesan balasan tidak ditemukan":
            # Do not reply
            message.reply_text("Dilarang!", quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "ERROR banning user %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Uhm ... itu tidak berhasil...")

    return log_message


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Saya ragu itu adalah pengguna.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Pengguna tidak ditemukan":
            message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Aku tidak akan melarang diriku sendiri, apakah kamu sudah gila?")
        return log_message

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Saya tidak merasa seperti itu.")
        return log_message

    if not reason:
        message.reply_text("Anda belum menentukan waktu untuk mencekal pengguna ini!")
        return log_message

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return log_message

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        "#TEMP BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna:</b> {mention_html(member.user.id, member.user.first_name)}\n"
        f"<b>Waktu:</b> {time_val}"
    )
    if reason:
        log += "\n<b>Alasan:</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            f"Dilarang! Pengguna {mention_html(member.user.id, member.user.first_name)} "
            f"akan dilarang selama {time_val}.",
            parse_mode=ParseMode.HTML,
        )
        return log

    except BadRequest as excp:
        if excp.message == "Pesan balasan tidak ditemukan":
            # Do not reply
            message.reply_text(
                f"Dilarang! Pengguna akan diblokir {time_val}.", quote=False
            )
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "ERROR banning user %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Sial, saya tidak bisa mencekal pengguna itu.")

    return log_message


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@loggable
def punch(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Saya ragu itu adalah pengguna.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Pengguna tidak ditemukan":
            message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Yeahhh aku tidak akan melakukan itu.")
        return log_message

    if is_user_ban_protected(chat, user_id):
        message.reply_text("Saya benar-benar berharap saya bisa memukul pengguna ini....")
        return log_message

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            f"Punched out! {mention_html(member.user.id, member.user.first_name)}.",
            parse_mode=ParseMode.HTML,
        )
        log = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#DITENDANG\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>Pengguna:</b> {mention_html(member.user.id, member.user.first_name)}"
        )
        if reason:
            log += f"\n<b>Alasan:</b> {reason}"

        return log

    else:
        message.reply_text("Sial, aku tidak bisa memukul pengguna itu.")

    return log_message


@run_async
@bot_admin
@can_restrict
def punchme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Saya berharap saya bisa ... tetapi Anda adalah admin.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("Tidak masalah.")
    else:
        update.effective_message.reply_text("Hah? Aku tidak bis :/")


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Saya ragu itu adalah pengguna.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Pengguna tidak ditemukan":
            message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Bagaimana saya membatalkan pelarangan diri sendiri jika saya tidak ada di sin...?")
        return log_message

    if is_user_in_chat(chat, user_id):
        message.reply_text("Bukankah orang ini sudah ada di sini??")
        return log_message

    chat.unban_member(user_id)
    message.reply_text("Ya, pengguna ini dapat bergabung!")

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna:</b> {mention_html(member.user.id, member.user.first_name)}"
    )
    if reason:
        log += f"\n<b>Alasan:</b> {reason}"

    return log


@run_async
@connection_status
@bot_admin
@can_restrict
@gloggable
def selfunban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user

    if user.id not in SUDO_USERS or user.id not in SARDEGNA_USERS:
        return

    try:
        chat_id = int(args[0])
    except:
        message.reply_text("Berikan ID obrolan yang valid.")
        return

    chat = bot.getChat(chat_id)

    try:
        member = chat.get_member(user.id)
    except BadRequest as excp:
        if excp.message == "Pengguna tidak ditemukan":
            message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
            return
        else:
            raise

    if is_user_in_chat(chat, user.id):
        message.reply_text("Bukankah kamu sudah mengobrol??")
        return

    chat.unban_member(user.id)
    message.reply_text("Ya, saya telah membatalkan pencekalan Anda.")

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>Pengguna:</b> {mention_html(member.user.id, member.user.first_name)}"
    )

    return log


__help__ = """
 - /punchme: meninju pengguna yang mengeluarkan perintah

*Admin only:*
 - /ban <userhandle>: melarang pengguna. (melalui pegangan, atau balasan)
 - /tban <userhandle> x(m/h/d): bsebagai pengguna untuk waktu x. (melalui pegangan, atau balasan). m = menit, h = jam, d = hari.
 - /unban <userhandle>: batalkan larangan pengguna. (melalui pegangan, atau balasan)
 - /punch <userhandle>: Meninju pengguna keluar dari grup, (melalui pegangan, atau balasan)
"""

BAN_HANDLER = CommandHandler("ban", ban, pass_args=True)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True)
PUNCH_HANDLER = CommandHandler(["punch", "kick"], punch, pass_args=True)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True)
ROAR_HANDLER = CommandHandler("roar", selfunban, pass_args=True)
PUNCHME_HANDLER = DisableAbleCommandHandler(
    ["punchme", "kickme"], punchme, filters=Filters.group
)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(PUNCH_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(ROAR_HANDLER)
dispatcher.add_handler(PUNCHME_HANDLER)

__mod_name__ = "Bans"
__handlers__ = [
    BAN_HANDLER,
    TEMPBAN_HANDLER,
    PUNCH_HANDLER,
    UNBAN_HANDLER,
    ROAR_HANDLER,
    PUNCHME_HANDLER,
]
