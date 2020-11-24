from datetime import datetime
from functools import wraps

from tg_bot.modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import Bot, Update, ParseMode
    from telegram.error import BadRequest, Unauthorized
    from telegram.ext import CommandHandler, run_async, JobQueue
    from telegram.utils.helpers import escape_markdown

    from tg_bot import dispatcher, LOGGER, GBAN_LOGS
    from tg_bot.modules.helper_funcs.chat_status import user_admin
    from tg_bot.modules.sql import log_channel_sql as sql

    def loggable(func):
        @wraps(func)
        def log_action(
            bot: Bot, update: Update, job_queue: JobQueue = None, *args, **kwargs
        ):

            if not job_queue:
                result = func(bot, update, *args, **kwargs)
            else:
                result = func(bot, update, job_queue, *args, **kwargs)

            chat = update.effective_chat
            message = update.effective_message

            if result:
                datetime_fmt = "%H:%M - %d-%m-%Y"
                result += f"\n<b>Event Stamp</b>: <code>{datetime.utcnow().strftime(datetime_fmt)}</code>"

                if message.chat.type == chat.SUPERGROUP and message.chat.username:
                    result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    send_log(bot, log_chat, chat.id, result)
            elif result == "" or not result:
                pass
            else:
                LOGGER.warning(
                    "%s was set as loggable, but had no return statement.", func
                )

            return result

        return log_action

    def gloggable(func):
        @wraps(func)
        def glog_action(bot: Bot, update: Update, *args, **kwargs):

            result = func(bot, update, *args, **kwargs)
            chat = update.effective_chat
            message = update.effective_message

            if result:
                datetime_fmt = "%H:%M - %d-%m-%Y"
                result += "\n<b>Event Stamp</b>: <code>{}</code>".format(
                    datetime.utcnow().strftime(datetime_fmt)
                )

                if message.chat.type == chat.SUPERGROUP and message.chat.username:
                    result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
                log_chat = str(GBAN_LOGS)
                if log_chat:
                    send_log(bot, log_chat, chat.id, result)
            elif result == "" or not result:
                pass
            else:
                LOGGER.warning(
                    "%s was set as loggable to gbanlogs, but had no return statement.",
                    func,
                )

            return result

        return glog_action

    def send_log(bot: Bot, log_chat_id: str, orig_chat_id: str, result: str):

        try:
            bot.send_message(
                log_chat_id,
                result,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except BadRequest as excp:
            if excp.message == "Chat not found":
                bot.send_message(
                    orig_chat_id, "This log channel has been deleted - unsetting."
                )
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning(excp.message)
                LOGGER.warning(result)
                LOGGER.exception("Could not parse")

                bot.send_message(
                    log_chat_id,
                    result
                    + "\n\nFormatting has been disabled due to an unexpected error.",
                )

    @run_async
    @user_admin
    def logging(bot: Bot, update: Update):

        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = bot.get_chat(log_channel)
            message.reply_text(
                f"Grup ini memiliki semua log yang dikirim ke:"
                f" {escape_markdown(log_channel_info.title)} (`{log_channel}`)",
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            message.reply_text("Tidak ada saluran log yang disetel untuk grup ini!")

    @run_async
    @user_admin
    def setlog(bot: Bot, update: Update):

        message = update.effective_message
        chat = update.effective_chat
        if chat.type == chat.CHANNEL:
            message.reply_text(
                "Sekarang, teruskan /setlog ke grup yang ingin Anda kaitkan dengan saluran ini!"
            )

        elif message.forward_from_chat:
            sql.set_chat_log_channel(chat.id, message.forward_from_chat.id)
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception(
                        "Error deleting message in log channel. Should work anyway though."
                    )

            try:
                bot.send_message(
                    message.forward_from_chat.id,
                    f"Saluran ini telah ditetapkan sebagai saluran log untuk {chat.title or chat.first_name}.",
                )
            except Unauthorized as excp:
                if excp.message == "Forbidden: bot is not a member of the channel chat":
                    bot.send_message(chat.id, "Berhasil menyetel saluran log!")
                else:
                    LOGGER.exception("ERROR in setting the log channel.")

            bot.send_message(chat.id, "Berhasil menyetel saluran log!")

        else:
            message.reply_text(
                "Langkah-langkah untuk mengatur saluran log adalah:\n"
                " - tambahkan bot ke saluran yang diinginkan\n"
                " - kirim /setlog ke saluran\n"
                " - meneruskan /setlog ke grup\n"
            )

    @run_async
    @user_admin
    def unsetlog(bot: Bot, update: Update):

        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            bot.send_message(
                log_channel, f"Tautan saluran telah dibatalkan dari {chat.title}"
            )
            message.reply_text("Saluran log telah dilepas.")

        else:
            message.reply_text("Tidak ada saluran log yang telah ditetapkan kamut!")

    def __stats__():
        return f"{sql.num_logchannels()} saluran log ditetapkan."

    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)

    def __chat_settings__(chat_id, user_id):
        log_channel = sql.get_chat_log_channel(chat_id)
        if log_channel:
            log_channel_info = dispatcher.bot.get_chat(log_channel)
            return f"Grup ini memiliki semua log yang dikirim ke: {escape_markdown(log_channel_info.title)} (`{log_channel}`)"
        return "Tidak ada saluran log yang disetel untuk grup ini!"

    __help__ = """
*Admin saja:*
- /logchannel: dapatkan info saluran log
- /setlog: mengatur saluran log.
- /unsetlog: hapus saluran log.

Pengaturan saluran log dilakukan dengan:
- menambahkan bot ke saluran yang diinginkan (sebagai admin!)
- kirim /setlog di saluran
- meneruskan /setlog ke grup
"""

    __mod_name__ = "Log Channels"

    LOG_HANDLER = CommandHandler("logchannel", logging)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog)

    dispatcher.add_handler(LOG_HANDLER)
    dispatcher.add_handler(SET_LOG_HANDLER)
    dispatcher.add_handler(UNSET_LOG_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func

    def gloggable(func):
        return func
