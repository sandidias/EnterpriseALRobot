import html

from typing import Optional, List

from telegram import Bot, Chat, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER, SARDEGNA_USERS
from tg_bot.modules.helper_funcs.chat_status import (
    bot_admin,
    user_admin,
    is_user_admin,
    can_restrict,
    connection_status,
)
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable


def check_user(user_id: int, bot: Bot, chat: Chat) -> Optional[str]:
    if not user_id:
        reply = "Anda sepertinya tidak mengacu pada pengguna."
        return reply

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Pengguna tidak ditemukan":
            reply = "Sepertinya saya tidak dapat menemukan pengguna ini"
            return reply
        else:
            raise

    if user_id == bot.id:
        reply = "Aku tidak akan MUTE diriku sendiri, Seberapa tinggi dirimu?"
        return reply

    if is_user_admin(chat, user_id, member) or user_id in SARDEGNA_USERS:
        reply = "Saya benar-benar berharap saya bisa membisukan admin ... Mungkin Pukulan?"
        return reply

    return None


@run_async
@connection_status
@bot_admin
@user_admin
@loggable
def mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id, reason = extract_user_and_text(message, args)
    reply = check_user(user_id, bot, chat)

    if reply:
        message.reply_text(reply)
        return ""

    member = chat.get_member(user_id)

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#MUTE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    )

    if reason:
        log += f"\n<b>Alasan:</b> {reason}"

    if member.can_send_messages is None or member.can_send_messages:
        bot.restrict_chat_member(chat.id, user_id, can_send_messages=False)
        bot.sendMessage(
            chat.id,
            f"Muted <b>{html.escape(member.user.first_name)}</b> tanpa tanggal kedaluwarsa!",
            parse_mode=ParseMode.HTML,
        )
        return log

    else:
        message.reply_text("Pengguna ini telah dibungkam!")

    return ""


@run_async
@connection_status
@bot_admin
@user_admin
@loggable
def unmute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text(
            "Anda harus memberi saya nama pengguna untuk menyuarakan, atau membalas seseorang untuk dibungkam."
        )
        return ""

    member = chat.get_member(int(user_id))

    if member.status != "kicked" and member.status != "left":
        if (
            member.can_send_messages
            and member.can_send_media_messages
            and member.can_send_other_messages
            and member.can_add_web_page_previews
        ):
            message.reply_text("Pengguna ini sudah memiliki hak untuk berbicara.")
        else:
            bot.restrict_chat_member(
                chat.id,
                int(user_id),
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
            bot.sendMessage(
                chat.id,
                f"I shall allow <b>{html.escape(member.user.first_name)}</b> to text!",
                parse_mode=ParseMode.HTML,
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#UNMUTE\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>Pengguna:</b> {mention_html(member.user.id, member.user.first_name)}"
            )
    else:
        message.reply_text(
            "Pengguna ini bahkan tidak ada dalam obrolan, mengaktifkannya tidak akan membuat mereka berbicara lebih banyak daripada mereka "
            "sudah lakukan!"
        )

    return ""


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id, reason = extract_user_and_text(message, args)
    reply = check_user(user_id, bot, chat)

    if reply:
        message.reply_text(reply)
        return ""

    member = chat.get_member(user_id)

    if not reason:
        message.reply_text("Anda belum menentukan waktu untuk menonaktifkan pengguna ini!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#TEMP MUTED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna:</b> {mention_html(member.user.id, member.user.first_name)}\n"
        f"<b>Waktu:</b> {time_val}"
    )
    if reason:
        log += f"\n<b>Alasan:</b> {reason}"

    try:
        if member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(
                chat.id, user_id, until_date=mutetime, can_send_messages=False
            )
            bot.sendMessage(
                chat.id,
                f"Muted <b>{html.escape(member.user.first_name)}</b> for {time_val}!",
                parse_mode=ParseMode.HTML,
            )
            return log
        else:
            message.reply_text("Pengguna ini telah dibungkam.")

    except BadRequest as excp:
        if excp.message == "Pesan balasan tidak ditemukan":
            # Do not reply
            message.reply_text(f"Muted for {time_val}!", quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "ERROR muting user %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Sial, saya tidak bisa menonaktifkan pengguna itu.")

    return ""


__help__ = """
*Khusus Admin:*
 - /mute <userhandle>: membungkam pengguna. Bisa juga digunakan sebagai balasan, membungkam pengguna yang dibalas.
 - /tmute <userhandle> x(m/h/d): membisukan pengguna selama x waktu. (melalui pegangan, atau balasan). m = menit, h = jam, d = hari.
 - /unmute <userhandle>: mengaktifkan pengguna. Bisa juga digunakan sebagai balasan, membungkam pengguna yang dibalas.
"""

MUTE_HANDLER = CommandHandler("mute", mute, pass_args=True)
UNMUTE_HANDLER = CommandHandler("unmute", unmute, pass_args=True)
TEMPMUTE_HANDLER = CommandHandler(["tmute", "tempmute"], temp_mute, pass_args=True)

dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)

__mod_name__ = "Muting"
__handlers__ = [MUTE_HANDLER, UNMUTE_HANDLER, TEMPMUTE_HANDLER]
