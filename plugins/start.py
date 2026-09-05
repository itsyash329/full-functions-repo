from helper.helper_func import *
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import humanize
from config import MSG_EFFECT, OWNER_ID, SHORT_TUT
from plugins.shortner import get_short
from helper.helper_func import get_messages, force_sub, decode, batch_auto_del_notification
import asyncio

#===============================================================#
# ===============================================================
# Access Screen
# ===============================================================
async def send_access_screen(client, message, open_url):
    """Send the configured secure-access screen used by all access modes."""
    caption = client.messages.get("SHORT_MSG", "🔐 Secure access has been enabled.")
    photo = client.messages.get("SHORT_PIC", client.messages.get("SHORT", ""))
    tutorial_url = getattr(client, "tutorial_link", None) or SHORT_TUT
    premium_url = getattr(client, "premium_url", None) or "https://t.me/LustyDormNeT"

    buttons = [[InlineKeyboardButton("• OPEN LINK •", url=open_url)]]
    if tutorial_url:
        buttons[0].append(InlineKeyboardButton("• TUTORIAL •", url=tutorial_url))
    if premium_url:
        buttons.append([InlineKeyboardButton("• BUY PREMIUM •", url=premium_url)])

    markup = InlineKeyboardMarkup(buttons)

    if photo:
        try:
            return await client.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=caption,
                reply_markup=markup,
                message_effect_id=MSG_EFFECT
            )
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Access screen photo failed: {e}")

    return await message.reply(
        caption,
        reply_markup=markup
    )

@Client.on_message(filters.command('start') & filters.private)
@force_sub
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id

    # 1. Add user if not present
    present = await client.mongodb.present_user(user_id)
    if not present:
        try:
            await client.mongodb.add_user(user_id)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error adding a user:\n{e}")

    # 2. Check if banned
    is_banned = await client.mongodb.is_banned(user_id)
    if is_banned:
        return await message.reply("**You have been banned from using this bot!**")

    text = message.text
    if len(text) > 7:
        try:
            original_payload = text.split(" ", 1)[1]
            base64_string = original_payload

            # Resolve compact start tokens first. Legacy long links still work.
            token_payload = await client.mongodb.get_short_start_payload(base64_string)
            if token_payload:
                base64_string = token_payload
                is_short_link = False
            else:
                is_short_link = False
                if base64_string.startswith("yu3elk"):
                    base64_string = base64_string[6:-1]
                    is_short_link = True

        except IndexError:
            return await message.reply("Invalid command format.")

        # Verification callbacks. Tokens are bound to the user who requested them.
        if base64_string.startswith("verify_") or base64_string.startswith("earn_") or base64_string.startswith("token_"):
            kind, verify_token = base64_string.split("_", 1)
            pending = await client.mongodb.get_pending_verification(verify_token)
            if not pending or pending.get("user_id") != user_id or pending.get("expires_at") <= __import__("datetime").datetime.now():
                return await message.reply("⚠️ This verification link is invalid, expired, or belongs to another user.")
            settings = await client.mongodb.get_access_settings()
            elapsed = (__import__("datetime").datetime.now() - pending["created_at"]).total_seconds()
            if elapsed < int(settings.get("min_verify_seconds", 0)):
                await client.mongodb.consume_pending_verification(verify_token)
                await message.reply("⚠️ Uncertain activity detected. Your verification was revoked. Please verify again normally.")
                try: await client.send_message(client.owner, f"🚨 Suspicious verification\nUser: {user_id}\nTime: {elapsed:.1f}s\nAction: revoked")
                except Exception: pass
                return
            await client.mongodb.consume_pending_verification(verify_token)
            if kind == "token":
                await client.mongodb.set_token_access(user_id, int(settings["token_hours"]))
                return await message.reply(f"✅ Token verified! You now have access for {settings['token_hours']} hour(s).")
            if kind == "earn":
                if await client.mongodb.get_credit(user_id) != 0:
                    return await message.reply("⚠️ Use your existing credits before earning more free credits.")
                bal = await client.mongodb.change_credit(user_id, int(settings["credit_reward"]))
                return await message.reply(f"✅ Verification complete! You earned {settings['credit_reward']} credit(s). Balance: {bal}")
            # verify_ shortener callback: continue using original payload
            base64_string = pending["payload"]

        # 3. Premium always bypasses every mode.
        is_user_pro = await client.mongodb.is_pro(user_id)
        mode = await client.mongodb.get_access_mode()
        settings = await client.mongodb.get_access_settings()

        if not is_user_pro and user_id != OWNER_ID:
            # TOKEN: one verification grants temporary access to everything.
            if mode == "token":
                until = await client.mongodb.get_token_access(user_id)
                if not until or until <= __import__("datetime").datetime.now():
                    pending = await client.mongodb.create_pending_verification(user_id, base64_string, "token")
                    url = f"https://t.me/{client.username}?start=token_{pending['_id']}"
                    return await send_access_screen(client, message, url)

            # CREDIT: deduct configured price per requested content. Free earning is only available at zero balance.
            elif mode == "credit":
                balance = await client.mongodb.get_credit(user_id)
                price = int(settings["credit_price"])
                if balance < price:
                    if balance == 0:
                        pending = await client.mongodb.create_pending_verification(user_id, base64_string, "earn")
                        short_link = get_short(f"https://t.me/{client.username}?start=earn_{pending['_id']}", client)
                        return await send_access_screen(client, message, short_link)
                    return await message.reply(f"💳 Insufficient credits. You have {balance}, but this content costs {price}. Use /credit_status to purchase more.")
                await client.mongodb.change_credit(user_id, -price, floor_zero=True)

            # SHORTENER: every file request requires its own verification; same pending link survives until expiry.
            elif mode == "shortener" and not is_short_link:
                pending = await client.mongodb.create_pending_verification(user_id, base64_string, "shortener")
                short_link = pending.get("short_url")
                if not short_link:
                    destination = f"https://t.me/{client.username}?start=verify_{pending['_id']}"
                    short_link = get_short(destination, client)
                    await client.mongodb.db['pending_verifications'].update_one({'_id': pending['_id']}, {'$set': {'short_url': short_link}})
                return await send_access_screen(client, message, short_link)

        # 6. Decode and prepare file IDs
        try:
            string = await decode(base64_string)
            argument = string.split("-")
            ids = []
            source_channel_id = None

            if len(argument) == 3:
                # Try to determine source channel from encoded multiplier
                encoded_start = int(argument[1])
                encoded_end = int(argument[2])
                
                # Try primary channel first
                primary_multiplier = abs(client.db)
                start_primary = int(encoded_start / primary_multiplier)
                end_primary = int(encoded_end / primary_multiplier)
                
                # Check if the division results in clean integers (meaning this channel was used for encoding)
                if encoded_start % primary_multiplier == 0 and encoded_end % primary_multiplier == 0:
                    source_channel_id = client.db
                    start = start_primary
                    end = end_primary
                    client.LOGGER(__name__, client.name).info(f"Decoded batch from primary channel {source_channel_id}: {start}-{end}")
                else:
                    # Try secondary channels
                    db_channels = getattr(client, 'db_channels', {})
                    for channel_id_str in db_channels.keys():
                        channel_id = int(channel_id_str)
                        channel_multiplier = abs(channel_id)
                        start_test = int(encoded_start / channel_multiplier)
                        end_test = int(encoded_end / channel_multiplier)
                        
                        if encoded_start % channel_multiplier == 0 and encoded_end % channel_multiplier == 0:
                            source_channel_id = channel_id
                            start = start_test
                            end = end_test
                            client.LOGGER(__name__, client.name).info(f"Decoded batch from secondary channel {source_channel_id}: {start}-{end}")
                            break
                    
                    # Fallback to primary if no match found
                    if source_channel_id is None:
                        source_channel_id = client.db
                        start = start_primary
                        end = end_primary
                
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))

            elif len(argument) == 2:
                # Single message
                encoded_msg = int(argument[1])
                
                # Try primary channel first
                if hasattr(client, 'db_channel') and client.db_channel:
                    primary_multiplier = abs(client.db_channel.id)
                    msg_id_primary = int(encoded_msg / primary_multiplier)
                    
                    if encoded_msg % primary_multiplier == 0:
                        source_channel_id = client.db_channel.id
                        ids = [msg_id_primary]
                    else:
                        # Try secondary channels
                        db_channels = getattr(client, 'db_channels', {})
                        for channel_id_str in db_channels.keys():
                            channel_id = int(channel_id_str)
                            channel_multiplier = abs(channel_id)
                            msg_id_test = int(encoded_msg / channel_multiplier)
                            
                            if encoded_msg % channel_multiplier == 0:
                                source_channel_id = channel_id
                                ids = [msg_id_test]
                                break
                        
                        # Fallback to primary
                        if source_channel_id is None:
                            source_channel_id = client.db_channel.id if hasattr(client, 'db_channel') else client.db
                            ids = [msg_id_primary]
                else:
                    # Fallback for legacy compatibility
                    source_channel_id = client.db
                    ids = [int(encoded_msg / abs(client.db))]

        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error decoding base64: {e}")
            return await message.reply("⚠️ Invalid or expired link.")

        # 7. Get messages from the specific source channel first
        temp_msg = await message.reply("Wait A Sec..")
        messages = []

        try:
            # Try to get messages from the identified source channel first
            if source_channel_id:
                client.LOGGER(__name__, client.name).info(f"Trying to get messages from source channel: {source_channel_id}")
                try:
                    msgs = await client.get_messages(
                        chat_id=source_channel_id,
                        message_ids=list(ids)
                    )
                    # Filter out None messages (deleted/not found)
                    valid_msgs = [msg for msg in msgs if msg is not None]
                    messages.extend(valid_msgs)
                    client.LOGGER(__name__, client.name).info(f"Found {len(valid_msgs)} messages from source channel {source_channel_id}")
                    
                    # If we didn't get all messages, try the fallback system
                    if len(valid_msgs) < len(list(ids)):
                        missing_ids = [mid for mid in ids if mid not in {msg.id for msg in valid_msgs}]
                        if missing_ids:
                            client.LOGGER(__name__, client.name).info(f"Missing {len(missing_ids)} messages, trying fallback system")
                            # Use the fallback system for missing messages
                            additional_messages = await get_messages(client, missing_ids)
                            messages.extend(additional_messages)
                            client.LOGGER(__name__, client.name).info(f"Found {len(additional_messages)} additional messages from fallback")
                except Exception as e:
                    client.LOGGER(__name__, client.name).warning(f"Error getting messages from source channel {source_channel_id}: {e}")
                    # Fallback to the multi-channel system
                    messages = await get_messages(client, ids)
            else:
                client.LOGGER(__name__, client.name).info("No specific source channel identified, using multi-channel fallback")
                # Use the multi-channel fallback system
                messages = await get_messages(client, ids)
        except Exception as e:
            await temp_msg.edit_text("Something went wrong!")
            client.LOGGER(__name__, client.name).warning(f"Error getting messages: {e}")
            return

        if not messages:
            return await temp_msg.edit("Couldn't find the files in the database.")
        await temp_msg.delete()

        yugen_msgs = []
        for msg in messages:
            caption = (
                client.messages.get('CAPTION', '').format(
                    previouscaption=msg.caption.html if msg.caption else msg.document.file_name
                ) if bool(client.messages.get('CAPTION', '')) and bool(msg.document)
                else ("" if not msg.caption else msg.caption.html)
            )
            reply_markup = msg.reply_markup if not client.disable_btn else None

            try:
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    reply_markup=reply_markup,
                    protect_content=client.protect
                )
                yugen_msgs.append(copied_msg)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    reply_markup=reply_markup,
                    protect_content=client.protect
                )
                yugen_msgs.append(copied_msg)
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(f"Failed to send message: {e}")
                pass

        # 8. Auto delete timer
        if messages and client.auto_del > 0:
            # Create transfer link for getting files again (original base64_string)
            transfer_link = original_payload
            
            # Start batch auto delete notification - single notification for all files
            asyncio.create_task(batch_auto_del_notification(
                bot_username=client.username,
                messages=yugen_msgs,
                delay_time=client.auto_del,
                transfer_link=transfer_link,
                chat_id=message.from_user.id,
                client=client
            ))
        return

    # 9. Normal start message
    else:
        buttons = [[InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data="about"), InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data='close')]]
        if user_id in client.admins:
            buttons.insert(0, [InlineKeyboardButton("⛩️ ꜱᴇᴛᴛɪɴɢꜱ ⛩️", callback_data="settings")])

        photo = client.messages.get("START_PHOTO", "")
        start_caption = client.messages.get('START', 'Welcome, {mention}').format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        )

        if photo:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=start_caption,
                message_effect_id=MSG_EFFECT,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await client.send_message(
                chat_id=message.chat.id,
                text=start_caption,
                message_effect_id=MSG_EFFECT,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        return

#===============================================================#

@Client.on_message(filters.command('request') & filters.private)
async def request_command(client: Client, message: Message):
    user_id = message.from_user.id
    is_admin = user_id in client.admins  # ✅ Fix this line
    is_user_premium = await client.mongodb.is_pro(user_id)

    if is_admin or user_id == OWNER_ID:
        await message.reply_text("🔹 **You are my sensei!**\nThis command is only for users.")
        return

    if not is_user_premium: 
        BUTTON_URL = "https://t.me/LustyDormNeT"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Upgrade to Premium", url=BUTTON_URL)]
        ])
        await message.reply(
            "❌ **You are not a premium user.**\nUpgrade to premium to access this feature.",
            reply_markup=reply_markup
        )
        return

    if len(message.command) < 2:
        await message.reply("⚠️ **Send me your request in this format:**\n`/request Your_Request_Here`")
        return

    requested = " ".join(message.command[1:])

    owner_message = (
        f"📩 **New Request from {message.from_user.mention}**\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"📝 Request: `{requested}`"
    )

    await client.send_message(OWNER_ID, owner_message)
    await message.reply("✅ **Thanks for your request!**\nYour request will be reviewed soon. Please wait.")

#===============================================================#

@Client.on_message(filters.command('profile') & filters.private)
async def my_plan(client: Client, message: Message):
    user_id = message.from_user.id
    is_admin = user_id in client.admins  # ✅ Fix here

    if is_admin or user_id == OWNER_ID:
        await message.reply_text("🔹 You're my sensei! This command is only for users.")
        return
    
    is_user_premium = await client.mongodb.is_pro(user_id)

    if is_user_premium:
        await message.reply_text(
            "**👤 Profile Information:**\n\n"
            "🔸 Ads: Disabled\n"
            "🔸 Plan: Premium\n"
            "🔸 Request: Enabled\n\n"
            "🌟 You're a Premium User!"
        )
    else:
        await message.reply_text(
            "**👤 Profile Information:**\n\n"
            "🔸 Ads: Enabled\n"
            "🔸 Plan: Free\n"
            "🔸 Request: Disabled\n\n"
            "🥳 Unlock Premium to get more benefits\n"
            "Contact: @Bruce_Wayne_01b"
)
