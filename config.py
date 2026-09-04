import logging
from logging.handlers import RotatingFileHandler

# Bot Configuration
LOG_FILE_NAME = "bot.log2"
PORT = "8080"
OWNER_ID = 8980698496

MSG_EFFECT = 5046509860389126442

SHORT_URL = "https://linkshortify.com" # shortner url 
SHORT_API = "1ac53c500528c1bf5f71acc484967c3e3d5887c1" 
SHORT_TUT = "https://t.me/SHORTNER_OPENING_VERSE"

# Bot Configuration
SESSION = "ShortnerBot2"
TOKEN = "8905059366:AAF1W7JyRMgu_MoKN4bC8YjRxbSrpK6AZc8"
API_ID = "21592881"
API_HASH = "eba06a0d465f1d1797f0e92e97ac68ad"
WORKERS = 5

DB_URI = "mongodb+srv://testsccount01_db_user:BJX9YV3pOkYxw2H0@cluster0.4gue04w.mongodb.net/?appName=Cluster0"
DB_NAME = "ShortnerBot"

FSUBS = [] # Force Subscription Channels [channel_id, request_enabled, timer_in_minutes]
# Database Channel (Primary)
DB_CHANNEL =  -1004297078456  # just put channel id dont add ""
# Multiple Database Channels (can be set via bot settings)
# DB_CHANNELS = {
#     "-1002595092736": {"name": "Primary DB", "is_primary": True, "is_active": True},
#     "-1001234567890": {"name": "Secondary DB", "is_primary": False, "is_active": True}
# }
# Auto Delete Timer (seconds)
AUTO_DEL = 180
# Admin IDs
ADMINS = [7203919038,6901528008]
# Bot Settings
DISABLE_BTN = True
PROTECT = False

# Messages Configuration
MESSAGES = {
    "START": "<b>›› ʜᴇʏ!! {mention}× sᴇɴᴘᴀɪ 🎊\n</b><blockquote><b>ʟᴏᴠᴇ ᴍᴏᴠɪᴇs ᴀɴᴅ sᴇʀɪᴇs? ɪ ᴀᴍ ᴍᴀᴅᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴛᴏ ғɪɴᴅ ᴡʜᴀᴛ ʏᴏᴜ'ʀᴇ ʟᴏᴏᴋɪɴɢ ꜰᴏʀ..</b></blockquote>\n<blockquote>››ᴍᴀɪɴᴛᴀɪɴᴇᴅ ʙʏ : <a href='https://t.me/Bruce_Wayne_01b'>彡 𝕭𝕽𝖀𝕮𝕰 彡</a></blockquote>",
    "FSUB": "<blockquote>🎬 𝗕𝗲𝗳𝗼𝗿𝗲 𝘄𝗲 𝗰𝗼𝗻𝘁𝗶𝗻𝘂𝗲...</blockquote>\n<blockquote>📢 𝗣𝗹𝗲𝗮𝘀𝗲 𝗷𝗼𝗶𝗻 𝘁𝗵𝗲 𝘂𝗽𝗱𝗮𝘁𝗲 𝗰𝗵𝗮𝗻𝗻𝗲𝗹(𝘀) 𝗹𝗶𝘀𝘁𝗲𝗱 𝗯𝗲𝗹𝗼𝘄.</blockquote>\n✦ 𝗧𝗵𝗶𝘀 𝗵𝗲𝗹𝗽𝘀 𝘂𝘀 𝗸𝗲𝗲𝗽 𝘁𝗵𝗲 𝘀𝗲𝗿𝘃𝗶𝗰𝗲 𝘂𝗽𝗱𝗮𝘁𝗲𝗱.\n<blockquote>🍿 𝗔𝗳𝘁𝗲𝗿 𝗷𝗼𝗶𝗻𝗶𝗻𝗴 𝗰𝗹𝗶𝗰𝗸 𝗧𝗿𝘆 𝗔𝗴𝗮𝗶𝗻 𝘁𝗼 𝗿𝗲𝗰𝗲𝗶𝘃𝗲 𝘆𝗼𝘂𝗿 𝗳𝗶𝗹𝗲.</blockquote>",
    "ABOUT": "<b>›› ғᴏʀ ᴍᴏʀᴇ: <a href='https://t.me/movies_alliance_18'>Cʟɪᴄᴋ ʜᴇʀᴇ</a>\n<blockquote expandable>›› ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ: <a href='https://t.me/HEAVEN_ALLIANCE'>𝗛𝗘𝗔𝗩𝗘𝗡 𝗔𝗟𝗟𝗜𝗔𝗡𝗖𝗘</a> \n›› ᴏᴡɴᴇʀ: @Bruce_Wayne_01b\n›› ʟᴀɴɢᴜᴀɢᴇ: <a href='https://docs.python.org/3/'>Pʏᴛʜᴏɴ 3</a> \n›› ʟɪʙʀᴀʀʏ: <a href='https://docs.pyrogram.org/'>Pʏʀᴏɢʀᴀᴍ ᴠ2</a> \n›› ᴅᴀᴛᴀʙᴀsᴇ: <a href='https://www.mongodb.com/docs/'>Mᴏɴɢᴏ ᴅʙ</a> \n›› ᴅᴇᴠᴇʟᴏᴘᴇʀ: @BRUCE_WAYNE_01B</b></blockquote>",
    "REPLY": "<b>For More Join - @HEAVEN_ALLIANCE</b>",
    "SHORT_MSG": "<blockquote>🔐 𝗦𝗲𝗰𝘂𝗿𝗲 𝗮𝗰𝗰𝗲𝘀𝘀 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗲𝗻𝗮𝗯𝗹𝗲𝗱.</blockquote>\n<blockquote>📥 𝗖𝗹𝗶𝗰𝗸 𝘁𝗵𝗲 𝗯𝘂𝘁𝘁𝗼𝗻 𝗯𝗲𝗹𝗼𝘄 𝘁𝗼 𝗿𝗲𝗰𝗲𝗶𝘃𝗲 𝘆𝗼𝘂𝗿 𝗳𝗶𝗹𝗲.</blockquote>\n✦ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗮𝗹𝗹𝗼𝘄 𝗮 𝗺𝗼𝗺𝗲𝗻𝘁 𝗳𝗼𝗿 𝘁𝗵𝗲 𝘀𝘆𝘀𝘁𝗲𝗺 𝘁𝗼 𝗿𝗲𝘀𝗽𝗼𝗻𝗱.\n<blockquote>⍟ 𝗥𝗲𝗼𝗽𝗲𝗻 𝘁𝗵𝗲 𝗹𝗶𝗻𝗸 𝗶𝗳 𝘆𝗼𝘂 𝗿𝗲𝗰𝗲𝗶𝘃𝗲 𝗮𝗻 𝗲𝗿𝗿𝗼𝗿.</blockquote>",
    "START_PHOTO": "https://img.sanishtech.com/u/cb047eb18151280df2978b4c973ddbb8.jpg",
    "FSUB_PHOTO": "https://i.ibb.co/KxwHyn0S/upscalemedia-transformed-1.png",
    "SHORT_PIC": "https://img.sanishtech.com/u/cb047eb18151280df2978b4c973ddbb8.jpg",
    "SHORT": "https://img.sanishtech.com/u/517539c66163ee8a2a11ee8014ca77de.jpg"
}

def LOGGER(name: str, client_name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    formatter = logging.Formatter(
        f"[%(asctime)s - %(levelname)s] - {client_name} - %(name)s - %(message)s",
        datefmt='%d-%b-%y %H:%M:%S'
    )
    file_handler = RotatingFileHandler(LOG_FILE_NAME, maxBytes=50_000_000, backupCount=10)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
