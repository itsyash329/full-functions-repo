from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.pyromod import ListenerTimeout
from datetime import datetime, timedelta
import secrets

ADMIN = lambda c, u: u in c.admins

async def panel_text(client):
    mode = await client.mongodb.get_access_mode()
    return f"<b>🎛 ACCESS MODE PANEL</b>\n\nCurrent Mode: <b>{mode.upper()}</b>\n\nOnly one mode can be active at a time.\nFREE mode sends files directly."

def panel_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🔗 SHORTENER', 'mode_shortener'), InlineKeyboardButton('💳 CREDIT', 'mode_credit')],
        [InlineKeyboardButton('🎟 TOKEN', 'mode_token'), InlineKeyboardButton('📂 FREE', 'mode_free')],
        [InlineKeyboardButton('⚙️ SETTINGS', 'access_settings')]
    ])

@Client.on_message(filters.command('panel') & filters.private)
async def access_panel(client, message):
    if not ADMIN(client, message.from_user.id): return
    await message.reply(await panel_text(client), reply_markup=panel_markup())

@Client.on_callback_query(filters.regex('^mode_(shortener|credit|token|free)$'))
async def set_mode(client, query):
    if not ADMIN(client, query.from_user.id): return await query.answer('Admins only', show_alert=True)
    mode = query.matches[0].group(1)
    await client.mongodb.set_access_mode(mode)
    await query.answer(f'{mode.upper()} MODE ENABLED')
    await query.message.edit_text(await panel_text(client), reply_markup=panel_markup())

@Client.on_message(filters.command('credit_panel') & filters.private)
async def credit_panel(client, message):
    if not ADMIN(client, message.from_user.id): return
    s = await client.mongodb.get_access_settings()
    await message.reply(f"<b>💳 CREDIT PANEL</b>\n\nContent price: <b>{s['credit_price']}</b> credit(s)\nEarn reward: <b>{s['credit_reward']}</b> credit(s)", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton('💰 CONTENT PRICE', 'credit_price'), InlineKeyboardButton('🎁 CREDIT REWARD', 'credit_reward')],
        [InlineKeyboardButton('📊 STATS', 'credit_stats')]
    ]))

async def ask_int(client, query, label, key):
    await query.message.edit_text(f'Send new {label} within 60 seconds.')
    try:
        r = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
        n = int(r.text.strip())
        if n < 1: raise ValueError
        await client.mongodb.update_access_setting(key, n)
        await query.message.edit_text(f'✅ {label} updated to {n}.')
    except Exception:
        await query.message.edit_text('❌ Invalid value or timeout.')

@Client.on_callback_query(filters.regex('^credit_price$'))
async def cp(client, query):
    if ADMIN(client, query.from_user.id): await ask_int(client, query, 'content price', 'credit_price')

@Client.on_callback_query(filters.regex('^credit_reward$'))
async def cr(client, query):
    if ADMIN(client, query.from_user.id): await ask_int(client, query, 'credit reward', 'credit_reward')

@Client.on_message(filters.command('add_credit') & filters.private)
async def add_credit(client, message):
    if not ADMIN(client, message.from_user.id): return
    try:
        _, uid, amount = message.text.split(maxsplit=2)
        bal = await client.mongodb.change_credit(int(uid), int(amount))
        await message.reply(f'✅ Credit added. New balance: {bal}')
    except Exception: await message.reply('Usage: /add_credit USER_ID AMOUNT')

@Client.on_message(filters.command('rem_credit') & filters.private)
async def rem_credit(client, message):
    if not ADMIN(client, message.from_user.id): return
    try:
        _, uid, amount = message.text.split(maxsplit=2)
        bal = await client.mongodb.change_credit(int(uid), -int(amount), floor_zero=True)
        await message.reply(f'✅ Credit removed. New balance: {bal}')
    except Exception: await message.reply('Usage: /rem_credit USER_ID AMOUNT')

@Client.on_message(filters.command('credit_status') & filters.private)
async def credit_status(client, message):
    bal = await client.mongodb.get_credit(message.from_user.id)
    s = await client.mongodb.get_access_settings()
    await message.reply(f'<b>💳 CREDIT STATUS</b>\n\nAvailable credits: <b>{bal}</b>', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🛒 GET MORE CREDITS', url=s['purchase_url'])]]) if s.get('purchase_url') else None)

@Client.on_message(filters.command('list_credit_users') & filters.private)
async def list_credit(client, message):
    if not ADMIN(client, message.from_user.id): return
    users = await client.mongodb.list_credit_users()
    text='\n'.join(f'`{x["_id"]}` — {x.get("credit",0)}' for x in users[:100]) or 'No users with credits.'
    await message.reply('<b>💳 CREDIT USERS</b>\n\n'+text)

@Client.on_message(filters.command('token_panel') & filters.private)
async def token_panel(client, message):
    if not ADMIN(client, message.from_user.id): return
    s=await client.mongodb.get_access_settings()
    await message.reply(f'<b>🎟 TOKEN PANEL</b>\n\nVerified access: <b>{s["token_hours"]} hour(s)</b>', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⏳ SET VALIDITY', 'token_hours')]]))

@Client.on_callback_query(filters.regex('^token_hours$'))
async def token_hours(client, query):
    if ADMIN(client, query.from_user.id): await ask_int(client, query, 'token validity in hours', 'token_hours')

@Client.on_message(filters.command('setting') & filters.private)
async def setting(client, message):
    if not ADMIN(client, message.from_user.id): return
    s=await client.mongodb.get_access_settings()
    await message.reply(f'<b>⚙️ GLOBAL SETTINGS</b>\n\nShortener request expiry: {s["shortener_expiry"]} minutes\nMinimum verification time: {s["min_verify_seconds"]} seconds', reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton('⏱ LINK EXPIRY', 'set_link_expiry'), InlineKeyboardButton('🛡 MIN VERIFY TIME', 'set_min_verify')],
        [InlineKeyboardButton('🛒 PURCHASE URL', 'set_purchase_url')]
    ]))

@Client.on_callback_query(filters.regex('^set_link_expiry$'))
async def sle(client,q):
    if ADMIN(client,q.from_user.id): await ask_int(client,q,'shortener expiry in minutes','shortener_expiry')
@Client.on_callback_query(filters.regex('^set_min_verify$'))
async def smv(client,q):
    if ADMIN(client,q.from_user.id): await ask_int(client,q,'minimum verification time in seconds','min_verify_seconds')
@Client.on_callback_query(filters.regex('^set_purchase_url$'))
async def spu(client,q):
    if not ADMIN(client,q.from_user.id): return
    await q.message.edit_text('Send purchase/contact URL within 60 seconds.')
    try:
        r=await client.listen(user_id=q.from_user.id,filters=filters.text,timeout=60)
        if not r.text.startswith(('http://','https://')): raise ValueError
        await client.mongodb.update_access_setting('purchase_url',r.text.strip())
        await q.message.edit_text('✅ Purchase URL updated.')
    except Exception: await q.message.edit_text('❌ Invalid URL or timeout.')

@Client.on_message(filters.command('status') & filters.private)
async def status(client,message):
    uid=message.from_user.id
    expiry=await client.mongodb.get_expiry_date(uid)
    pro=await client.mongodb.is_pro(uid)
    token_until=await client.mongodb.get_token_access(uid)
    text='<b>👤 ACCOUNT STATUS</b>\n\n'
    if pro: text+=f'👑 Premium: ACTIVE\nExpiry: {expiry or "Lifetime"}'
    else: text+='Status: FREE USER'
    text+=f'\n💳 Credits: {await client.mongodb.get_credit(uid)}'
    if token_until and token_until>datetime.now(): text+=f'\n🎟 Token access until: {token_until.strftime("%d %b %Y %H:%M")}'
    await message.reply(text)

async def issue_pending(client, uid, payload, kind):
    return await client.mongodb.create_pending_verification(uid, payload, kind)

# ---------------- Command aliases / missing panels ----------------
@Client.on_message(filters.command(['access_panel', 'access', 'access_system']) & filters.private)
async def access_panel_alias(client, message):
    if not ADMIN(client, message.from_user.id): return
    await message.reply(await panel_text(client), reply_markup=panel_markup())

@Client.on_message(filters.command(['premium_panel']) & filters.private)
async def premium_panel(client, message):
    if not ADMIN(client, message.from_user.id): return
    pros = await client.mongodb.get_pros_list()
    text = f'<b>👑 PREMIUM PANEL</b>\n\nActive premium users: <b>{len(pros)}</b>\n\nUse /add_premium USER_ID and /rem_premium USER_ID.'
    await message.reply(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ BACK TO ACCESS PANEL','mode_free')]]))
