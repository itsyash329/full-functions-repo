import requests, random, string
from config import SHORT_URL, SHORT_API, MESSAGES
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.errors.pyromod import ListenerTimeout
shortened_urls_cache={}
def generate_random_alphanumeric(): return ''.join(random.choice(string.ascii_letters+string.digits) for _ in range(8))
def _shortners(client):
    items=getattr(client,'shortners',None)
    if not items: items=[{'id':1,'url':getattr(client,'short_url',SHORT_URL),'api':getattr(client,'short_api',SHORT_API),'enabled':True}]
    client.shortners=items; return items
async def _save(client):
    await client.mongodb.update_shortner_setting('shortners',client.shortners); await client.mongodb.update_shortner_setting('shortner_index',getattr(client,'shortner_index',0))
def _next_shortner(client):
    active=[x for x in _shortners(client) if x.get('enabled',True)]
    if not active:return None
    i=getattr(client,'shortner_index',0)%len(active); client.shortner_index=(i+1)%len(active); return active[i]
def get_short(url,client):
    if not getattr(client,'shortner_enabled',True): return url
    p=_next_shortner(client)
    if not p:return url
    # Never cache across different verification destinations/users.
    key=f"{p['id']}:{url}"
    if key in shortened_urls_cache:return shortened_urls_cache[key]
    try:
        alias=generate_random_alphanumeric(); r=requests.get(f"https://{p['url']}/api?api={p['api']}&url={url}&alias={alias}",timeout=15); d=r.json()
        if r.status_code==200 and d.get('status')=='success':
            out=d.get('shortenedUrl',url); shortened_urls_cache[key]=out; return out
    except Exception as e: print(f"[Shortener Error - {p['url']}] {e}")
    return url

async def shortner_panel(client,obj):
    items=_shortners(client); enabled=getattr(client,'shortner_enabled',True)
    listing='\n'.join(f"{'🟢' if x.get('enabled',True) else '🔴'} #{x['id']} • `{x['url']}`" for x in items) or 'No shorteners added.'
    text=f"<b>🔗 MULTIPLE SHORTENER SETTINGS</b>\n\nGlobal: {'🟢 ENABLED' if enabled else '🔴 DISABLED'}\nActive: {sum(x.get('enabled',True) for x in items)}/{len(items)}\n\n{listing}\n\nRound-robin rotation is automatic."
    kb=InlineKeyboardMarkup([[InlineKeyboardButton('➕ ADD SHORTENER','add_shortner'),InlineKeyboardButton('📋 MANAGE LIST','manage_shortners')],[InlineKeyboardButton('🔄 TEST','test_shortner'),InlineKeyboardButton('⚡ TOGGLE SYSTEM','toggle_shortner')],[InlineKeyboardButton('📚 TUTORIAL LINK','set_tutorial_link')]])
    if hasattr(obj,'message'): await obj.message.edit_text(text,reply_markup=kb)
    else: await obj.reply_text(text,reply_markup=kb)
@Client.on_message(filters.command(['shortner','shortener_panel']) & filters.private)
async def cmd(client,m):
    if m.from_user.id in client.admins: await shortner_panel(client,m)
@Client.on_callback_query(filters.regex('^shortner$'))
async def cb(client,q):
    if q.from_user.id in client.admins: await shortner_panel(client,q)
@Client.on_callback_query(filters.regex('^toggle_shortner$'))
async def toggle(client,q):
    if q.from_user.id not in client.admins:return await q.answer('Admins only',show_alert=True)
    client.shortner_enabled=not getattr(client,'shortner_enabled',True); await client.mongodb.set_shortner_status(client.shortner_enabled); await shortner_panel(client,q)
@Client.on_callback_query(filters.regex('^add_shortner$'))
async def add(client,q):
    if q.from_user.id not in client.admins:return
    await q.message.edit_text('Send: `domain.com api_key` within 60 seconds.')
    try:
        r=await client.listen(user_id=q.from_user.id,filters=filters.text,timeout=60); parts=r.text.strip().split(maxsplit=1)
        if len(parts)!=2:raise ValueError
        url=parts[0].replace('https://','').replace('http://','').strip('/'); api=parts[1].strip()
        if '.' not in url or not api:raise ValueError
        items=_shortners(client); nid=max([x.get('id',0) for x in items] or [0])+1; items.append({'id':nid,'url':url,'api':api,'enabled':True}); await _save(client); await q.message.edit_text(f'✅ Shortener #{nid} added.')
    except Exception: await q.message.edit_text('❌ Invalid format or timeout.')
@Client.on_callback_query(filters.regex('^manage_shortners$'))
async def manage(client,q):
    if q.from_user.id not in client.admins:return
    rows=[]
    for x in _shortners(client): rows.append([InlineKeyboardButton(f"{'🟢' if x.get('enabled',True) else '🔴'} #{x['id']} {x['url']}",f"noop_{x['id']}"),InlineKeyboardButton('⚡ ON/OFF',f"toggle_provider_{x['id']}"),InlineKeyboardButton('❌ REMOVE',f"remove_provider_{x['id']}")])
    rows.append([InlineKeyboardButton('◂ BACK','shortner')]); await q.message.edit_text('📋 <b>MANAGE SHORTENERS</b>',reply_markup=InlineKeyboardMarkup(rows))
@Client.on_callback_query(filters.regex('^toggle_provider_'))
async def tp(client,q):
    sid=int(q.data.rsplit('_',1)[1])
    if q.from_user.id not in client.admins:return
    for x in _shortners(client):
        if x['id']==sid:x['enabled']=not x.get('enabled',True);break
    await _save(client); await manage(client,q)
@Client.on_callback_query(filters.regex('^remove_provider_'))
async def rp(client,q):
    sid=int(q.data.rsplit('_',1)[1]); items=_shortners(client)
    if q.from_user.id not in client.admins:return
    if len(items)<=1:return await q.answer('At least one shortener must remain!',show_alert=True)
    client.shortners=[x for x in items if x['id']!=sid]; await _save(client); await manage(client,q)
@Client.on_callback_query(filters.regex('^set_tutorial_link$'))
async def tut(client,q):
    if q.from_user.id not in client.admins:return
    await q.message.edit_text('Send tutorial URL within 60 seconds.')
    try:
        r=await client.listen(user_id=q.from_user.id,filters=filters.text,timeout=60); link=r.text.strip()
        if not link.startswith(('http://','https://')):raise ValueError
        client.tutorial_link=link; await client.mongodb.update_shortner_setting('tutorial_link',link); await q.message.edit_text('✅ Tutorial link updated.')
    except Exception:await q.message.edit_text('❌ Invalid URL or timeout.')
@Client.on_callback_query(filters.regex('^test_shortner$'))
async def test(client,q):
    if q.from_user.id not in client.admins:return
    out=[]
    for x in _shortners(client):
        try:
            r=requests.get(f"https://{x['url']}/api?api={x['api']}&url=https://google.com&alias={generate_random_alphanumeric()}",timeout=10); d=r.json(); out.append(f"{'✅' if d.get('status')=='success' else '❌'} #{x['id']} `{x['url']}`")
        except:out.append(f"❌ #{x['id']} `{x['url']}`")
    await q.message.edit_text('SHORTENER TEST RESULTS\n\n'+'\n'.join(out))
@Client.on_callback_query(filters.regex('^noop_'))
async def noop(client,q): await q.answer()

# ---------------- Command compatibility layer ----------------
def _admin_or_alert(client, message):
    return message.from_user and message.from_user.id in client.admins

@Client.on_message(filters.command(['shortener', 'shortner_panel']) & filters.private)
async def shortener_alias_panel(client, message):
    if not _admin_or_alert(client, message): return
    await shortner_panel(client, message)

@Client.on_message(filters.command(['list_shorteners']) & filters.private)
async def list_shorteners_cmd(client, message):
    if not _admin_or_alert(client, message): return
    items = _shortners(client)
    text = '<b>📋 SHORTENER LIST</b>\n\n' + '\n'.join(
        f"{'🟢' if x.get('enabled', True) else '🔴'} ID {x['id']} • <code>{x['url']}</code>" for x in items
    )
    await message.reply(text or 'No shorteners configured.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ BACK TO PANEL','shortner')]]))

@Client.on_message(filters.command(['toggle_shortener']) & filters.private)
async def toggle_shortener_cmd(client, message):
    if not _admin_or_alert(client, message): return
    parts = message.command
    if len(parts) == 1:
        client.shortner_enabled = not getattr(client, 'shortner_enabled', True)
        await client.mongodb.set_shortner_status(client.shortner_enabled)
        return await message.reply(f"✅ Shortener system {'ENABLED' if client.shortner_enabled else 'DISABLED'}.")
    try:
        sid = int(parts[1])
        for x in _shortners(client):
            if x['id'] == sid:
                x['enabled'] = not x.get('enabled', True)
                await _save(client)
                return await message.reply(f"✅ Shortener #{sid} is now {'ENABLED' if x['enabled'] else 'DISABLED'}.")
        await message.reply('❌ Shortener ID not found.')
    except ValueError:
        await message.reply('Usage: /toggle_shortener ID')

@Client.on_message(filters.command(['rem_shortener']) & filters.private)
async def rem_shortener_cmd(client, message):
    if not _admin_or_alert(client, message): return
    if len(message.command) < 2:
        return await message.reply('Usage: /rem_shortener ID')
    try:
        sid = int(message.command[1]); items = _shortners(client)
        if len(items) <= 1: return await message.reply('❌ At least one shortener must remain.')
        if not any(x['id'] == sid for x in items): return await message.reply('❌ Shortener ID not found.')
        client.shortners = [x for x in items if x['id'] != sid]
        await _save(client)
        await message.reply(f'✅ Shortener #{sid} removed.')
    except ValueError: await message.reply('Usage: /rem_shortener ID')

@Client.on_message(filters.command(['add_shortener', 'add_shortner']) & filters.private)
async def add_shortener_cmd(client, message):
    if not _admin_or_alert(client, message): return
    # Supports /add_shortener domain.com API_KEY or interactive mode.
    if len(message.command) >= 3:
        url = message.command[1].replace('https://','').replace('http://','').strip('/')
        api = message.command[2]
    else:
        await message.reply('Send: <code>domain.com API_KEY</code> within 60 seconds.')
        try:
            r = await client.listen(user_id=message.from_user.id, filters=filters.text, timeout=60)
            parts = r.text.strip().split(maxsplit=1)
            if len(parts) != 2: raise ValueError
            url = parts[0].replace('https://','').replace('http://','').strip('/'); api = parts[1].strip()
        except Exception:
            return await message.reply('❌ Invalid format or timeout.')
    if '.' not in url or not api: return await message.reply('❌ Invalid format. Use: domain.com API_KEY')
    items = _shortners(client); nid = max([x.get('id',0) for x in items] or [0]) + 1
    items.append({'id':nid,'url':url,'api':api,'enabled':True}); await _save(client)
    await message.reply(f'✅ Shortener #{nid} added: <code>{url}</code>')
