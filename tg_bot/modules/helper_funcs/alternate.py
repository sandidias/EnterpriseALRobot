from telegram import error


def send_message(message, text, *args, **kwargs):
    try:
        return message.reply_text(text, *args, **kwargs)
    except error.BadRequest as err:
        if str(err) == "Pesan balasan tidak ditemukan":
            return message.reply_text(text, quote=False, *args, **kwargs)
