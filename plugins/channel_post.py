import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from helper.helper_func import encode

#===============================================================#

BOT_COMMANDS = [

    # ===========================================================
    # USER COMMANDS
    # ===========================================================
    "start",
    "request",
    "profile",


    # ===========================================================
    # FILE LINK GENERATOR
    # ===========================================================
    "batch",
    "genlink",
    "nbatch",


    # ===========================================================
    # STATISTICS & BROADCAST
    # ===========================================================
    "stats",
    "users",
    "broadcast",
    "pbroadcast",


    # ===========================================================
    # ACCESS SYSTEM
    # ===========================================================
    "panel",
    "credit_panel",
    "add_credit",
    "rem_credit",
    "credit_status",
    "list_credit_users",
    "token_panel",
    "setting",
    "status",


    # Access system aliases
    "access_panel",
    "access",
    "access_system",


    # ===========================================================
    # PREMIUM SYSTEM
    # ===========================================================
    "addpremium",
    "delpremium",
    "premiumusers",
    "premium_panel",


    # Premium aliases
    "add_premium",
    "rem_premium",
    "remove_premium",


    # ===========================================================
    # SHORTENER SYSTEM
    # ===========================================================
    "shortner",
    "shortener",
    "shortener_panel",
    "shortner_panel",

    "list_shorteners",
    "toggle_shortener",
    "rem_shortener",

    "add_shortener",
    "add_shortner",


    # ===========================================================
    # DATABASE MANAGEMENT
    # ===========================================================
    "db",

    "adddb",
    "add_db",

    "removedb",
    "rm_db",


    # ===========================================================
    # USER MANAGEMENT
    # ===========================================================
    "ban",
    "unban"
]

@Client.on_message(filters.private & ~filters.command(BOT_COMMANDS))
async def channel_post(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    reply_text = await message.reply_text("Please Wait...!", quote = True)
    try:
        post_message = await message.copy(chat_id = client.db, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.x)
        post_message = await message.copy(chat_id = client.db, disable_notification=True)
    except Exception as e:
        print(e)
        await reply_text.edit_text("Something went Wrong..!")
        return
    converted_id = post_message.id * abs(client.db)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    short_token = await client.mongodb.create_short_start_token(base64_string)
    link = f"https://t.me/{client.username}?start={short_token}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])

    await reply_text.edit(f"<b>Here is your link</b>\n\n{link}", reply_markup=reply_markup, disable_web_page_preview = True)

    if not client.disable_btn:
        await post_message.edit_reply_markup(reply_markup)

#===============================================================#

@Client.on_message(filters.channel & filters.incoming)
async def new_post(client: Client, message: Message):
    if message.chat.id != client.db:
        return
    if client.disable_btn:
        return

    converted_id = message.id * abs(client.db)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    short_token = await client.mongodb.create_short_start_token(base64_string)
    link = f"https://t.me/{client.username}?start={short_token}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    try:
        await message.edit_reply_markup(reply_markup)
    except Exception as e:
        print(e)

        pass
