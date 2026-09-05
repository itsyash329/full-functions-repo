from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime


# ===============================================================
# ADMIN CHECK
# ===============================================================

ADMIN = lambda c, u: u in c.admins


# ===============================================================
# SMLCAP FONT HELPER
# ===============================================================

SMLCAP_MAP = str.maketrans({
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ",
    "e": "ᴇ", "f": "ꜰ", "g": "ɢ", "h": "ʜ",
    "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ",
    "m": "ᴍ", "n": "ɴ", "o": "ᴏ", "p": "ᴘ",
    "q": "ǫ", "r": "ʀ", "s": "ꜱ", "t": "ᴛ",
    "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x",
    "y": "ʏ", "z": "ᴢ",

    "A": "ᴀ", "B": "ʙ", "C": "ᴄ", "D": "ᴅ",
    "E": "ᴇ", "F": "ꜰ", "G": "ɢ", "H": "ʜ",
    "I": "ɪ", "J": "ᴊ", "K": "ᴋ", "L": "ʟ",
    "M": "ᴍ", "N": "ɴ", "O": "ᴏ", "P": "ᴘ",
    "Q": "ǫ", "R": "ʀ", "S": "ꜱ", "T": "ᴛ",
    "U": "ᴜ", "V": "ᴠ", "W": "ᴡ", "X": "x",
    "Y": "ʏ", "Z": "ᴢ",
})


def smlcap(text: str) -> str:
    """Convert text into SMLCAP Unicode style."""
    return str(text).translate(SMLCAP_MAP)


# ===============================================================
# USER DETAILS HELPER
# ===============================================================

async def get_user_details(client, user_id):
    """
    Safely fetch Telegram user details.

    Returns:
        user
        full_name
        username
    """

    try:
        user = await client.get_users(user_id)

        full_name = user.first_name or "Unknown User"

        if user.last_name:
            full_name += f" {user.last_name}"

        username = f"@{user.username}" if user.username else "No Username"

        return user, full_name, username

    except Exception:
        return None, "Unknown User", "No Username"


# ===============================================================
# ACCESS PANEL TEXT
# ===============================================================

async def panel_text(client):

    mode = await client.mongodb.get_access_mode()

    return (
        f"<b>🎛 {smlcap('Access Mode Panel')}</b>\n\n"

        f"{smlcap('Current Mode')}: "
        f"<b>{smlcap(mode.upper())}</b>\n\n"

        f"⚠️ {smlcap('Only One Mode Can Be Active At A Time')}.\n\n"

        f"📂 <b>{smlcap('Free Mode')}:</b> "
        f"{smlcap('Sends Files Directly Without Verification')}."
    )


# ===============================================================
# ACCESS PANEL BUTTONS
# ===============================================================

def panel_markup():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                f"🔗 {smlcap('Shortener')}",
                callback_data="mode_shortener"
            ),

            InlineKeyboardButton(
                f"💳 {smlcap('Credit')}",
                callback_data="mode_credit"
            )
        ],

        [
            InlineKeyboardButton(
                f"🎟 {smlcap('Token')}",
                callback_data="mode_token"
            ),

            InlineKeyboardButton(
                f"📂 {smlcap('Free')}",
                callback_data="mode_free"
            )
        ],

        [
            InlineKeyboardButton(
                f"⚙️ {smlcap('Settings')}",
                callback_data="access_settings"
            )
        ]
    ])


# ===============================================================
# ACCESS PANEL COMMAND
# ===============================================================

@Client.on_message(
    filters.command("panel") & filters.private
)
async def access_panel(client, message):

    if not ADMIN(client, message.from_user.id):
        return

    await message.reply(
        await panel_text(client),
        reply_markup=panel_markup()
    )


# ===============================================================
# ACCESS MODE CALLBACK
# ===============================================================

@Client.on_callback_query(
    filters.regex("^mode_(shortener|credit|token|free)$")
)
async def set_mode(client, query):

    if not ADMIN(client, query.from_user.id):

        return await query.answer(
            smlcap("Admins Only"),
            show_alert=True
        )

    mode = query.matches[0].group(1)

    await client.mongodb.set_access_mode(mode)

    await query.answer(
        f"✅ {smlcap(mode.upper())} {smlcap('Mode Enabled')}"
    )

    await query.message.edit_text(
        await panel_text(client),
        reply_markup=panel_markup()
    )


# ===============================================================
# ACCESS SETTINGS CALLBACK
# ===============================================================

@Client.on_callback_query(
    filters.regex("^access_settings$")
)
async def access_settings_callback(client, query):

    if not ADMIN(client, query.from_user.id):

        return await query.answer(
            smlcap("Admins Only"),
            show_alert=True
        )

    settings = await client.mongodb.get_access_settings()

    text = (
        f"<b>⚙️ {smlcap('Access Settings')}</b>\n\n"

        f"⏱ <b>{smlcap('Shortener Expiry')}:</b> "
        f"<code>{settings['shortener_expiry']}</code> "
        f"{smlcap('Minutes')}\n\n"

        f"🛡 <b>{smlcap('Minimum Verify Time')}:</b> "
        f"<code>{settings['min_verify_seconds']}</code> "
        f"{smlcap('Seconds')}\n\n"

        f"🛒 <b>{smlcap('Purchase URL')}:</b> "
        f"{smlcap('Configured') if settings.get('purchase_url') else smlcap('Not Set')}"
    )

    markup = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                f"⏱ {smlcap('Link Expiry')}",
                callback_data="set_link_expiry"
            ),

            InlineKeyboardButton(
                f"🛡 {smlcap('Verify Time')}",
                callback_data="set_min_verify"
            )
        ],

        [
            InlineKeyboardButton(
                f"🛒 {smlcap('Purchase URL')}",
                callback_data="set_purchase_url"
            )
        ],

        [
            InlineKeyboardButton(
                f"◂ {smlcap('Back')}",
                callback_data="back_access_panel"
            )
        ]
    ])

    await query.message.edit_text(
        text,
        reply_markup=markup
    )


# ===============================================================
# BACK TO ACCESS PANEL
# ===============================================================

@Client.on_callback_query(
    filters.regex("^back_access_panel$")
)
async def back_access_panel(client, query):

    if not ADMIN(client, query.from_user.id):

        return await query.answer(
            smlcap("Admins Only"),
            show_alert=True
        )

    await query.message.edit_text(
        await panel_text(client),
        reply_markup=panel_markup()
    )


# ===============================================================
# CREDIT PANEL
# ===============================================================

@Client.on_message(
    filters.command("credit_panel") & filters.private
)
async def credit_panel(client, message):

    if not ADMIN(client, message.from_user.id):
        return

    settings = await client.mongodb.get_access_settings()

    text = (
        f"<b>💳 {smlcap('Credit Panel')}</b>\n\n"

        f"💰 <b>{smlcap('Content Price')}:</b> "
        f"<code>{settings['credit_price']}</code> "
        f"{smlcap('Credit(s)')}\n\n"

        f"🎁 <b>{smlcap('Earn Reward')}:</b> "
        f"<code>{settings['credit_reward']}</code> "
        f"{smlcap('Credit(s)')}"
    )

    markup = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                f"💰 {smlcap('Content Price')}",
                callback_data="credit_price"
            ),

            InlineKeyboardButton(
                f"🎁 {smlcap('Credit Reward')}",
                callback_data="credit_reward"
            )
        ],

        [
            InlineKeyboardButton(
                f"📊 {smlcap('Stats')}",
                callback_data="credit_stats"
            )
        ],

        [
            InlineKeyboardButton(
                f"◂ {smlcap('Back')}",
                callback_data="back_access_panel"
            )
        ]
    ])

    await message.reply(
        text,
        reply_markup=markup
    )


# ===============================================================
# ASK INTEGER
# ===============================================================

async def ask_int(
    client,
    query,
    label,
    key
):

    await query.message.edit_text(

        f"🔢 <b>{smlcap('Send New Value')}</b>\n\n"

        f"{smlcap('Setting')}: "
        f"<b>{smlcap(label)}</b>\n\n"

        f"⏳ {smlcap('You Have 60 Seconds')}."
    )

    try:

        response = await client.listen(
            user_id=query.from_user.id,
            filters=filters.text,
            timeout=60
        )

        value = int(response.text.strip())

        if value < 1:
            raise ValueError

        await client.mongodb.update_access_setting(
            key,
            value
        )

        await query.message.edit_text(

            f"✅ <b>{smlcap('Setting Updated Successfully')}</b>\n\n"

            f"{smlcap(label)}: "
            f"<code>{value}</code>"
        )

    except Exception:

        await query.message.edit_text(

            f"❌ <b>{smlcap('Invalid Value Or Request Timed Out')}.</b>"
        )


# ===============================================================
# CREDIT PRICE CALLBACK
# ===============================================================

@Client.on_callback_query(
    filters.regex("^credit_price$")
)
async def credit_price_callback(client, query):

    if ADMIN(client, query.from_user.id):

        await ask_int(
            client,
            query,
            "Content Price",
            "credit_price"
        )


# ===============================================================
# CREDIT REWARD CALLBACK
# ===============================================================

@Client.on_callback_query(
    filters.regex("^credit_reward$")
)
async def credit_reward_callback(client, query):

    if ADMIN(client, query.from_user.id):

        await ask_int(
            client,
            query,
            "Credit Reward",
            "credit_reward"
        )


# ===============================================================
# CREDIT STATS CALLBACK
# ===============================================================

@Client.on_callback_query(
    filters.regex("^credit_stats$")
)
async def credit_stats_callback(client, query):

    if not ADMIN(client, query.from_user.id):

        return await query.answer(
            smlcap("Admins Only"),
            show_alert=True
        )

    users = await client.mongodb.list_credit_users()

    total_users = len(users)

    total_credits = sum(
        int(user.get("credit", 0))
        for user in users
    )

    text = (
        f"<b>📊 {smlcap('Credit Statistics')}</b>\n\n"

        f"👥 <b>{smlcap('Users With Credits')}:</b> "
        f"<code>{total_users}</code>\n\n"

        f"💳 <b>{smlcap('Total Credits')}:</b> "
        f"<code>{total_credits}</code>"
    )

    markup = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                f"◂ {smlcap('Back')}",
                callback_data="credit_panel_back"
            )
        ]
    ])

    await query.message.edit_text(
        text,
        reply_markup=markup
    )


# ===============================================================
# BACK TO CREDIT PANEL
# ===============================================================

@Client.on_callback_query(
    filters.regex("^credit_panel_back$")
)
async def credit_panel_back(client, query):

    if not ADMIN(client, query.from_user.id):
        return

    settings = await client.mongodb.get_access_settings()

    text = (
        f"<b>💳 {smlcap('Credit Panel')}</b>\n\n"

        f"💰 <b>{smlcap('Content Price')}:</b> "
        f"<code>{settings['credit_price']}</code> "
        f"{smlcap('Credit(s)')}\n\n"

        f"🎁 <b>{smlcap('Earn Reward')}:</b> "
        f"<code>{settings['credit_reward']}</code> "
        f"{smlcap('Credit(s)')}"
    )

    markup = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                f"💰 {smlcap('Content Price')}",
                callback_data="credit_price"
            ),

            InlineKeyboardButton(
                f"🎁 {smlcap('Credit Reward')}",
                callback_data="credit_reward"
            )
        ],

        [
            InlineKeyboardButton(
                f"📊 {smlcap('Stats')}",
                callback_data="credit_stats"
            )
        ],

        [
            InlineKeyboardButton(
                f"◂ {smlcap('Back')}",
                callback_data="back_access_panel"
            )
        ]
    ])

    await query.message.edit_text(
        text,
        reply_markup=markup
    )


# ===============================================================
# ADD CREDIT COMMAND
# ===============================================================

@Client.on_message(
    filters.command("add_credit") & filters.private
)
async def add_credit(client, message):

    if not ADMIN(client, message.from_user.id):
        return

    try:

        _, uid, amount = message.text.split(
            maxsplit=2
        )

        user_id = int(uid)
        credit_amount = int(amount)

        if credit_amount < 1:
            raise ValueError

        # Get user details
        user, full_name, username = await get_user_details(
            client,
            user_id
        )

        # Add credits
        balance = await client.mongodb.change_credit(
            user_id,
            credit_amount
        )

        # Admin confirmation
        admin_message = (

            f"<b>💳 {smlcap('Credits Added Successfully')}</b>\n\n"

            f"👤 <b>{smlcap('User')}:</b> "
            f"{full_name}\n"

            f"🔗 <b>{smlcap('Username')}:</b> "
            f"{username}\n"

            f"🆔 <b>{smlcap('User ID')}:</b> "
            f"<code>{user_id}</code>\n\n"

            f"➕ <b>{smlcap('Credits Added')}:</b> "
            f"<code>{credit_amount}</code>\n"

            f"💰 <b>{smlcap('New Balance')}:</b> "
            f"<code>{balance}</code>"
        )

        await message.reply(
            admin_message
        )

        # User notification
        if user:

            try:

                user_message = (

                    f"<b>🎉 {smlcap('Credits Added Successfully')}!</b>\n\n"

                    f"👤 <b>{smlcap('User')}:</b> "
                    f"{user.mention}\n"

                    f"🆔 <b>{smlcap('User ID')}:</b> "
                    f"<code>{user_id}</code>\n\n"

                    f"➕ <b>{smlcap('Credits Received')}:</b> "
                    f"<code>{credit_amount}</code>\n"

                    f"💳 <b>{smlcap('Available Credits')}:</b> "
                    f"<code>{balance}</code>\n\n"

                    f"✨ {smlcap('Your Credits Are Ready To Use')}!"
                )

                await client.send_message(
                    user_id,
                    user_message
                )

            except Exception as error:

                print(
                    f"Failed to notify credit user "
                    f"{user_id}: {error}"
                )

    except Exception:

        await message.reply(

            f"<b>⚠️ {smlcap('Usage')}:</b>\n\n"

            f"<code>/add_credit USER_ID AMOUNT</code>"
        )


# ===============================================================
# REMOVE CREDIT COMMAND
# ===============================================================

@Client.on_message(
    filters.command("rem_credit") & filters.private
)
async def rem_credit(client, message):

    if not ADMIN(client, message.from_user.id):
        return

    try:

        _, uid, amount = message.text.split(
            maxsplit=2
        )

        user_id = int(uid)
        credit_amount = int(amount)

        if credit_amount < 1:
            raise ValueError

        # Get user details
        user, full_name, username = await get_user_details(
            client,
            user_id
        )

        # Current balance
        old_balance = await client.mongodb.get_credit(
            user_id
        )

        # Remove credits
        balance = await client.mongodb.change_credit(
            user_id,
            -credit_amount,
            floor_zero=True
        )

        actual_removed = old_balance - balance

        # Admin confirmation
        admin_message = (

            f"<b>💳 {smlcap('Credits Removed Successfully')}</b>\n\n"

            f"👤 <b>{smlcap('User')}:</b> "
            f"{full_name}\n"

            f"🔗 <b>{smlcap('Username')}:</b> "
            f"{username}\n"

            f"🆔 <b>{smlcap('User ID')}:</b> "
            f"<code>{user_id}</code>\n\n"

            f"➖ <b>{smlcap('Credits Removed')}:</b> "
            f"<code>{actual_removed}</code>\n"

            f"💳 <b>{smlcap('Remaining Balance')}:</b> "
            f"<code>{balance}</code>"
        )

        await message.reply(
            admin_message
        )

        # User notification
        if user:

            try:

                user_message = (

                    f"<b>⚠️ {smlcap('Credits Have Been Removed')}</b>\n\n"

                    f"👤 <b>{smlcap('User')}:</b> "
                    f"{user.mention}\n"

                    f"🆔 <b>{smlcap('User ID')}:</b> "
                    f"<code>{user_id}</code>\n\n"

                    f"➖ <b>{smlcap('Credits Removed')}:</b> "
                    f"<code>{actual_removed}</code>\n"

                    f"💳 <b>{smlcap('Available Credits')}:</b> "
                    f"<code>{balance}</code>"
                )

                await client.send_message(
                    user_id,
                    user_message
                )

            except Exception as error:

                print(
                    f"Failed to notify credit user "
                    f"{user_id}: {error}"
                )

    except Exception:

        await message.reply(

            f"<b>⚠️ {smlcap('Usage')}:</b>\n\n"

            f"<code>/rem_credit USER_ID AMOUNT</code>"
        )


# ===============================================================
# CREDIT STATUS COMMAND
# ===============================================================

@Client.on_message(
    filters.command("credit_status") & filters.private
)
async def credit_status(client, message):

    balance = await client.mongodb.get_credit(
        message.from_user.id
    )

    settings = await client.mongodb.get_access_settings()

    text = (

        f"<b>💳 {smlcap('Credit Status')}</b>\n\n"

        f"💰 <b>{smlcap('Available Credits')}:</b> "
        f"<code>{balance}</code>"
    )

    markup = None

    if settings.get("purchase_url"):

        markup = InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    f"🛒 {smlcap('Get More Credits')}",
                    url=settings["purchase_url"]
                )
            ]
        ])

    await message.reply(
        text,
        reply_markup=markup
    )


# ===============================================================
# LIST CREDIT USERS
# ===============================================================

@Client.on_message(
    filters.command("list_credit_users") & filters.private
)
async def list_credit_users(client, message):

    if not ADMIN(client, message.from_user.id):
        return

    users = await client.mongodb.list_credit_users()

    if not users:

        return await message.reply(

            f"<b>💳 {smlcap('Credit Users')}</b>\n\n"

            f"{smlcap('No Users Currently Have Credits')}."
        )

    text = (

        f"<b>💳 {smlcap('Credit Users')}</b>\n\n"
    )

    count = 0

    for user_data in users[:100]:

        user_id = user_data["_id"]
        credit = user_data.get("credit", 0)

        count += 1

        text += (

            f"<b>{count}.</b> "
            f"<code>{user_id}</code> — "
            f"<b>{credit}</b> "
            f"{smlcap('Credits')}\n"
        )

    await message.reply(text)


# ===============================================================
# TOKEN PANEL
# ===============================================================

@Client.on_message(
    filters.command("token_panel") & filters.private
)
async def token_panel(client, message):

    if not ADMIN(client, message.from_user.id):
        return

    settings = await client.mongodb.get_access_settings()

    text = (

        f"<b>🎟 {smlcap('Token Panel')}</b>\n\n"

        f"⏳ <b>{smlcap('Verified Access')}:</b> "
        f"<code>{settings['token_hours']}</code> "
        f"{smlcap('Hour(s)')}"
    )

    markup = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                f"⏳ {smlcap('Set Validity')}",
                callback_data="token_hours"
            )
        ],

        [
            InlineKeyboardButton(
                f"◂ {smlcap('Back')}",
                callback_data="back_access_panel"
            )
        ]
    ])

    await message.reply(
        text,
        reply_markup=markup
    )


# ===============================================================
# TOKEN HOURS CALLBACK
# ===============================================================

@Client.on_callback_query(
    filters.regex("^token_hours$")
)
async def token_hours(client, query):

    if ADMIN(client, query.from_user.id):

        await ask_int(
            client,
            query,
            "Token Validity In Hours",
            "token_hours"
        )


# ===============================================================
# GLOBAL SETTINGS COMMAND
# ===============================================================

@Client.on_message(
    filters.command("setting") & filters.private
)
async def setting(client, message):

    if not ADMIN(client, message.from_user.id):
        return

    settings = await client.mongodb.get_access_settings()

    purchase_status = (
        smlcap("Configured")
        if settings.get("purchase_url")
        else smlcap("Not Set")
    )

    text = (

        f"<b>⚙️ {smlcap('Global Settings')}</b>\n\n"

        f"⏱ <b>{smlcap('Shortener Request Expiry')}:</b> "
        f"<code>{settings['shortener_expiry']}</code> "
        f"{smlcap('Minutes')}\n\n"

        f"🛡 <b>{smlcap('Minimum Verification Time')}:</b> "
        f"<code>{settings['min_verify_seconds']}</code> "
        f"{smlcap('Seconds')}\n\n"

        f"🛒 <b>{smlcap('Purchase URL')}:</b> "
        f"{purchase_status}"
    )

    markup = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                f"⏱ {smlcap('Link Expiry')}",
                callback_data="set_link_expiry"
            ),

            InlineKeyboardButton(
                f"🛡 {smlcap('Min Verify Time')}",
                callback_data="set_min_verify"
            )
        ],

        [
            InlineKeyboardButton(
                f"🛒 {smlcap('Purchase URL')}",
                callback_data="set_purchase_url"
            )
        ]
    ])

    await message.reply(
        text,
        reply_markup=markup
    )


# ===============================================================
# SET LINK EXPIRY
# ===============================================================

@Client.on_callback_query(
    filters.regex("^set_link_expiry$")
)
async def set_link_expiry(client, query):

    if ADMIN(client, query.from_user.id):

        await ask_int(
            client,
            query,
            "Shortener Expiry In Minutes",
            "shortener_expiry"
        )


# ===============================================================
# SET MINIMUM VERIFY TIME
# ===============================================================

@Client.on_callback_query(
    filters.regex("^set_min_verify$")
)
async def set_min_verify(client, query):

    if ADMIN(client, query.from_user.id):

        await ask_int(
            client,
            query,
            "Minimum Verification Time In Seconds",
            "min_verify_seconds"
        )


# ===============================================================
# SET PURCHASE URL
# ===============================================================

@Client.on_callback_query(
    filters.regex("^set_purchase_url$")
)
async def set_purchase_url(client, query):

    if not ADMIN(client, query.from_user.id):
        return

    await query.message.edit_text(

        f"🛒 <b>{smlcap('Send Purchase Or Contact URL')}</b>\n\n"

        f"⏳ {smlcap('You Have 60 Seconds')}."
    )

    try:

        response = await client.listen(

            user_id=query.from_user.id,
            filters=filters.text,
            timeout=60
        )

        url = response.text.strip()

        if not url.startswith(
            ("http://", "https://")
        ):
            raise ValueError

        await client.mongodb.update_access_setting(
            "purchase_url",
            url
        )

        await query.message.edit_text(

            f"✅ <b>{smlcap('Purchase URL Updated Successfully')}.</b>"
        )

    except Exception:

        await query.message.edit_text(

            f"❌ <b>{smlcap('Invalid URL Or Request Timed Out')}.</b>"
        )


# ===============================================================
# USER STATUS COMMAND
# ===============================================================

@Client.on_message(
    filters.command("status") & filters.private
)
async def status(client, message):

    user_id = message.from_user.id

    expiry = await client.mongodb.get_expiry_date(
        user_id
    )

    is_premium = await client.mongodb.is_pro(
        user_id
    )

    token_until = await client.mongodb.get_token_access(
        user_id
    )

    credits = await client.mongodb.get_credit(
        user_id
    )

    text = (

        f"<b>👤 {smlcap('Account Status')}</b>\n\n"
    )

    # Premium status
    if is_premium:

        if expiry:

            text += (

                f"👑 <b>{smlcap('Premium')}:</b> "
                f"{smlcap('Active')}\n"

                f"📅 <b>{smlcap('Expiry')}:</b> "
                f"{expiry.strftime('%d %b %Y • %I:%M %p')}\n\n"
            )

        else:

            text += (

                f"👑 <b>{smlcap('Premium')}:</b> "
                f"{smlcap('Lifetime')}\n\n"
            )

    else:

        text += (

            f"👤 <b>{smlcap('Status')}:</b> "
            f"{smlcap('Free User')}\n\n"
        )

    # Credits
    text += (

        f"💳 <b>{smlcap('Credits')}:</b> "
        f"<code>{credits}</code>\n"
    )

    # Token status
    if token_until and token_until > datetime.now():

        text += (

            f"\n🎟 <b>{smlcap('Token Access Until')}:</b>\n"

            f"<code>"
            f"{token_until.strftime('%d %b %Y • %I:%M %p')}"
            f"</code>"
        )

    await message.reply(text)


# ===============================================================
# ISSUE PENDING VERIFICATION
# ===============================================================

async def issue_pending(
    client,
    uid,
    payload,
    kind
):

    return await client.mongodb.create_pending_verification(
        uid,
        payload,
        kind
    )


# ===============================================================
# ACCESS PANEL ALIASES
# ===============================================================

@Client.on_message(
    filters.command(
        [
            "access_panel",
            "access",
            "access_system"
        ]
    )
    & filters.private
)
async def access_panel_alias(client, message):

    if not ADMIN(client, message.from_user.id):
        return

    await message.reply(

        await panel_text(client),

        reply_markup=panel_markup()
    )


# ===============================================================
# PREMIUM PANEL
# ===============================================================

@Client.on_message(
    filters.command("premium_panel") & filters.private
)
async def premium_panel(client, message):

    if not ADMIN(client, message.from_user.id):
        return

    pros = await client.mongodb.get_pros_list()

    text = (

        f"<b>👑 {smlcap('Premium Panel')}</b>\n\n"

        f"👥 <b>{smlcap('Active Premium Users')}:</b> "
        f"<code>{len(pros)}</code>\n\n"

        f"➕ <code>/addpremium USER_ID DURATION</code>\n"

        f"➖ <code>/delpremium USER_ID</code>\n"

        f"📋 <code>/premiumusers</code>"
    )

    markup = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                f"◂ {smlcap('Back To Access Panel')}",
                callback_data="back_access_panel"
            )
        ]
    ])

    await message.reply(
        text,
        reply_markup=markup
    )


# ===============================================================
# END OF FILE
# ===============================================================
