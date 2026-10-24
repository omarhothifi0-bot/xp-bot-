import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# إعدادات البوت الأساسية (Basic Bot Settings)
# ==========================================
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "PUT_YOUR_TOKEN_HERE")
PREFIX = "-"

# ==========================================
# إعدادات نقاط الشات (Chat XP Settings)
# ==========================================
# كم نقطة (XP) يأخذ العضو على كل رسالة (بعد انتهاء الكول داون)
CHAT_XP_PER_MESSAGE = 5

# وقت الانتظار بالثواني بين كل رسالة ورسالة لمنع السبام (Cooldown)
CHAT_COOLDOWN_SECONDS = 45

# أيديات رومات الشات العام (إذا تركتها فاضية [] رح يحسب كل الرومات الكتابية كـ inpublic)
# مثال: PUBLIC_CHANNEL_IDS = [123456789012345678]
PUBLIC_CHANNEL_IDS = []

# ==========================================
# إعدادات نقاط الفويس (Voice XP Settings)
# ==========================================
# كم نقطة يأخذ العضو عن كل دقيقة يقضيها بالفويس وهو فاتح السماعة (Undeafen)
VOICE_XP_PER_MINUTE_UNDEAFEN = 2

# كم نقطة يأخذ العضو عن كل دقيقة يقضيها بالفويس وهو مسكر السماعة (Deafen)
VOICE_XP_PER_MINUTE_DEAFEN = 2

# تجاهل روم الـ AFK الرسمي بالسيرفر؟ (True = نعم، لا يحسب فيه نقاط)
IGNORE_AFK_CHANNEL = True

# ==========================================
# إعدادات الرتب التلقائية مع اللفل (Auto Roles)
# ==========================================
# ضع اللفل وجنبه اسم الرتبة أو الـ ID تبعها في الديسكورد
# إذا كتبنا اسم الرتبة ومش موجودة، البوت بيحاول يدور عليها أو ينشئها تلقائياً
CHAT_LEVEL_ROLES = {
    5: "Chat Level 5",
    10: "Chat Level 10",
    20: "Chat Level 20",
    30: "Chat Level 30",
    50: "Chat Legend",
}

VOICE_LEVEL_ROLES = {
    5: "Voice Level 5",
    10: "Voice Level 10",
    20: "Voice Level 20",
    30: "Voice Level 30",
    50: "Voice King",
}

# روم إشعارات الترقية باللفل (ضع ID الروم، أو 0 لإرسال التهنئة بنفس الشات أو إيقافها)
LEVEL_UP_CHANNEL_ID = 0
SEND_LEVEL_UP_MESSAGE = True
