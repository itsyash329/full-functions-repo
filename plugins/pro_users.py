# YASHXCODES

from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime, timedelta
import re

from config import OWNER_ID


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
    """Convert normal English text into SMLCAP Unicode style."""
    return str(text).translate(SMLCAP_MAP)


# ===============================================================
# DURATION PARSER
# ===============================================================

def parse_duration(duration_str: str):
    """
    Parse durations such as:

    1 day
    2 weeks
    1 month
    1 year

    Returns timedelta or None.
    """

    duration_str = duration_str.lower().strip()

    match = re.match(
        r"^(\d+)\s*(day|days|week|weeks|month|months|year|years)$",
        duration_str
    )

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).rstrip("s")

    if amount <= 0:
        return None

    if unit == "day":
        return timedelta(days=amount)

    elif unit == "week":
        return timedelta(weeks=amount)

    elif unit == "month":
        # Approximate month as 30 days
        return timedelta(days=amount * 30)

    elif unit == "year":
        # Approximate year as 365 days
        return timedelta(days=amount * 365)

    return None


# ===============================================================
# FORMAT EXPIRY
# ===============================================================

def format_expiry(expiry_date):
    """Format expiry date for notifications."""

    if not expiry_date:
        return smlcap("Lifetime")

    return expiry_date.strftime("%d %B %Y • %I:%M %p")


def get_duration_text(duration_str, expiry_date):
    """Generate a clean duration description."""

    if not expiry_date:
        return smlcap("Permanent Access")

    if duration_str:
        return smlcap(duration_str)

    return smlcap("Premium Access")


# ===============================================================
# GET USER DETAILS
# ===============================================================

async def get_user_details(client, user_id):
    """
    Fetch user details safely.

    Returns:
        user
        full_name
        username
    """

    user = await client.get_users(user_id)

    full_name = user.first_name or "Unknown User"

    if user.last_name:
        full_name += f" {user.last_name}"

    username = f"@{user.username}" if user.username else "No Username"

    return user, full_name, username


# ===============================================================
# PREMIUM ACTIVATION NOTIFICATION
# ===============================================================

def premium_activated_message(
    user,
    user_id,
    duration_str=None,
    expiry_date=None
):
    """
    Premium activation notification shown to the user.
    """

    duration_display = (
        smlcap(duration_str)
        if duration_str
        else smlcap("Lifetime")
    )

    expiry_display = format_expiry(expiry_date)

    return (
        f"<b>👑 {smlcap('Premium Activated Successfully')}!</b>\n\n"

        f"👤 <b>{smlcap('User')}:</b> {user.mention}\n"
        f"🆔 <b>{smlcap('User ID')}:</b> <code>{user_id}</code>\n"
        f"💎 <b>{smlcap('Plan')}:</b> {smlcap('Premium')}\n"
        f"⏳ <b>{smlcap('Duration')}:</b> {duration_display}\n"
        f"📅 <b>{smlcap('Validity')}:</b> {expiry_display}\n\n"

        f"<b>✨ {smlcap('Your Premium Benefits Are Now Active')}!</b>"
    )


# ===============================================================
# PREMIUM REMOVAL NOTIFICATION
# ===============================================================

def premium_removed_message(user, user_id):
    """
    Premium removal notification shown to the user.
    """

    return (
        f"<b>⚠️ {smlcap('Premium Membership Ended')}</b>\n\n"

        f"👤 <b>{smlcap('User')}:</b> {user.mention}\n"
        f"🆔 <b>{smlcap('User ID')}:</b> <code>{user_id}</code>\n"
        f"💎 <b>{smlcap('Plan')}:</b> {smlcap('Free User')}\n\n"

        f"{smlcap('Your Premium Membership Is No Longer Active')}.\n"
        f"{smlcap('Contact The Administrator To Renew Your Membership')}."
    )


# ===============================================================
# ADD PREMIUM COMMAND
# ===============================================================

@Client.on_message(filters.command("addpremium") & filters.private)
async def add_premium_command(client: Client, message: Message):

    # Owner check
    if message.from_user.id != OWNER_ID:
        return await message.reply_text(
            f"<b>{smlcap('Only Owner Can Use This Command')}.</b>"
        )

    # Usage message
    usage = (
        f"<b>👑 {smlcap('Add Premium User')}</b>\n\n"

        f"<b>{smlcap('Usage')}:</b>\n"
        f"<code>/addpremium USER_ID [duration]</code>\n\n"

        f"<b>{smlcap('Examples')}:</b>\n"
        f"• <code>/addpremium 123456 1 day</code>\n"
        f"• <code>/addpremium 123456 2 weeks</code>\n"
        f"• <code>/addpremium 123456 1 month</code>\n"
        f"• <code>/addpremium 123456 1 year</code>\n"
        f"• <code>/addpremium 123456</code>\n\n"

        f"⚠️ {smlcap('No Duration Means Permanent Premium')}."
    )

    parts = message.command[1:]

    if not parts:
        return await message.reply_text(usage)

    # Parse user ID
    try:
        user_id_to_add = int(parts[0])

    except ValueError:
        return await message.reply_text(
            f"❌ <b>{smlcap('Invalid User ID')}.</b>"
        )

    # Fetch user
    try:
        user, user_name, username = await get_user_details(
            client,
            user_id_to_add
        )

    except Exception:
        return await message.reply_text(
            f"❌ <b>{smlcap('Unable To Find This User')}.</b>\n\n"
            f"{smlcap('Make Sure The User Has Started The Bot')}."
        )

    # ===========================================================
    # PARSE DURATION
    # ===========================================================

    duration_str = (
        " ".join(parts[1:])
        if len(parts) > 1
        else None
    )

    expiry_date = None

    if duration_str:

        duration = parse_duration(duration_str)

        if not duration:
            return await message.reply_text(
                f"❌ <b>{smlcap('Invalid Duration Format')}.</b>\n\n"
                f"{usage}"
            )

        expiry_date = datetime.now() + duration

    # ===========================================================
    # CHECK EXISTING PREMIUM
    # ===========================================================

    already_premium = await client.mongodb.is_pro(user_id_to_add)

    if already_premium:

        current_expiry = await client.mongodb.get_expiry_date(
            user_id_to_add
        )

        if current_expiry:

            return await message.reply_text(
                f"⚠️ <b>{smlcap('User Is Already A Premium Member')}</b>\n\n"

                f"👤 <b>{smlcap('User')}:</b> {user_name}\n"
                f"🆔 <b>{smlcap('User ID')}:</b> "
                f"<code>{user_id_to_add}</code>\n"

                f"📅 <b>{smlcap('Expires')}:</b> "
                f"{format_expiry(current_expiry)}"
            )

        return await message.reply_text(
            f"⚠️ <b>{smlcap('User Already Has Permanent Premium')}</b>\n\n"

            f"👤 <b>{smlcap('User')}:</b> {user_name}\n"
            f"🆔 <b>{smlcap('User ID')}:</b> "
            f"<code>{user_id_to_add}</code>"
        )

    # ===========================================================
    # ADD PREMIUM
    # ===========================================================

    success = await client.mongodb.add_pro(
        user_id_to_add,
        expiry_date
    )

    if not success:

        return await message.reply_text(
            f"❌ <b>{smlcap('Failed To Activate Premium')}.</b>"
        )

    # ===========================================================
    # ADMIN CONFIRMATION
    # ===========================================================

    duration_display = (
        smlcap(duration_str)
        if duration_str
        else smlcap("Lifetime")
    )

    expiry_display = format_expiry(expiry_date)

    admin_message = (
        f"<b>👑 {smlcap('Premium Activated Successfully')}</b>\n\n"

        f"👤 <b>{smlcap('User')}:</b> {user_name}\n"
        f"🔗 <b>{smlcap('Username')}:</b> {username}\n"
        f"🆔 <b>{smlcap('User ID')}:</b> "
        f"<code>{user_id_to_add}</code>\n"

        f"💎 <b>{smlcap('Plan')}:</b> Premium\n"
        f"⏳ <b>{smlcap('Duration')}:</b> {duration_display}\n"
        f"📅 <b>{smlcap('Validity')}:</b> {expiry_display}"
    )

    await message.reply_text(admin_message)

    # ===========================================================
    # USER NOTIFICATION
    # ===========================================================

    try:

        notification = premium_activated_message(
            user=user,
            user_id=user_id_to_add,
            duration_str=duration_str,
            expiry_date=expiry_date
        )

        await client.send_message(
            chat_id=user_id_to_add,
            text=notification
        )

    except Exception as error:

        # Do not fail premium activation if the user cannot be messaged.
        print(
            f"Failed to notify premium user "
            f"{user_id_to_add}: {error}"
        )


# ===============================================================
# DELETE PREMIUM COMMAND
# ===============================================================

@Client.on_message(filters.command("delpremium") & filters.private)
async def remove_premium_command(
    client: Client,
    message: Message
):

    # Owner check
    if message.from_user.id != OWNER_ID:

        return await message.reply_text(
            f"<b>{smlcap('Only Owner Can Use This Command')}.</b>"
        )

    # Usage validation
    if len(message.command) != 2:

        return await message.reply_text(
            f"<b>{smlcap('Incorrect Command Format')}</b>\n\n"

            f"<b>{smlcap('Usage')}:</b>\n"
            f"<code>/delpremium USER_ID</code>"
        )

    # Parse user ID
    try:

        user_id_to_remove = int(message.command[1])

    except ValueError:

        return await message.reply_text(
            f"❌ <b>{smlcap('Invalid User ID')}.</b>"
        )

    # Fetch user
    try:

        user, user_name, username = await get_user_details(
            client,
            user_id_to_remove
        )

    except Exception:

        return await message.reply_text(
            f"❌ <b>{smlcap('Unable To Find This User')}.</b>"
        )

    # Check premium status
    is_premium = await client.mongodb.is_pro(
        user_id_to_remove
    )

    if not is_premium:

        return await message.reply_text(
            f"⚠️ <b>{smlcap('This User Is Not An Active Premium User')}.</b>\n\n"

            f"👤 {user_name}\n"
            f"🆔 <code>{user_id_to_remove}</code>"
        )

    # Get expiry before removing
    expiry_date = await client.mongodb.get_expiry_date(
        user_id_to_remove
    )

    # Remove premium
    success = await client.mongodb.remove_pro(
        user_id_to_remove
    )

    if not success:

        return await message.reply_text(
            f"❌ <b>{smlcap('Failed To Remove Premium')}.</b>"
        )

    # ===========================================================
    # ADMIN CONFIRMATION
    # ===========================================================

    admin_message = (
        f"<b>🗑 {smlcap('Premium Membership Removed')}</b>\n\n"

        f"👤 <b>{smlcap('User')}:</b> {user_name}\n"
        f"🔗 <b>{smlcap('Username')}:</b> {username}\n"
        f"🆔 <b>{smlcap('User ID')}:</b> "
        f"<code>{user_id_to_remove}</code>\n"

        f"📅 <b>{smlcap('Previous Expiry')}:</b> "
        f"{format_expiry(expiry_date)}"
    )

    await message.reply_text(admin_message)

    # ===========================================================
    # USER NOTIFICATION
    # ===========================================================

    try:

        notification = premium_removed_message(
            user=user,
            user_id=user_id_to_remove
        )

        await client.send_message(
            chat_id=user_id_to_remove,
            text=notification
        )

    except Exception as error:

        print(
            f"Failed to notify removed premium user "
            f"{user_id_to_remove}: {error}"
        )


# ===============================================================
# PREMIUM USERS LIST
# ===============================================================

@Client.on_message(filters.command("premiumusers") & filters.private)
async def premium_users_command(
    client: Client,
    message: Message
):

    # Owner check
    if message.from_user.id != OWNER_ID:

        return await message.reply_text(
            f"<b>{smlcap('Only Owner Can Use This Command')}.</b>"
        )

    # Get active premium users
    pro_user_ids = await client.mongodb.get_pros_list()

    if not pro_user_ids:

        return await message.reply_text(
            f"<b>👑 {smlcap('Premium Users')}</b>\n\n"
            f"{smlcap('No Active Premium Users Found')}."
        )

    formatted_users = []

    # ===========================================================
    # BUILD USER LIST
    # ===========================================================

    for index, user_id in enumerate(
        pro_user_ids,
        start=1
    ):

        try:

            user, full_name, username = await get_user_details(
                client,
                user_id
            )

            expiry_date = await client.mongodb.get_expiry_date(
                user_id
            )

            if expiry_date:

                status = (
                    f"⏳ {smlcap('Expires')}: "
                    f"{format_expiry(expiry_date)}"
                )

            else:

                status = (
                    f"♾ {smlcap('Permanent Premium')}"
                )

            formatted_users.append(

                f"<b>{index}. 👤 {full_name}</b>\n"
                f"🔗 {username}\n"
                f"🆔 <code>{user_id}</code>\n"
                f"{status}"

            )

        except Exception:

            # Skip deleted/unavailable Telegram accounts.
            continue

    # ===========================================================
    # SEND LIST
    # ===========================================================

    if not formatted_users:

        return await message.reply_text(
            f"<b>👑 {smlcap('Premium Users')}</b>\n\n"
            f"{smlcap('No Active Premium Users Found')}."
        )

    header = (
        f"<b>👑 {smlcap('Premium Users List')}</b>\n\n"

        f"📊 <b>{smlcap('Active Premium Users')}:</b> "
        f"<code>{len(formatted_users)}</code>\n\n"
    )

    text = header

    # Telegram messages have a limit, so split long lists safely.
    for user_text in formatted_users:

        if len(text) + len(user_text) + 5 > 4000:

            await message.reply_text(
                text,
                disable_web_page_preview=True
            )

            text = (
                f"<b>👑 {smlcap('Premium Users List')} "
                f"({smlcap('Continued')})</b>\n\n"
            )

        text += user_text + "\n\n"

    if text:

        await message.reply_text(
            text,
            disable_web_page_preview=True
        )


# ===============================================================
# COMMAND ALIASES
# ===============================================================

@Client.on_message(filters.command(
    ["add_premium"]
) & filters.private)
async def add_premium_alias(
    client: Client,
    message: Message
):
    """
    Alias command.

    Redirects:
    /add_premium USER_ID duration

    to the same handler logic as /addpremium.
    """

    if message.from_user.id != OWNER_ID:

        return await message.reply_text(
            f"<b>{smlcap('Only Owner Can Use This Command')}.</b>"
        )

    # Reuse the command by changing command text.
    # This avoids duplicating premium logic.
    message.text = message.text.replace(
        "/add_premium",
        "/addpremium",
        1
    )

    await add_premium_command(client, message)


@Client.on_message(filters.command(
    ["rem_premium", "remove_premium"]
) & filters.private)
async def remove_premium_alias(
    client: Client,
    message: Message
):
    """
    Aliases:

    /rem_premium USER_ID
    /remove_premium USER_ID
    """

    if message.from_user.id != OWNER_ID:

        return await message.reply_text(
            f"<b>{smlcap('Only Owner Can Use This Command')}.</b>"
        )

    # We handle aliases directly instead of modifying
    # message.command, which Pyrogram may cache.

    if len(message.command) != 2:

        return await message.reply_text(
            f"<b>{smlcap('Incorrect Command Format')}</b>\n\n"
            f"<code>/rem_premium USER_ID</code>"
        )

    try:

        user_id_to_remove = int(message.command[1])

    except ValueError:

        return await message.reply_text(
            f"❌ <b>{smlcap('Invalid User ID')}.</b>"
        )

    try:

        user, user_name, username = await get_user_details(
            client,
            user_id_to_remove
        )

    except Exception:

        return await message.reply_text(
            f"❌ <b>{smlcap('Unable To Find This User')}.</b>"
        )

    if not await client.mongodb.is_pro(user_id_to_remove):

        return await message.reply_text(
            f"⚠️ <b>{smlcap('This User Is Not An Active Premium User')}.</b>"
        )

    expiry_date = await client.mongodb.get_expiry_date(
        user_id_to_remove
    )

    success = await client.mongodb.remove_pro(
        user_id_to_remove
    )

    if not success:

        return await message.reply_text(
            f"❌ <b>{smlcap('Failed To Remove Premium')}.</b>"
        )

    await message.reply_text(

        f"<b>🗑 {smlcap('Premium Membership Removed')}</b>\n\n"

        f"👤 <b>{smlcap('User')}:</b> {user_name}\n"
        f"🆔 <b>{smlcap('User ID')}:</b> "
        f"<code>{user_id_to_remove}</code>\n"
        f"📅 <b>{smlcap('Previous Expiry')}:</b> "
        f"{format_expiry(expiry_date)}"

    )

    try:

        await client.send_message(
            user_id_to_remove,
            premium_removed_message(
                user,
                user_id_to_remove
            )
        )

    except Exception as error:

        print(
            f"Failed to notify removed premium user: "
            f"{error}"
        )


# ===============================================================
# END OF FILE
# ===============================================================
