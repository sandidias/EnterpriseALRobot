from tg_bot.modules.helper_funcs.telethn.chatstatus import user_is_admin
from tg_bot.modules.helper_funcs.telethn.chatstatus import can_delete_messages
from tg_bot.lyn import lyndabot


@lyndabot(pattern="^/purge")
async def purge_messages(event):
    if event.from_id == None:
        return

    if not await user_is_admin(user_id=event.from_id, message=event):
        await event.reply("Hanya Admin yang diizinkan untuk menggunakan perintah ini")
        return

    if not await can_delete_messages(message=event):
        await event.reply("Sepertinya tidak bisa membersihkan pesan")
        return

    message = await event.get_reply_message()
    if not message:
        await event.reply("Balas pesan untuk memilih dari mana mulai membersihkan.")
        return
    messages = []
    message_id = message.id
    delete_to = event.message.id - 1
    await event.client.delete_messages(event.chat_id, event.message.id)

    messages.append(event.reply_to_msg_id)
    for message_id in range(delete_to, message_id - 1, -1):
        messages.append(message_id)
        if len(messages) == 100:
            await event.client.delete_messages(event.chat_id, messages)
            messages = []

    await event.client.delete_messages(event.chat_id, messages)
    text = "Berhasil dibersihkan!"
    await event.respond(text, parse_mode="markdown")


@lyndabot(pattern="^/del$")
async def delete_messages(event):
    if event.from_id == None:
        return

    if not await user_is_admin(user_id=event.from_id, message=event):
        await event.reply("Hanya Admin yang diizinkan untuk menggunakan perintah ini")
        return

    if not await can_delete_messages(message=event):
        await event.reply("Sepertinya tidak dapat menghapus ini?")
        return

    message = await event.get_reply_message()
    if not message:
        await event.reply("Whadaw ingin menghapus?")
        return
    chat = await event.get_input_chat()
    del_message = [message, event.message]
    await event.client.delete_messages(chat, del_message)


__help__ = """
*Admin saja:*
 - /del: menghapus pesan yang Anda balas
 - /purge: menghapus semua pesan antara ini dan pesan yang dibalas.
 - /purge <integer X>: menghapus pesan balasan, dan X pesan mengikutinya jika membalas pesan.
"""

__mod_name__ = "Purges"
