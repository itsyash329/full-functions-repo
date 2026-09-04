from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.pyromod import ListenerTimeout
from datetime import datetime
from config import OWNER_ID


def ADMIN(client, user_id):
    return user_id in getattr(client, "admins", []) or user_id == OWNER_ID


def back_button(callback_data="access_home", text="◂ BACK"):
    return [InlineKeyboardButton(text, callback_data=callback_data)]


async def panel_text(client):
    mode = await client.mongodb.get_access_mode()
    return (
        "<b>🎛 ACCESS MODE PANEL</b>\n\n"
        f"Current Mode: <b>{mode.upper()}</b>\n\n"
        "Select one access system. Premium users and the owner bypass all modes."
    )


def panel_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 SHORTENER", "mode_shortener"), InlineKeyboardButton("💳 CREDIT", "mode_credit")],
        [InlineKeyboardButton("🎟 TOKEN", "mode_token"), InlineKeyboardButton("📂 FREE", "mode_free")],
        [InlineKeyboardButton("💳 CREDIT PANEL", "open_credit_panel"), InlineKeyboardButton("🎟 TOKEN PANEL", "open_token_panel")],
        [InlineKeyboardButton("⚙️ GLOBAL SETTINGS", "access_settings")],
    ])


async def show_access_panel(client, obj):
    text = await panel_text(client)
    if hasattr(obj, "message"):
        return await obj.message.edit_text(text, reply_markup=panel_markup())
    return await obj.reply(text, reply_markup=panel_markup())


@Client.on_message(filters.command(["panel", "premium_panel", "access_panel"]) & filters.private)
async def access_panel(client, message):
    if not ADMIN(client, message.from_user.id):
        return
    await show_access_panel(client, message)


@Client.on_callback_query(filters.regex("^access_home$"))
async def access_home(client, query):
    if not ADMIN(client, query.from_user.id):
        return await query.answer("Admins only", show_alert=True)
    await query.answer()
    await show_access_panel(client, query)


@Client.on_callback_query(filters.regex("^mode_(shortener|credit|token|free)$"))
async def set_mode(client, query):
    if not ADMIN(client, query.from_user.id):
        return await query.answer("Admins only", show_alert=True)
    mode = query.matches[0].group(1)
    await client.mongodb.set_access_mode(mode)
    await query.answer(f"{mode.upper()} MODE ENABLED")
    await show_access_panel(client, query)


# ---------------- CREDIT ----------------
async def credit_panel_view(client, obj):
    s = await client.mongodb.get_access_settings()
    text = (
        "<b>💳 CREDIT PANEL</b>\n\n"
        f"Content price: <b>{s['credit_price']}</b> credit(s)\n"
        f"Earn reward: <b>{s['credit_reward']}</b> credit(s)"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 CONTENT PRICE", "credit_price"), InlineKeyboardButton("🎁 CREDIT REWARD", "credit_reward")],
        [InlineKeyboardButton("📊 STATS", "credit_stats")],
        back_button(),
    ])
    if hasattr(obj, "message"):
        return await obj.message.edit_text(text, reply_markup=markup)
    return await obj.reply(text, reply_markup=markup)


@Client.on_message(filters.command("credit_panel") & filters.private)
async def credit_panel(client, message):
    if ADMIN(client, message.from_user.id):
        await credit_panel_view(client, message)


@Client.on_callback_query(filters.regex("^open_credit_panel$"))
async def open_credit_panel(client, query):
    if not ADMIN(client, query.from_user.id):
        return await query.answer("Admins only", show_alert=True)
    await query.answer()
    await credit_panel_view(client, query)


async def ask_int(client, query, label, key, back="access_home", minimum=0):
    await query.message.edit_text(
        f"Send new <b>{label}</b> within 60 seconds.",
        reply_markup=InlineKeyboardMarkup([back_button(back)])
    )
    try:
        r = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
        n = int(r.text.strip())
        if n < minimum:
            raise ValueError
        await client.mongodb.update_access_setting(key, n)
        await query.message.edit_text(
            f"✅ {label} updated to <b>{n}</b>.",
            reply_markup=InlineKeyboardMarkup([back_button(back)])
        )
    except ListenerTimeout:
        await query.message.edit_text("❌ Timeout. Try again.", reply_markup=InlineKeyboardMarkup([back_button(back)]))
    except Exception:
        await query.message.edit_text("❌ Invalid value.", reply_markup=InlineKeyboardMarkup([back_button(back)]))


@Client.on_callback_query(filters.regex("^credit_price$"))
async def cp(client, query):
    if ADMIN(client, query.from_user.id):
        await ask_int(client, query, "content price", "credit_price", "open_credit_panel", 1)


@Client.on_callback_query(filters.regex("^credit_reward$"))
async def cr(client, query):
    if ADMIN(client, query.from_user.id):
        await ask_int(client, query, "credit reward", "credit_reward", "open_credit_panel", 1)


@Client.on_callback_query(filters.regex("^credit_stats$"))
async def credit_stats(client, query):
    if not ADMIN(client, query.from_user.id):
        return await query.answer("Admins only", show_alert=True)
    users = await client.mongodb.list_credit_users()
    total_credits = sum(int(x.get("credit", 0)) for x in users)
    await query.answer()
    await query.message.edit_text(
        f"<b>📊 CREDIT STATS</b>\n\nUsers with credits: <b>{len(users)}</b>\nTotal credits: <b>{total_credits}</b>",
        reply_markup=InlineKeyboardMarkup([back_button("open_credit_panel")])
    )


@Client.on_message(filters.command("add_credit") & filters.private)
async def add_credit(client, message):
    if not ADMIN(client, message.from_user.id):
        return
    args = message.command[1:]
    if len(args) != 2:
        return await message.reply("Usage: <code>/add_credit USER_ID AMOUNT</code>")
    try:
        uid, amount = int(args[0]), int(args[1])
        if amount <= 0:
            raise ValueError
        bal = await client.mongodb.change_credit(uid, amount)
        await message.reply(f"✅ Credit added. New balance: <b>{bal}</b>")
    except Exception:
        await message.reply("Usage: <code>/add_credit USER_ID AMOUNT</code>")


@Client.on_message(filters.command("rem_credit") & filters.private)
async def rem_credit(client, message):
    if not ADMIN(client, message.from_user.id):
        return
    args = message.command[1:]
    if len(args) != 2:
        return await message.reply("Usage: <code>/rem_credit USER_ID AMOUNT</code>")
    try:
        uid, amount = int(args[0]), int(args[1])
        if amount <= 0:
            raise ValueError
        bal = await client.mongodb.change_credit(uid, -amount, floor_zero=True)
        await message.reply(f"✅ Credit removed. New balance: <b>{bal}</b>")
    except Exception:
        await message.reply("Usage: <code>/rem_credit USER_ID AMOUNT</code>")


@Client.on_message(filters.command("credit_status") & filters.private)
async def credit_status(client, message):
    bal = await client.mongodb.get_credit(message.from_user.id)
    s = await client.mongodb.get_access_settings()
    markup = None
    if s.get("purchase_url"):
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 GET MORE CREDITS", url=s["purchase_url"])]] )
    await message.reply(f"<b>💳 CREDIT STATUS</b>\n\nAvailable credits: <b>{bal}</b>", reply_markup=markup)


@Client.on_message(filters.command("list_credit_users") & filters.private)
async def list_credit(client, message):
    if not ADMIN(client, message.from_user.id):
        return
    users = await client.mongodb.list_credit_users()
    text = "\n".join(f"<code>{x['_id']}</code> — {x.get('credit', 0)}" for x in users[:100]) or "No users with credits."
    await message.reply("<b>💳 CREDIT USERS</b>\n\n" + text)


# ---------------- TOKEN ----------------
async def token_panel_view(client, obj):
    s = await client.mongodb.get_access_settings()
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ SET VALIDITY", "token_hours")],
        back_button(),
    ])
    text = f"<b>🎟 TOKEN PANEL</b>\n\nVerified access: <b>{s['token_hours']} hour(s)</b>"
    if hasattr(obj, "message"):
        return await obj.message.edit_text(text, reply_markup=markup)
    return await obj.reply(text, reply_markup=markup)


@Client.on_message(filters.command("token_panel") & filters.private)
async def token_panel(client, message):
    if ADMIN(client, message.from_user.id):
        await token_panel_view(client, message)


@Client.on_callback_query(filters.regex("^open_token_panel$"))
async def open_token_panel(client, query):
    if not ADMIN(client, query.from_user.id):
        return await query.answer("Admins only", show_alert=True)
    await query.answer()
    await token_panel_view(client, query)


@Client.on_callback_query(filters.regex("^token_hours$"))
async def token_hours(client, query):
    if ADMIN(client, query.from_user.id):
        await ask_int(client, query, "token validity in hours", "token_hours", "open_token_panel", 1)


# ---------------- GLOBAL SETTINGS ----------------
async def settings_view(client, obj):
    s = await client.mongodb.get_access_settings()
    text = (
        "<b>⚙️ GLOBAL ACCESS SETTINGS</b>\n\n"
        f"Shortener link expiry: <b>{s['shortener_expiry']} minutes</b>\n"
        f"Minimum verification time: <b>{s['min_verify_seconds']} seconds</b>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱ LINK EXPIRY", "set_link_expiry"), InlineKeyboardButton("🛡 MIN VERIFY TIME", "set_min_verify")],
        [InlineKeyboardButton("🛒 PURCHASE URL", "set_purchase_url")],
        back_button(),
    ])
    if hasattr(obj, "message"):
        return await obj.message.edit_text(text, reply_markup=markup)
    return await obj.reply(text, reply_markup=markup)


@Client.on_message(filters.command(["setting", "access_settings"]) & filters.private)
async def setting(client, message):
    if ADMIN(client, message.from_user.id):
        await settings_view(client, message)


@Client.on_callback_query(filters.regex("^access_settings$"))
async def access_settings_cb(client, query):
    if not ADMIN(client, query.from_user.id):
        return await query.answer("Admins only", show_alert=True)
    await query.answer()
    await settings_view(client, query)


@Client.on_callback_query(filters.regex("^set_link_expiry$"))
async def sle(client, query):
    if ADMIN(client, query.from_user.id):
        await ask_int(client, query, "shortener expiry in minutes", "shortener_expiry", "access_settings", 1)


@Client.on_callback_query(filters.regex("^set_min_verify$"))
async def smv(client, query):
    if ADMIN(client, query.from_user.id):
        await ask_int(client, query, "minimum verification time in seconds", "min_verify_seconds", "access_settings", 0)


@Client.on_callback_query(filters.regex("^set_purchase_url$"))
async def spu(client, q):
    if not ADMIN(client, q.from_user.id):
        return
    await q.message.edit_text("Send purchase/contact URL within 60 seconds.", reply_markup=InlineKeyboardMarkup([back_button("access_settings")]))
    try:
        r = await client.listen(user_id=q.from_user.id, filters=filters.text, timeout=60)
        url = r.text.strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError
        await client.mongodb.update_access_setting("purchase_url", url)
        await q.message.edit_text("✅ Purchase URL updated.", reply_markup=InlineKeyboardMarkup([back_button("access_settings")]))
    except Exception:
        await q.message.edit_text("❌ Invalid URL or timeout.", reply_markup=InlineKeyboardMarkup([back_button("access_settings")]))


@Client.on_message(filters.command("status") & filters.private)
async def status(client, message):
    uid = message.from_user.id
    expiry = await client.mongodb.get_expiry_date(uid)
    pro = await client.mongodb.is_pro(uid)
    token_until = await client.mongodb.get_token_access(uid)
    text = "<b>👤 ACCOUNT STATUS</b>\n\n"
    text += f"👑 Premium: {'ACTIVE' if pro else 'INACTIVE'}"
    if pro:
        text += f"\nExpiry: {expiry or 'Lifetime'}"
    text += f"\n💳 Credits: {await client.mongodb.get_credit(uid)}"
    if token_until and token_until > datetime.now():
        text += f"\n🎟 Token access until: {token_until.strftime('%d %b %Y %H:%M')}"
    await message.reply(text)
