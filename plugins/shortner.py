import requests
import random
import string

from config import SHORT_URL, SHORT_API
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.pyromod import ListenerTimeout

shortened_urls_cache = {}


def generate_random_alphanumeric():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))


def _is_admin(client, user_id):
    return user_id in getattr(client, 'admins', [])


def _shortners(client):
    items = getattr(client, 'shortners', None)
    if not items:
        items = [{
            'id': 1,
            'url': getattr(client, 'short_url', SHORT_URL),
            'api': getattr(client, 'short_api', SHORT_API),
            'enabled': True,
        }]
    client.shortners = items
    return items


async def _save(client):
    await client.mongodb.update_shortner_setting('shortners', client.shortners)
    await client.mongodb.update_shortner_setting('shortner_index', getattr(client, 'shortner_index', 0))


def _next_shortner(client):
    active = [x for x in _shortners(client) if x.get('enabled', True)]
    if not active:
        return None
    index = getattr(client, 'shortner_index', 0) % len(active)
    client.shortner_index = (index + 1) % len(active)
    return active[index]


def get_short(url, client):
    """Create a short URL using the existing round-robin shortener system."""
    if not getattr(client, 'shortner_enabled', True):
        return url

    provider = _next_shortner(client)
    if not provider:
        return url

    key = f"{provider['id']}:{url}"
    if key in shortened_urls_cache:
        return shortened_urls_cache[key]

    try:
        domain = str(provider['url']).replace('https://', '').replace('http://', '').strip('/')
        params = {
            'api': provider['api'],
            'url': url,
            'alias': generate_random_alphanumeric(),
        }
        response = requests.get(f"https://{domain}/api", params=params, timeout=15)
        data = response.json()
        if response.status_code == 200 and data.get('status') == 'success':
            result = data.get('shortenedUrl') or data.get('short_url') or url
            shortened_urls_cache[key] = result
            return result
    except Exception as error:
        print(f"[Shortener Error - {provider.get('url')}] {error}")

    return url


async def shortner_panel(client, obj):
    items = _shortners(client)
    enabled = getattr(client, 'shortner_enabled', True)
    listing = '\n'.join(
        f"{'🟢' if x.get('enabled', True) else '🔴'} <code>#{x['id']}</code> • <code>{x['url']}</code>"
        for x in items
    ) or 'No shorteners added.'

    text = (
        '<b>🔗 MULTIPLE SHORTENER SETTINGS</b>\n\n'
        f"Global: {'🟢 ENABLED' if enabled else '🔴 DISABLED'}\n"
        f"Active: {sum(x.get('enabled', True) for x in items)}/{len(items)}\n\n"
        f"{listing}\n\nRound-robin rotation is automatic."
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('➕ ADD SHORTENER', 'add_shortner'), InlineKeyboardButton('📋 MANAGE LIST', 'manage_shortners')],
        [InlineKeyboardButton('⚡ TOGGLE SYSTEM', 'toggle_shortner'), InlineKeyboardButton('🔄 TEST', 'test_shortner')],
        [InlineKeyboardButton('📚 TUTORIAL LINK', 'set_tutorial_link')],
        [InlineKeyboardButton('◂ BACK', 'settings')],
    ])
    if hasattr(obj, 'message'):
        return await obj.message.edit_text(text, reply_markup=markup)
    return await obj.reply_text(text, reply_markup=markup)


@Client.on_message(filters.command(['shortner', 'shortener', 'shortener_panel']) & filters.private)
async def shortener_command(client, message):
    if _is_admin(client, message.from_user.id):
        await shortner_panel(client, message)


@Client.on_callback_query(filters.regex('^shortner$'))
async def shortner_callback(client, query):
    if not _is_admin(client, query.from_user.id):
        return await query.answer('Admins only', show_alert=True)
    await query.answer()
    await shortner_panel(client, query)


@Client.on_callback_query(filters.regex('^toggle_shortner$'))
async def toggle_shortner_system(client, query):
    if not _is_admin(client, query.from_user.id):
        return await query.answer('Admins only', show_alert=True)
    client.shortner_enabled = not getattr(client, 'shortner_enabled', True)
    await client.mongodb.set_shortner_status(client.shortner_enabled)
    await query.answer('Updated')
    await shortner_panel(client, query)


async def _add_shortener_flow(client, message):
    await message.reply_text('Send: <code>domain.com API_KEY</code> within 60 seconds.')
    try:
        reply = await client.listen(user_id=message.from_user.id, filters=filters.text, timeout=60)
        parts = reply.text.strip().split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError
        domain = parts[0].replace('https://', '').replace('http://', '').strip('/')
        api_key = parts[1].strip()
        if '.' not in domain or not api_key:
            raise ValueError
        items = _shortners(client)
        new_id = max([int(x.get('id', 0)) for x in items] or [0]) + 1
        items.append({'id': new_id, 'url': domain, 'api': api_key, 'enabled': True})
        await _save(client)
        await reply.reply_text(f'✅ Shortener <code>#{new_id}</code> added: <code>{domain}</code>')
    except ListenerTimeout:
        await message.reply_text('❌ Timeout.')
    except Exception:
        await message.reply_text('❌ Invalid format. Use: <code>/add_shortener domain.com API_KEY</code>')


@Client.on_message(filters.command(['add_shortener', 'add_shortner']) & filters.private)
async def add_shortener_command(client, message):
    if not _is_admin(client, message.from_user.id):
        return
    args = message.command[1:]
    if len(args) >= 2:
        domain, api_key = args[0], ' '.join(args[1:])
        domain = domain.replace('https://', '').replace('http://', '').strip('/')
        if '.' not in domain or not api_key.strip():
            return await message.reply_text('Usage: <code>/add_shortener domain.com API_KEY</code>')
        items = _shortners(client)
        new_id = max([int(x.get('id', 0)) for x in items] or [0]) + 1
        items.append({'id': new_id, 'url': domain, 'api': api_key.strip(), 'enabled': True})
        await _save(client)
        return await message.reply_text(f'✅ Shortener <code>#{new_id}</code> added.')
    await _add_shortener_flow(client, message)


@Client.on_callback_query(filters.regex('^add_shortner$'))
async def add_shortner_callback(client, query):
    if not _is_admin(client, query.from_user.id):
        return await query.answer('Admins only', show_alert=True)
    await query.answer()
    await query.message.edit_text('Send: <code>domain.com API_KEY</code> within 60 seconds.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ BACK', 'shortner')]]))
    try:
        reply = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
        parts = reply.text.strip().split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError
        domain = parts[0].replace('https://', '').replace('http://', '').strip('/')
        api_key = parts[1].strip()
        if '.' not in domain or not api_key:
            raise ValueError
        items = _shortners(client)
        new_id = max([int(x.get('id', 0)) for x in items] or [0]) + 1
        items.append({'id': new_id, 'url': domain, 'api': api_key, 'enabled': True})
        await _save(client)
        await query.message.edit_text(f'✅ Shortener <code>#{new_id}</code> added.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ BACK', 'shortner')]]))
    except Exception:
        await query.message.edit_text('❌ Invalid format or timeout.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ BACK', 'shortner')]]))


async def manage_shortners(client, query):
    if not _is_admin(client, query.from_user.id):
        return
    rows = []
    for item in _shortners(client):
        sid = item['id']
        status = '🟢' if item.get('enabled', True) else '🔴'
        rows.append([
            InlineKeyboardButton(f'{status} #{sid} {item["url"]}', f'noop_{sid}'),
            InlineKeyboardButton('⚡ ON/OFF', f'toggle_provider_{sid}'),
            InlineKeyboardButton('❌ REMOVE', f'remove_provider_{sid}'),
        ])
    rows.append([InlineKeyboardButton('◂ BACK', 'shortner')])
    await query.message.edit_text('📋 <b>MANAGE SHORTENERS</b>', reply_markup=InlineKeyboardMarkup(rows))


@Client.on_callback_query(filters.regex('^manage_shortners$'))
async def manage_shortners_callback(client, query):
    await query.answer()
    await manage_shortners(client, query)


@Client.on_message(filters.command('list_shorteners') & filters.private)
async def list_shorteners(client, message):
    if not _is_admin(client, message.from_user.id):
        return
    items = _shortners(client)
    text = '<b>📋 SHORTENERS</b>\n\n' + ('\n'.join(
        f"{'🟢' if x.get('enabled', True) else '🔴'} <code>#{x['id']}</code> • <code>{x['url']}</code>"
        for x in items
    ) or 'No shorteners configured.')
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ OPEN PANEL', 'shortner')]]))


@Client.on_message(filters.command(['toggle_shortener', 'toggle_shortner']) & filters.private)
async def toggle_shortener_command(client, message):
    if not _is_admin(client, message.from_user.id):
        return
    args = message.command[1:]
    if len(args) != 1 or not args[0].isdigit():
        return await message.reply_text('Usage: <code>/toggle_shortener ID</code>')
    sid = int(args[0])
    for item in _shortners(client):
        if int(item['id']) == sid:
            item['enabled'] = not item.get('enabled', True)
            await _save(client)
            return await message.reply_text(f"✅ Shortener #{sid} is now {'🟢 ENABLED' if item['enabled'] else '🔴 DISABLED'}.")
    await message.reply_text('❌ Shortener not found.')


@Client.on_message(filters.command(['rem_shortener', 'rem_shortner']) & filters.private)
async def rem_shortener_command(client, message):
    if not _is_admin(client, message.from_user.id):
        return
    args = message.command[1:]
    if len(args) != 1 or not args[0].isdigit():
        return await message.reply_text('Usage: <code>/rem_shortener ID</code>')
    sid = int(args[0])
    items = _shortners(client)
    if not any(int(x['id']) == sid for x in items):
        return await message.reply_text('❌ Shortener not found.')
    client.shortners = [x for x in items if int(x['id']) != sid]
    await _save(client)
    await message.reply_text(f'✅ Shortener #{sid} removed.')


@Client.on_callback_query(filters.regex('^toggle_provider_'))
async def toggle_provider(client, query):
    if not _is_admin(client, query.from_user.id):
        return await query.answer('Admins only', show_alert=True)
    sid = int(query.data.rsplit('_', 1)[1])
    for item in _shortners(client):
        if int(item['id']) == sid:
            item['enabled'] = not item.get('enabled', True)
            break
    await _save(client)
    await query.answer('Updated')
    await manage_shortners(client, query)


@Client.on_callback_query(filters.regex('^remove_provider_'))
async def remove_provider(client, query):
    if not _is_admin(client, query.from_user.id):
        return await query.answer('Admins only', show_alert=True)
    sid = int(query.data.rsplit('_', 1)[1])
    client.shortners = [x for x in _shortners(client) if int(x['id']) != sid]
    await _save(client)
    await query.answer('Removed')
    await manage_shortners(client, query)


@Client.on_callback_query(filters.regex('^set_tutorial_link$'))
async def set_tutorial_link(client, query):
    if not _is_admin(client, query.from_user.id):
        return await query.answer('Admins only', show_alert=True)
    await query.answer()
    await query.message.edit_text('Send tutorial URL within 60 seconds.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ BACK', 'shortner')]]))
    try:
        reply = await client.listen(user_id=query.from_user.id, filters=filters.text, timeout=60)
        link = reply.text.strip()
        if not link.startswith(('http://', 'https://')):
            raise ValueError
        client.tutorial_link = link
        await client.mongodb.update_shortner_setting('tutorial_link', link)
        await query.message.edit_text('✅ Tutorial link updated.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ BACK', 'shortner')]]))
    except Exception:
        await query.message.edit_text('❌ Invalid URL or timeout.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ BACK', 'shortner')]]))


@Client.on_callback_query(filters.regex('^test_shortner$'))
async def test_shortner(client, query):
    if not _is_admin(client, query.from_user.id):
        return await query.answer('Admins only', show_alert=True)
    await query.answer()
    results = []
    for item in _shortners(client):
        try:
            domain = str(item['url']).replace('https://', '').replace('http://', '').strip('/')
            response = requests.get(f'https://{domain}/api', params={'api': item['api'], 'url': 'https://google.com'}, timeout=10)
            data = response.json()
            results.append(f"{'✅' if data.get('status') == 'success' else '❌'} #{item['id']} <code>{item['url']}</code>")
        except Exception:
            results.append(f"❌ #{item['id']} <code>{item['url']}</code>")
    await query.message.edit_text('🔄 <b>SHORTENER TEST RESULTS</b>\n\n' + '\n'.join(results), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ BACK', 'shortner')]]))


@Client.on_callback_query(filters.regex('^noop_'))
async def noop(client, query):
    await query.answer()
