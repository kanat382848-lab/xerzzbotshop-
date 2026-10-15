import asyncio
import logging
import os
import uuid
import re
import time
import json
import random
import aiohttp
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BALA_BASE_URL = os.getenv("BALA_BASE_URL", "https://158.247.231.14/api/v1")
BALA_API_KEY = os.getenv("BALA_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "xerzzshop_bot")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# =========================================================
# 💳 ТӨЛЕМ ДЕРЕКТЕРІ
# =========================================================
PAYMENT_NUMBER = "8 778 293 51 78"
PAYMENT_HOLDER = "Бердибек Қанат"

MIN_BALANCE = 100
MAX_BALANCE = 10000


# =========================================================
# 💾 ЖЕРГІЛІКТІ ДЕРЕКҚОР (JSON файлдар)
# =========================================================
DATA_FILE = "users_data.json"
LUCKY_FILE = "lucky_data.json"
REFERRAL_FILE = "referral_data.json"
DEPOSITS_FILE = "deposits.json"


def load_json(filename, default=None):
    if default is None:
        default = {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Save error: {e}")


# Пайдаланушылар дерекқоры
USERS_DB = load_json(DATA_FILE)
LUCKY_DB = load_json(LUCKY_FILE)
REFERRAL_DB = load_json(REFERRAL_FILE)
DEPOSITS_DB = load_json(DEPOSITS_FILE, [])


def save_all():
    save_json(DATA_FILE, USERS_DB)
    save_json(LUCKY_FILE, LUCKY_DB)
    save_json(REFERRAL_FILE, REFERRAL_DB)
    save_json(DEPOSITS_FILE, DEPOSITS_DB)


# =========================================================
# 💱 ВАЛЮТА
# =========================================================
RATES = {"kz": 1.0, "ru": 0.18, "en": 0.002}
CURRENCY_SYMBOL = {"kz": "₸", "ru": "₽", "en": "$"}


def format_price(tg_price: float, lang: str) -> str:
    rate = RATES.get(lang, 1.0)
    converted = tg_price * rate
    if lang == "en":
        return f"${converted:.2f}"
    elif lang == "ru":
        return f"{converted:.0f}₽"
    else:
        return f"{converted:.0f}₸"


# =========================================================
# 🌐 ТІЛ ЖҮЙЕСІ
# =========================================================
TRANSLATIONS = {
    "kz": {
        "hello": "Сәлем", "powered": "Қуаттандырылған",
        "direct_deals": "Тікелей жеткізушілермен мәмілелер",
        "instant_delivery": "Төлемнен кейін лезде жеткізу",
        "discounted": "Кепілдендірілген жеңілдік бағалар",
        "support_247": "24/7 админ қолдау",
        "tap_button": "Төмендегі батырманы басыңыз.",
        "your_balance": "Сіздің балансыңыз",
        "shop": "Дүкен", "add_balance": "Баланс толтыру",
        "my_profile": "Менің профилім", "how_to_use": "Қалай қолдану",
        "lucky": "Сәттілік", "share": "Бөлісу", "support": "Қолдау",
        "back": "Артқа", "back_to_menu": "Артқа",
        "choose_product": "Тауарды таңдаңыз",
        "choose_plan": "Жоспарды таңдаңыз",
        "your_tier": "Сіздің деңгейіңіз",
        "purchased": "Сәтті сатып алынды",
        "your_key": "Сіздің кілтіңіз",
        "copy_key": "Кілтті көшіру",
        "error": "Қате", "select_device": "Құрылғы түрін таңдаңыз",
        "id": "ID", "name": "Аты", "username": "Логин",
        "balance": "Баланс", "keys": "Кілттер",
        "balance_select": "Баланс толтыру сомасын таңдаңыз:",
        "balance_custom": "Баланс толтыру (Custom)",
        "min_max": "Мин", "max": "Макс",
        "balance_min": "Ең аз сома", "balance_max": "Ең көп сома",
        "send_receipt": "Чекті жіберіңіз",
        "receipt_sent": "Чек қабылданды!",
        "receipt_thanks": "Админ тексереді. Біраз күте тұрыңыз.",
        "send_custom_amount": "Соманы жазыңыз (тек сан):",
        "choose_payment": "Төлем әдісін таңдаңыз:",
        "kaspi": "Kaspi Bank", "halyk": "Halyk Bank",
        "payment_info": "Төлем ақпараты:",
        "copy_number": "Нөмірді көшіру",
        "i_paid": "Төледім ✅",
        "how_to_use_text": (
            "📖 <b>ҚАЛАЙ ҚОЛДАНУ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ <b>Баланс толтыру:</b>\n"
            "   💰 Баланс → соманы таңдаңыз → төлеңіз → чек жіберіңіз\n\n"
            "2️⃣ <b>Тауар сатып алу:</b>\n"
            "   🛒 Дүкен → санат → тауар → жоспар\n\n"
            "3️⃣ <b>Кілтті алу:</b>\n"
            "   Сатып алған соң кілт автоматты түрде шығады\n\n"
            "4️⃣ <b>Реферал:</b>\n"
            "   🔗 Бөлісу → сілтемені досқа жіберіңіз\n"
        ),
        "share_text": (
            "🔗 <b>БӨЛІСУ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Сіздің реферал сілтемеңіз:\n"
        ),
        "lucky_text": (
            "🎁 <b>СӘТТІЛІК ОЙЫНЫ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Аптасына 1 рет ойнай аласыз!\n"
            "Сыйақы: 0.1₸ - 10₸\n\n"
        ),
        "lucky_win": "🎉 <b>Сіз ұттыңыз!</b>\n\n💰 +",
        "lucky_already": "❌ <b>Сіз бұл аптада ойнадыңыз!</b>\n\nКелесі аптада қайталап көріңіз.",
        "support_text": (
            "🆘 <b>ҚОЛДАУ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Админге хабарлама жазыңыз:"
        ),
        "support_sent": "✅ Хабарлама админге жіберілді!",
        "admin_panel": "Админ панель",
        "stats": "Статистика", "users": "Пайдаланушылар",
        "deposits": "Толтырулар", "broadcast": "Хабарлама",
        "reload": "Қайта жүктеу", "close": "Жабу",
    },
    "ru": {
        "hello": "Привет", "powered": "Работает на",
        "direct_deals": "Прямые сделки с поставщиками",
        "instant_delivery": "Мгновенная доставка после оплаты",
        "discounted": "Гарантированные скидки",
        "support_247": "Поддержка 24/7",
        "tap_button": "Нажмите кнопку ниже.",
        "your_balance": "Ваш баланс",
        "shop": "Магазин", "add_balance": "Пополнить баланс",
        "my_profile": "Мой профиль", "how_to_use": "Как использовать",
        "lucky": "Удача", "share": "Поделиться", "support": "Поддержка",
        "back": "Назад", "back_to_menu": "Назад",
        "choose_product": "Выберите товар",
        "choose_plan": "Выберите план", "your_tier": "Ваш уровень",
        "purchased": "Успешно куплено", "your_key": "Ваш ключ",
        "copy_key": "Копировать ключ",
        "error": "Ошибка", "select_device": "Выберите устройство",
        "id": "ID", "name": "Имя", "username": "Логин",
        "balance": "Баланс", "keys": "Ключи",
        "balance_select": "Выберите сумму пополнения:",
        "balance_custom": "Пополнение (Custom)",
        "min_max": "Мин", "max": "Макс",
        "balance_min": "Мин. сумма", "balance_max": "Макс. сумма",
        "send_receipt": "Отправьте чек",
        "receipt_sent": "Чек принят!",
        "receipt_thanks": "Админ проверит. Подождите.",
        "send_custom_amount": "Напишите сумму (только число):",
        "choose_payment": "Выберите способ оплаты:",
        "kaspi": "Kaspi Bank", "halyk": "Halyk Bank",
        "payment_info": "Информация об оплате:",
        "copy_number": "Копировать номер",
        "i_paid": "Оплатил ✅",
        "how_to_use_text": (
            "📖 <b>КАК ИСПОЛЬЗОВАТЬ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ <b>Пополнение:</b>\n"
            "   💰 Баланс → выберите сумму → оплатите → отправьте чек\n\n"
            "2️⃣ <b>Покупка:</b>\n"
            "   🛒 Магазин → категория → товар → план\n\n"
            "3️⃣ <b>Получение ключа:</b>\n"
            "   После покупки ключ появится автоматически\n\n"
            "4️⃣ <b>Реферал:</b>\n"
            "   🔗 Поделиться → отправьте ссылку друзьям\n"
        ),
        "share_text": "🔗 <b>ПОДЕЛИТЬСЯ</b>\n━━━━━━━━━━━━━━━━━━━━\n\nВаша реферальная ссылка:\n",
        "lucky_text": "🎁 <b>ИГРА УДАЧИ</b>\n━━━━━━━━━━━━━━━━━━━━\n\nРаз в неделю!\nПриз: 0.1₸ - 10₸\n\n",
        "lucky_win": "🎉 <b>Вы выиграли!</b>\n\n💰 +",
        "lucky_already": "❌ <b>Вы уже играли на этой неделе!</b>\n\nПопробуйте на следующей.",
        "support_text": "🆘 <b>ПОДДЕРЖКА</b>\n━━━━━━━━━━━━━━━━━━━━\n\nНапишите сообщение админу:",
        "support_sent": "✅ Сообщение отправлено админу!",
        "admin_panel": "Админ панель",
        "stats": "Статистика", "users": "Пользователи",
        "deposits": "Пополнения", "broadcast": "Рассылка",
        "reload": "Перезагрузить", "close": "Закрыть",
    },
    "en": {
        "hello": "Hello", "powered": "Powered by",
        "direct_deals": "Direct deals with every supplier",
        "instant_delivery": "Instant delivery after payment",
        "discounted": "Guaranteed discounted prices",
        "support_247": "24/7 admin support",
        "tap_button": "Tap any button below to begin.",
        "your_balance": "Your Balance",
        "shop": "Shop", "add_balance": "Add Balance",
        "my_profile": "My Profile", "how_to_use": "How To Use",
        "lucky": "Lucky", "share": "Share", "support": "Support",
        "back": "Back", "back_to_menu": "Back",
        "choose_product": "Choose a product",
        "choose_plan": "Choose your plan", "your_tier": "Your Tier",
        "purchased": "Purchased successfully", "your_key": "Your key",
        "copy_key": "Copy key",
        "error": "Error", "select_device": "Select device type",
        "id": "ID", "name": "Name", "username": "Username",
        "balance": "Balance", "keys": "Keys",
        "balance_select": "Select deposit amount:",
        "balance_custom": "Deposit (Custom)",
        "min_max": "Min", "max": "Max",
        "balance_min": "Min amount", "balance_max": "Max amount",
        "send_receipt": "Send receipt",
        "receipt_sent": "Receipt accepted!",
        "receipt_thanks": "Admin will check. Please wait.",
        "send_custom_amount": "Write amount (number only):",
        "choose_payment": "Choose payment method:",
        "kaspi": "Kaspi Bank", "halyk": "Halyk Bank",
        "payment_info": "Payment information:",
        "copy_number": "Copy number",
        "i_paid": "I paid ✅",
        "how_to_use_text": (
            "📖 <b>HOW TO USE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ <b>Deposit:</b>\n"
            "   💰 Balance → select amount → pay → send receipt\n\n"
            "2️⃣ <b>Buy:</b>\n"
            "   🛒 Shop → category → product → plan\n\n"
            "3️⃣ <b>Get key:</b>\n"
            "   Key appears automatically\n\n"
            "4️⃣ <b>Referral:</b>\n"
            "   🔗 Share → send link to friends\n"
        ),
        "share_text": "🔗 <b>SHARE</b>\n━━━━━━━━━━━━━━━━━━━━\n\nYour referral link:\n",
        "lucky_text": "🎁 <b>LUCKY GAME</b>\n━━━━━━━━━━━━━━━━━━━━\n\nOnce a week!\nPrize: 0.1₸ - 10₸\n\n",
        "lucky_win": "🎉 <b>You won!</b>\n\n💰 +",
        "lucky_already": "❌ <b>You already played this week!</b>\n\nTry next week.",
        "support_text": "🆘 <b>SUPPORT</b>\n━━━━━━━━━━━━━━━━━━━━\n\nWrite a message to admin:",
        "support_sent": "✅ Message sent to admin!",
        "admin_panel": "Admin Panel",
        "stats": "Statistics", "users": "Users",
        "deposits": "Deposits", "broadcast": "Broadcast",
        "reload": "Reload", "close": "Close",
    },
}


def t(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)


USER_LANGS = {}


def get_user_lang(user_id: int) -> str:
    return USER_LANGS.get(user_id, "kz")


def set_user_lang(user_id: int, lang: str):
    USER_LANGS[user_id] = lang


# =========================================================
# 📌 ЭМОДЗИ ID-ЛЕРІ
# =========================================================
E_STORE     = "5983399041197675256"
E_SPARK     = "5893321843149902412"
E_WAVE      = "5458904472598095631"
E_KEY       = "6005570495603282482"
E_DROP      = "6005553599201940235"
E_MONEY     = "5897958754267174109"
E_SEND      = "6143315044588326242"
E_SHOP_CART = "5312361253610475399"
E_FIRE      = "5204076520963842994"
E_DEVICE    = "5406809207947142040"
E_BACK      = "5942569381274850937"
E_ANDROID   = "6199417621100629765"
E_PC        = "5967816500415827773"
E_IOS       = "6269378983335303174"

B_CART      = "5431499171045581032"
B_DOLLAR    = "6229028551568397202"
B_CROWN     = "5942901773088857071"
B_LOCK      = "5303281151580844020"
B_GIFT      = "5204076520963842994"
B_SHARE     = "6143315044588326242"
B_SUPPORT   = "5240464278464515740"
B_ADMIN     = "5470012829983580233"


# =========================================================
# 🎯 ID → АТЫ
# =========================================================
ID_TO_NAME = {
    98: "DRIP PROXY", 99: "DRIP PROXY", 100: "DRIP PROXY", 101: "DRIP PROXY",
    89: "DRIP APKMOD", 90: "DRIP APKMOD", 91: "DRIP APKMOD", 92: "DRIP APKMOD", 93: "DRIP APKMOD",
    73: "HG BRUTAL VERSION", 74: "HG BRUTAL VERSION", 75: "HG BRUTAL VERSION", 76: "HG BRUTAL VERSION",
    94: "HG PROXY", 95: "HG PROXY", 96: "HG PROXY", 97: "HG PROXY",
    103: "MIGUL BASIC", 104: "MIGUL BASIC", 105: "MIGUL BASIC",
    106: "MIGUL PRO", 107: "MIGUL PRO", 108: "MIGUL PRO",
    82: "PUBG ZOLO", 83: "PUBG ZOLO", 84: "PUBG ZOLO",
    85: "PRIME HOOK", 86: "PRIME HOOK", 87: "PRIME HOOK", 88: "PRIME HOOK",
    109: "ABCD MOD", 110: "ABCD MOD", 111: "ABCD MOD", 112: "ABCD MOD",
    102: "IOS CERTIFICATE",
    113: "BR MODS PC", 114: "BR MODS PC", 115: "BR MODS PC",
    294: "GUILD GLORY", 295: "GUILD GLORY", 296: "GUILD GLORY",
}


# =========================================================
# 💰 ID → TG БАҒАСЫ
# =========================================================
ID_TO_PRICE = {
    109: 500, 110: 900, 111: 1600, 112: 3500,
    89: 300, 90: 700, 91: 1700, 92: 2500, 93: 4000,
    117: 500, 118: 1000, 119: 2000, 120: 3000, 121: 5000,
    85: 500, 86: 1000, 87: 1500, 88: 2000,
    82: 700, 83: 3000, 84: 5500,
    229: 500, 230: 1000, 231: 2000, 232: 3500, 233: 5000,
    221: 100, 222: 200, 223: 400, 224: 700, 225: 1200, 226: 1700, 227: 2500, 228: 5000,
    116: 100, 181: 200, 182: 400, 183: 700, 184: 1200, 185: 1700, 186: 2500, 187: 3500, 188: 5000,
    198: 200, 199: 400, 200: 600, 201: 1200, 202: 1800, 203: 3000, 204: 5000, 205: 10000,
    194: 300, 195: 500, 196: 800, 197: 2000,
    252: 500, 253: 2000, 254: 3000,
    94: 500, 95: 2000, 96: 3000, 97: 5000,
    248: 500, 249: 2000, 250: 3000, 251: 5000,
    259: 500, 260: 2000, 261: 3000, 262: 5000,
    218: 250, 219: 1500, 220: 3000,
    272: 500, 273: 2000, 274: 3000, 275: 5000,
    73: 500, 74: 2000, 75: 3000, 76: 5000,
    214: 500, 215: 2000, 216: 3000, 217: 5000,
    292: 500, 293: 2000,
    127: 2000, 128: 3000, 129: 5000,
    130: 2000, 131: 3000,
    77: 500, 78: 1000, 79: 2000, 80: 3000, 81: 5000,
    255: 200, 256: 800, 257: 1200, 258: 2000,
    269: 2000, 270: 3000, 271: 5000,
    243: 500, 244: 1200, 245: 1700, 246: 2500, 247: 4500,
    263: 250, 264: 500, 265: 800, 266: 1400, 267: 2000, 268: 3000,
    281: 100, 282: 200, 283: 400, 284: 700, 285: 1200, 286: 1700, 287: 2500,
    98: 500, 99: 1000, 100: 2500, 101: 5000,
    234: 100, 235: 200, 236: 400, 237: 700, 238: 1200, 239: 2000, 240: 2700, 241: 3300, 242: 4000,
    113: 350, 114: 2000, 115: 3500,
    288: 500, 289: 1500, 290: 2500, 291: 3500,
    102: 1500,
    103: 500, 104: 2000, 105: 3000,
    106: 1000, 107: 3000, 108: 5000,
    276: 500, 277: 1000, 278: 2000, 279: 3000, 280: 5000,
    294: 2000, 295: 4000, 296: 6000,
}


# =========================================================
# 🎨 ПРЕМИУМ ЭМОДЗИЛЕР
# =========================================================
PRODUCT_EMOJIS = {
    "PATO REGEDIT NON ROOT": "5942958105879911622",
    "Zrex mod": "5830151666023800699",
    "ZREX MOD": "5830151666023800699",
    "BALA MODS": "5470012829983580233",
    "Aimh@ck": "5942948845930420302",
    "AIMH@CK": "5942948845930420302",
    "AIM HACK": "5942948845930420302",
    "SILENT APKMOD": "5954090983233690091",
    "DRIP WIRE": "5789935155632151161",
    "DRIP APKMOD": "5789935155632151161",
    "HG PRIME PROXY": "5789487740298992735",
    "HG PROXY": "5789487740298992735",
    "PUBG ZOLO": "5830016739626196197",
    "PRIME HOOK": "5789423161170731369",
    "ABCD MOD": "5942977832664700642",
    "ANGRY MOD ROOT": "5830016739626196197",
    "BR MODS ROOT": "5792006910416790101",
    "GHOST ELITE STREAMER": "5825518839420428721",
    "HG SAFE VERSION": "5789864219952291426",
    "HG SAFE NORMAL VERSION": "5789864219952291426",
    "HG BRUTAL VERSION": "5789864219952291426",
    "PATO BLUE": "5803043541848432564",
    "PTO BLUE": "5803043541848432564",
    "PATO GREEN": "5803043541848432564",
    "PATO ORANGE": "5803033397135679303",
    "RAPID CORE ROOT": "5794092516470957001",
    "REAPER X PRO ROOT": "5834434104900197871",
    "REAPER x PRO ROOT": "5834434104900197871",
    "SILENT CHEATS ROOT": "5942999024033339772",
    "SILENT PROXY": "5942999024033339772",
    "STRICKS BR": "5832653093631697177",
    "TROLL MODZ": "5834743600243548047",
    "DRIP ROOT": "5789935155632151161",
    "DRIP PROXY": "5789935155632151161",
    "BR MOD PC": "5792006910416790101",
    "BR MODS PC": "5792006910416790101",
    "DUSTU AIMKILL PC": "5868462739944381572",
    "VELORA IOS": "5888803919806603389",
    "MIGUL BASIC": "5834513617629748928",
    "MIGUL PRO": "5834513617629748928",
    "IOS CERTIFICATE": "5764648441187670854",
    "GUILD GLORY": "5789935155632151161",
    "GLORY DIGITAL": "5789935155632151161",
}


def get_product_emoji_id(product_name: str) -> str:
    pn = product_name.upper()
    for keyword, emoji_id in PRODUCT_EMOJIS.items():
        if keyword.upper() in pn:
            return emoji_id
    return None


# =========================================================
# 🌐 BALA API
# =========================================================
HEADERS = {"X-API-Key": BALA_API_KEY, "Content-Type": "application/json"}
CATALOG = []
GROUPS = {}
PRODUCTS_BY_ID = {}

ME_CACHE = {"data": None, "time": 0}


async def bala_me():
    now = time.time()
    if ME_CACHE["data"] and (now - ME_CACHE["time"]) < 30:
        return ME_CACHE["data"]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BALA_BASE_URL}/me", headers=HEADERS, timeout=5) as r:
                data = await r.json()
                ME_CACHE["data"] = data
                ME_CACHE["time"] = now
                return data
    except Exception:
        return ME_CACHE["data"] or {"balance_pcoins": 0}


async def bala_catalog():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BALA_BASE_URL}/catalog", headers=HEADERS, timeout=15) as r:
                return await r.json()
    except Exception:
        return {}


async def bala_create_order(customer_ref: str, product_id: int, max_price: int):
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    headers = {**HEADERS, "Idempotency-Key": order_id}
    data = {"customer_ref": customer_ref, "product_id": product_id, "max_price_pcoins": max_price}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BALA_BASE_URL}/orders", headers=headers, json=data, timeout=30) as r:
                return await r.json(), order_id
    except Exception as e:
        return {"ok": False, "error": str(e)}, order_id


async def bala_customer_keys(customer_ref: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BALA_BASE_URL}/customers/keys", headers=HEADERS,
                params={"customer_ref": customer_ref}, timeout=10
            ) as r:
                return await r.json()
    except Exception:
        return {"keys": []}
def get_user_balance(user_id: int) -> float:
    """Пайдаланушының жеке балансын алу (жергілікті дерекқордан)"""
    uid = str(user_id)
    if uid not in USERS_DB:
        USERS_DB[uid] = {}
    return USERS_DB[uid].get("balance", 0.0)


def set_user_balance(user_id: int, amount: float):
    """Пайдаланушының балансын орнату"""
    uid = str(user_id)
    if uid not in USERS_DB:
        USERS_DB[uid] = {}
    USERS_DB[uid]["balance"] = amount
    save_all()


def add_user_balance(user_id: int, amount: float):
    """Пайдаланушының балансына қосу"""
    uid = str(user_id)
    current = get_user_balance(user_id)
    USERS_DB[uid]["balance"] = current + amount
    save_all()

# =========================================================
# 📋 САНАТТАР
# =========================================================
CATEGORIES_KEYWORDS = {
    "ANDROID NON-ROOT": [
        "PATO REGEDIT NON ROOT", "Zrex mod", "ZREX MOD", "BALA MODS",
        "Aimh@ck", "AIMH@CK", "AIM HACK", "SILENT APKMOD", "DRIP WIRE",
        "HG PRIME PROXY", "DRIP APKMOD", "HG PROXY", "PUBG ZOLO",
        "PRIME HOOK", "ABCD MOD",
    ],
    "ANDROID ROOT": [
        "ANGRY MOD ROOT", "BR MODS ROOT", "GHOST ELITE STREAMER ROOT",
        "HG SAFE VERSION", "HG SAFE NORMAL VERSION", "PATO BLUE",
        "PTO BLUE", "PATO GREEN", "PATO ORANGE", "RAPID CORE ROOT",
        "REAPER x PRO ROOT", "SILENT CHEATS ROOT", "SILENT PROXY",
        "STRICKS BR", "TROLL MODZ", "DRIP ROOT", "DRIP PROXY",
        "HG BRUTAL VERSION",
    ],
    "PC / COMPUTER": ["BR MOD PC", "BR MODS PC", "DUSTU AIMKILL PC"],
    "IOS / IPHONE": ["VELORA IOS", "MIGUL BASIC", "MIGUL PRO", "IOS CERTIFICATE"],
    "OTHER": ["GLORY DIGITAL", "GUILD GLORY"],
}


def match_product(product_name: str, keyword: str) -> bool:
    pn = product_name.upper().replace("-", "").replace("_", "").replace(" ", "")
    kw = keyword.upper().replace("-", "").replace("_", "").replace(" ", "")
    return kw in pn


def get_price(product: dict) -> int:
    for field in ["price_pcoins", "price", "price_pcoin", "cost", "amount"]:
        if field in product:
            try:
                return int(product[field])
            except (ValueError, TypeError):
                pass
    return 0


def get_product_id(product: dict) -> int:
    for field in ["id", "product_id", "productId"]:
        if field in product:
            try:
                return int(product[field])
            except (ValueError, TypeError):
                pass
    return 0


DURATION_PATTERNS = [
    r"\s*\d+\s*(?:DAY|DAYS|день|дня|дней|D|д)\b.*$",
    r"\s*\d+\s*(?:MONTH|MONTHS|месяц|месяцев|M|мес)\b.*$",
    r"\s*\d+\s*(?:HOUR|HOURS|час|часов|H|ч)\b.*$",
    r"\s*\d+\s*(?:YEAR|YEARS|год|лет|Y|г)\b.*$",
]


def get_group_name(product_name: str) -> str:
    name = product_name.strip()
    for pattern in DURATION_PATTERNS:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()
    return name if name else product_name


def get_duration_label(product_name: str) -> str:
    matches = re.findall(
        r"(\d+\s*(?:DAY|DAYS|день|дня|дней|D|MONTH|MONTHS|месяц|месяцев|HOUR|HOURS|час|часов|YEAR|год|лет|SQUAD))",
        product_name, re.IGNORECASE
    )
    if matches:
        return matches[-1].strip().upper()
    return "STANDARD"


async def load_catalog():
    global CATALOG, GROUPS, PRODUCTS_BY_ID
    
    # Егер каталог БАР болса — қайта жүктемейміз
    if GROUPS and len(GROUPS) > 0:
        print(f"✅ Catalog already loaded: {len(CATALOG)} тауар, {len(GROUPS)} топ")
        return
    
    try:
        data = await bala_catalog()
        
        # Егер API бос жауап берсе — ескісін сақтаймыз
        if not data or not data.get("products"):
            print(f"⚠️ BALA API empty response. Keeping old catalog.")
            return
        
        CATALOG = data.get("products") or data.get("items") or data.get("data") or []
        if isinstance(CATALOG, dict):
            CATALOG = list(CATALOG.values())
        
        if not CATALOG:
            print(f"⚠️ No products in catalog.")
            return

        PRODUCTS_BY_ID = {}
        used_ids = set()
        cat_products = {cat: [] for cat in CATEGORIES_KEYWORDS.keys()}

        for p in CATALOG:
            pid = get_product_id(p)
            if not pid:
                continue
            real_name = p.get("name") or p.get("title") or ""
            if pid in ID_TO_NAME:
                group_name = ID_TO_NAME[pid]
            else:
                group_name = get_group_name(real_name)
            p["_real_name"] = real_name
            p["_group_name"] = group_name
            PRODUCTS_BY_ID[pid] = p

            for cat_name, keywords in CATEGORIES_KEYWORDS.items():
                matched = False
                for kw in keywords:
                    if match_product(group_name, kw):
                        matched = True
                        break
                if matched and pid not in used_ids:
                    cat_products[cat_name].append(p)
                    used_ids.add(pid)
                    break

        new_groups = {}
        for cat_name, products in cat_products.items():
            if not products:
                continue
            groups = {}
            for p in products:
                gname = p.get("_group_name") or "?"
                groups.setdefault(gname, []).append(p)
            for gname, items in groups.items():
                items.sort(key=lambda x: ID_TO_PRICE.get(get_product_id(x), get_price(x)))
            new_groups[cat_name] = groups

        # Тек бос болмаса ғана ауыстырамыз
        if new_groups:
            GROUPS = new_groups
            print(f"✅ Catalog: {len(CATALOG)} тауар")
            for cat, groups in GROUPS.items():
                total = sum(len(v) for v in groups.values())
                print(f"   📂 {cat}: {len(groups)} топ, {total} тауар")
        else:
            print(f"⚠️ No categories matched. Keeping old catalog.")
    except Exception as e:
        print(f"❌ {e}")
        import traceback
        traceback.print_exc()


# =========================================================
# 🎨 БАТЫРМАЛАР
# =========================================================
def language_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kz", style="success")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru", style="primary")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en", style="danger")],
    ])


def main_menu(lang: str = "kz", user_id: int = 0):
    buttons = []
    if ADMIN_ID != 0 and user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(
            text="🛡️ ADMIN PANEL", callback_data="admin_panel",
            icon_custom_emoji_id=B_ADMIN, style="danger"
        )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "shop"), callback_data="shop",
        icon_custom_emoji_id=B_CART, style="success"
    )])
    buttons.append([
        InlineKeyboardButton(text=t(lang, "add_balance"), callback_data="add_balance",
                              icon_custom_emoji_id=B_DOLLAR, style="success"),
        InlineKeyboardButton(text=t(lang, "my_profile"), callback_data="profile",
                              icon_custom_emoji_id=B_CROWN, style="primary")
    ])
    buttons.append([
        InlineKeyboardButton(text=t(lang, "how_to_use"), callback_data="how_to",
                              icon_custom_emoji_id=B_LOCK, style="primary"),
        InlineKeyboardButton(text=t(lang, "lucky"), callback_data="lucky",
                              icon_custom_emoji_id=B_GIFT, style="danger")
    ])
    buttons.append([
        InlineKeyboardButton(text=t(lang, "share"), callback_data="share",
                              icon_custom_emoji_id=B_SHARE, style="primary"),
        InlineKeyboardButton(text=t(lang, "support"), callback_data="support",
                              icon_custom_emoji_id=B_SUPPORT, style="danger")
    ])
    buttons.append([InlineKeyboardButton(
        text="🌐 Тіл / Язык / Language", callback_data="choose_lang", style="primary"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def shop_menu(lang: str = "kz"):
    buttons = []
    for cat_name in GROUPS.keys():
        if "NON-ROOT" in cat_name or "NONROOT" in cat_name:
            icon = E_ANDROID
        elif "ROOT" in cat_name:
            icon = E_ANDROID
        elif "PC" in cat_name:
            icon = E_PC
        elif "IOS" in cat_name:
            icon = E_IOS
        else:
            icon = None
        buttons.append([InlineKeyboardButton(
            text=cat_name, callback_data=f"cat_{cat_name}",
            icon_custom_emoji_id=icon, style="primary"
        )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "back"), callback_data="back_menu",
        icon_custom_emoji_id=E_BACK, style="danger"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =========================================================
# 📌 /START
# =========================================================
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"
    
    print(f"🔍 START: user_id={user_id}, name={user_name}")
    
    # Дерекқорға сақтау
    USERS_DB[str(user_id)] = {
        "first_name": user_name,
        "username": message.from_user.username,
        "joined": datetime.now().isoformat(),
    }
    save_all()
    
    # Каталогты тек бір рет жүктейміз
    if not GROUPS or len(GROUPS) == 0:
        await load_catalog()
    
    # Тіл таңдау
    await message.answer(
        "🌐 <b>Тілді таңдаңыз / Выберите язык / Choose language:</b>",
        reply_markup=language_menu()
    )


@dp.callback_query(F.data.startswith("lang_"))
async def lang_handler(callback: types.CallbackQuery):
    lang = callback.data[5:]
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name or "User"
    
    print(f"🔍 LANG SELECTED: user_id={user_id}, name={user_name}, lang={lang}")
    
    set_user_lang(user_id, lang)
    
    # Хабарламаны өшіріп, басты мәзірді жібереміз
    await callback.message.delete()
    
    # Жаңа хабарлама — НАҚТЫ пайдаланушымен
    await show_main_menu(
        callback.message,  # осы хабарлама объектісі (chat ақпараты үшін)
        lang=lang,
        user_id=user_id,
        user_name=user_name
    )
    await callback.answer()


async def show_main_menu(message: types.Message, lang: str = "kz", user_id: int = 0, user_name: str = "User"):
    """
    message — жіберу үшін (edit немесе answer)
    user_id — нақты пайдаланушы ID
    user_name — нақты пайдаланушы аты
    """
    if user_id == 0:
        user_id = message.from_user.id
    if user_name == "User":
        user_name = message.from_user.first_name or "User"
    
    print(f"🔍 show_main_menu: user_id={user_id}, name={user_name}")
    
    user_balance = get_user_balance(user_id)

    text = (
        f'<tg-emoji emoji-id="{E_STORE}">🏪</tg-emoji> — <b>XERZZ KEYSHOP</b>'
        f'<tg-emoji emoji-id="{E_SPARK}">✨</tg-emoji> — '
        f'<tg-emoji emoji-id="{E_STORE}">🏪</tg-emoji>\n\n'
        f'<tg-emoji emoji-id="{E_WAVE}">👋</tg-emoji> {t(lang, "hello")}, <b>{user_name}</b>!\n\n'
        f'<tg-emoji emoji-id="{E_KEY}">🔑</tg-emoji> {t(lang, "powered")} <b>XERZZ KEYSHOP</b> '
        f'<tg-emoji emoji-id="{E_SPARK}">✨</tg-emoji>\n\n'
        f'— <tg-emoji emoji-id="{E_STORE}">🏪</tg-emoji> {t(lang, "direct_deals")}\n'
        f'— <tg-emoji emoji-id="{E_DROP}">💧</tg-emoji> {t(lang, "instant_delivery")}\n'
        f'— <tg-emoji emoji-id="{E_SEND}">📤</tg-emoji> {t(lang, "discounted")}\n'
        f'— <tg-emoji emoji-id="{E_STORE}">🏪</tg-emoji> {t(lang, "support_247")}\n\n'
        f'<b>{t(lang, "tap_button")}</b>\n\n'
        f'<tg-emoji emoji-id="{E_MONEY}">💰</tg-emoji> {t(lang, "your_balance")}: '
        f'<b>{format_price(user_balance, lang)}</b>'
    )
    await message.answer(text, reply_markup=main_menu(lang, user_id))

@dp.callback_query(F.data == "choose_lang")
async def choose_lang_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🌐 <b>Тілді таңдаңыз / Выберите язык / Choose language:</b>",
        reply_markup=language_menu()
    )
    await callback.answer()


# =========================================================
# 🛒 SHOP
# =========================================================
@dp.callback_query(F.data == "shop")
async def shop_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    if not GROUPS:
        await load_catalog()
    text = (
        f'<blockquote><tg-emoji emoji-id="{E_SHOP_CART}">🛒</tg-emoji> '
        f'<b>PRODUCT STORE — SHOP</b> '
        f'<tg-emoji emoji-id="{E_SHOP_CART}">🛒</tg-emoji></blockquote>\n\n'
        f'<tg-emoji emoji-id="{E_DEVICE}">📱</tg-emoji> '
        f'<b>{t(lang, "select_device")}:</b>'
    )
    await callback.message.edit_text(text, reply_markup=shop_menu(lang))
    await callback.answer()


@dp.callback_query(F.data.startswith("cat_"))
async def category_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    cat_name = callback.data[4:]
    groups = GROUPS.get(cat_name, {})
    if not groups:
        await callback.answer("❌", show_alert=True)
        return
    text = (
        f'<blockquote><tg-emoji emoji-id="{E_SHOP_CART}">🛒</tg-emoji> '
        f'<b>{cat_name}</b> '
        f'<tg-emoji emoji-id="{E_SHOP_CART}">🛒</tg-emoji></blockquote>\n\n'
        f'<tg-emoji emoji-id="{E_FIRE}">🔥</tg-emoji> <b>{t(lang, "choose_product")}:</b>'
    )
    buttons = []
    for group_name in groups.keys():
        emoji_id = get_product_emoji_id(group_name)
        button_text = group_name[:55] + "..." if len(group_name) > 55 else group_name
        buttons.append([InlineKeyboardButton(
            text=button_text, callback_data=f"grp_{cat_name}|{group_name}",
            icon_custom_emoji_id=emoji_id, style="primary"
        )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "back"), callback_data="shop",
        icon_custom_emoji_id=E_BACK, style="danger"
    )])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@dp.callback_query(F.data.startswith("grp_"))
async def group_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    data = callback.data[4:]
    if "|" not in data:
        await callback.answer("❌", show_alert=True)
        return
    cat_name, group_name = data.split("|", 1)
    items = GROUPS.get(cat_name, {}).get(group_name, [])
    if not items:
        await callback.answer("❌", show_alert=True)
        return
    emoji_id = get_product_emoji_id(group_name)
    emoji_tag = f'<tg-emoji emoji-id="{emoji_id}">🔹</tg-emoji> ' if emoji_id else ""
    plan_lines = []
    for p in items:
        pid = get_product_id(p)
        real_name = p.get("_real_name") or p.get("name") or "?"
        label = get_duration_label(real_name)
        tg_price = ID_TO_PRICE.get(pid, 0)
        if tg_price == 0:
            tg_price = get_price(p)
        price_str = format_price(tg_price, lang)
        plan_lines.append(f"├─ 💵 {price_str} — 🎁 {label}")
    if plan_lines:
        plan_lines[-1] = plan_lines[-1].replace("├─", "└─", 1)
    plans_text = "\n".join(plan_lines)
    text = (
        f'<blockquote><tg-emoji emoji-id="{E_SHOP_CART}">🛒</tg-emoji> '
        f'<b>{emoji_tag}{group_name}</b> '
        f'<tg-emoji emoji-id="{E_SHOP_CART}">🛒</tg-emoji></blockquote>\n\n'
        f'👤 <b>{t(lang, "your_tier")}:</b> USER\n\n'
        f'<tg-emoji emoji-id="{E_SHOP_CART}">🛒</tg-emoji> <b>{t(lang, "choose_plan")}:</b>\n\n'
        f'{plans_text}'
    )
    buttons = []
    for p in items:
        pid = get_product_id(p)
        real_name = p.get("_real_name") or p.get("name") or "?"
        label = get_duration_label(real_name)
        tg_price = ID_TO_PRICE.get(pid, 0)
        if tg_price == 0:
            tg_price = get_price(p)
        price_str = format_price(tg_price, lang)
        buttons.append([InlineKeyboardButton(
            text=f"{label} — {price_str}",
            callback_data=f"buy_{pid}_{tg_price}", style="success"
        )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "back"), callback_data=f"cat_{cat_name}",
        icon_custom_emoji_id=E_BACK, style="danger"
    )])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@dp.callback_query(F.data.startswith("buy_"))
async def buy_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    parts = callback.data.split("_")
    product_id = int(parts[1])
    tg_price = int(parts[2])
    customer_ref = f"telegram_{callback.from_user.id}"
    user_id = callback.from_user.id
    
    # ПАЙДАЛАНУШЫНЫҢ БАЛАНСЫН ТЕКСЕРУ
    user_balance = get_user_balance(user_id)
    
    if user_balance < tg_price:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Баланс толтыру", callback_data="add_balance", style="success")],
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_menu",
                                  icon_custom_emoji_id=E_BACK, style="danger")],
        ])
        await callback.message.edit_text(
            f"❌ <b>Баланс жеткіліксіз!</b>\n\n"
            f"💰 Сіздің балансыңыз: <b>{user_balance}₸</b>\n"
            f"💵 Керек: <b>{tg_price}₸</b>\n"
            f"⚠️ Жетпейді: <b>{tg_price - user_balance}₸</b>",
            reply_markup=kb
        )
        await callback.answer()
        return
    
    await callback.message.edit_text("⏳")
    result, order_id = await bala_create_order(customer_ref, product_id, tg_price)
    
    if not result.get("ok"):
        error = result.get("error") or "?"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_menu",
                                  icon_custom_emoji_id=E_BACK, style="danger")]
        ])
        await callback.message.edit_text(f"❌ <b>{t(lang, 'error')}:</b>\n<code>{error}</code>", reply_markup=kb)
        return
    
    order = result.get("order") or {}
    status = order.get("status", "unknown")
    key_value = order.get("key")
    
    if status in ["completed", "success"] and key_value:
        # БАЛАНСТАН АЛУ
        add_user_balance(user_id, -tg_price)
        new_balance = get_user_balance(user_id)
        
        text = (
            f'✅ <b>{t(lang, "purchased")}!</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n'
            f'🔑 <b>{t(lang, "your_key")}:</b>\n'
            f'<code>{key_value}</code>\n\n'
            f'💰 Қалған баланс: <b>{new_balance}₸</b>\n\n'
            f'📋 <i>{t(lang, "copy_key")}</i>'
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "copy_key"),
                                  copy_text={"text": str(key_value)}, style="primary")],
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_menu",
                                  icon_custom_emoji_id=E_BACK, style="danger")],
        ])
        await callback.message.edit_text(text, reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_menu",
                                  icon_custom_emoji_id=E_BACK, style="danger")]
        ])
        await callback.message.edit_text(
            f"⚠️ <b>Status:</b> {status}\n\nID: <code>{order_id}</code>", reply_markup=kb
        )
    await callback.answer()


# =========================================================
# 💰 ADD BALANCE
# =========================================================
@dp.callback_query(F.data == "add_balance")
async def add_balance_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    user_balance = get_user_balance(callback.from_user.id)
    
    text = (
        f'💰 <b>{t(lang, "add_balance")}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'💵 {t(lang, "your_balance")}: <b>{format_price(user_balance, lang)}</b>\n\n'
        f'📊 {t(lang, "balance_min")}: <b>{MIN_BALANCE}₸</b>\n'
        f'📊 {t(lang, "balance_max")}: <b>{MAX_BALANCE}₸</b>\n\n'
        f'{t(lang, "balance_select")}'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100₸", callback_data="dep_100", style="success"),
         InlineKeyboardButton(text="200₸", callback_data="dep_200", style="success")],
        [InlineKeyboardButton(text="500₸", callback_data="dep_500", style="success"),
         InlineKeyboardButton(text="1000₸", callback_data="dep_1000", style="success")],
        [InlineKeyboardButton(text="2000₸", callback_data="dep_2000", style="success"),
         InlineKeyboardButton(text="5000₸", callback_data="dep_5000", style="success")],
        [InlineKeyboardButton(text="10000₸", callback_data="dep_10000", style="success")],
        [InlineKeyboardButton(text=f"✍️ {t(lang, 'balance_custom')}", callback_data="dep_custom", style="primary")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_menu",
                              icon_custom_emoji_id=E_BACK, style="danger")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("dep_"))
async def deposit_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    action = callback.data[4:]
    
    if action == "custom":
        text = (
            f'✍️ <b>{t(lang, "balance_custom")}</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'📊 {t(lang, "balance_min")}: <b>{MIN_BALANCE}₸</b>\n'
            f'📊 {t(lang, "balance_max")}: <b>{MAX_BALANCE}₸</b>\n\n'
            f'{t(lang, "send_custom_amount")}'
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="add_balance",
                                  icon_custom_emoji_id=E_BACK, style="danger")]
        ])
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()
        # Күту режимі
        WAITING[callback.from_user.id] = "custom_amount"
        return
    
    try:
        amount = int(action)
    except ValueError:
        await callback.answer("❌", show_alert=True)
        return
    
    if amount < MIN_BALANCE or amount > MAX_BALANCE:
        await callback.answer(f"❌ {MIN_BALANCE}₸ - {MAX_BALANCE}₸", show_alert=True)
        return
    
    # Төлем әдісін таңдау
    text = (
        f'💳 <b>{t(lang, "choose_payment")}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'💰 Сома: <b>{amount}₸</b>\n\n'
        f'👇 Таңдаңыз:'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🏦 {t(lang, 'kaspi')}", callback_data=f"pay_kaspi_{amount}", style="success")],
        [InlineKeyboardButton(text=f"🏦 {t(lang, 'halyk')}", callback_data=f"pay_halyk_{amount}", style="success")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="add_balance",
                              icon_custom_emoji_id=E_BACK, style="danger")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# Күту режимі
WAITING = {}


@dp.message(F.text.regexp(r"^\d+$"))
async def custom_amount_handler(message: types.Message):
    user_id = message.from_user.id
    if WAITING.get(user_id) != "custom_amount":
        return
    try:
        amount = int(message.text)
    except ValueError:
        return
    if amount < MIN_BALANCE or amount > MAX_BALANCE:
        await message.answer(f"❌ {MIN_BALANCE}₸ - {MAX_BALANCE}₸ арасында болуы керек")
        return
    WAITING[user_id] = None
    lang = get_user_lang(user_id)
    text = (
        f'💳 <b>{t(lang, "choose_payment")}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'💰 Сома: <b>{amount}₸</b>\n\n'
        f'👇 Таңдаңыз:'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🏦 {t(lang, 'kaspi')}", callback_data=f"pay_kaspi_{amount}", style="success")],
        [InlineKeyboardButton(text=f"🏦 {t(lang, 'halyk')}", callback_data=f"pay_halyk_{amount}", style="success")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_menu",
                              icon_custom_emoji_id=E_BACK, style="danger")],
    ])
    await message.answer(text, reply_markup=kb)


@dp.callback_query(F.data.startswith("pay_"))
async def payment_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    parts = callback.data.split("_")
    method = parts[1]
    amount = int(parts[2])
    
    bank_name = "Kaspi Bank" if method == "kaspi" else "Halyk Bank"
    
    text = (
        f'🏦 <b>{bank_name}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'💰 Сома: <b>{amount}₸</b>\n\n'
        f'📱 <b>Нөмір:</b>\n'
        f'<code>{PAYMENT_NUMBER}</code>\n\n'
        f'👤 <b>Алушы:</b> {PAYMENT_HOLDER}\n\n'
        f'📸 <b>Төлем жасаған соң:</b>\n'
        f'1️⃣ Жоғарыдағы нөмірге {amount}₸ аударыңыз\n'
        f'2️⃣ Чекті (скриншот) осы чатқа жіберіңіз\n'
        f'3️⃣ Админ тексереді ✅'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "copy_number"),
                              copy_text={"text": PAYMENT_NUMBER}, style="primary")],
        [InlineKeyboardButton(text=t(lang, "i_paid"), callback_data=f"paid_{amount}", style="success")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="add_balance",
                              icon_custom_emoji_id=E_BACK, style="danger")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("paid_"))
async def paid_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    amount = int(callback.data.split("_")[1])
    
    text = (
        f'📸 <b>{t(lang, "send_receipt")}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'💰 Сома: <b>{amount}₸</b>\n\n'
        f'📎 Чекті (скриншот немесе фото) осы чатқа жіберіңіз.\n\n'
        f'⚠️ <i>Чексіз өтінім қабылданбайды</i>'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="add_balance",
                              icon_custom_emoji_id=E_BACK, style="danger")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
    
    WAITING[callback.from_user.id] = {"action": "receipt", "amount": amount}

@dp.callback_query(F.data == "profile")
async def profile_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    user_id = callback.from_user.id
    customer_ref = f"telegram_{user_id}"
    
    # Жеке баланс (жергілікті)
    user_balance = get_user_balance(user_id)
    
    # Кілттер (кэштен)
    keys = []
    try:
        keys_data = await bala_customer_keys(customer_ref)
        keys = keys_data.get("keys") or []
    except Exception:
        keys = []
    
    # Рефералдар
    ref_count = 0
    for uid, ref_data in REFERRAL_DB.items():
        if str(ref_data.get("referrer_id")) == str(user_id):
            ref_count += 1
    
    first_name = callback.from_user.first_name or "—"
    last_name = callback.from_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    
    text = (
        f'👑 <b>Your Profile</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
        f'🆔 ID: <code>{user_id}</code>\n'
        f'👤 Name: <b>{full_name}</b>\n'
        f'📛 Username: @{callback.from_user.username or "—"}\n\n'
        f'💰 Balance: <b>{format_price(user_balance, lang)}</b>\n'
        f'🔑 Total Keys: <b>{len(keys)}</b>\n'
        f'👥 Referrals: <b>{ref_count}</b>\n\n'
        f'🔑 <i>Tap "My Key" to see your purchased keys</i>'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 My Key", callback_data="my_keys", style="success")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back_menu", style="danger")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "my_keys")
async def my_keys_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    customer_ref = f"telegram_{callback.from_user.id}"
    
    try:
        keys_data = await bala_customer_keys(customer_ref)
        keys = keys_data.get("keys") or []
    except Exception:
        keys = []
    
    if not keys:
        text = (
            f'🔑 <b>My Keys</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
            f'❌ <i>Сізде әзірге кілттер жоқ</i>'
        )
    else:
        lines = [f'🔑 <b>My Keys ({len(keys)}):</b>\n']
        for i, k in enumerate(keys[:10], 1):
            key_val = k.get("key", "—")
            pid = k.get("product_id", "?")
            pname = "?"
            for p in CATALOG:
                if str(p.get("id")) == str(pid):
                    pname = p.get("name", "?")
                    break
            lines.append(f'<b>{i}.</b> <code>{key_val}</code>\n    🛒 {pname}\n')
        text = "\n".join(lines)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data="profile", style="danger")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
# =========================================================
# 📸 ЧЕК ҚАБЫЛДАУ
# =========================================================
@dp.message(F.photo | F.document)
async def get_receipt(message: types.Message):
    user_id = message.from_user.id
    wait = WAITING.get(user_id)
    
    if not wait or not isinstance(wait, dict) or wait.get("action") != "receipt":
        return
    
    amount = wait["amount"]
    lang = get_user_lang(user_id)
    
    # Чекті сақтау
    deposit_id = f"dep_{uuid.uuid4().hex[:8]}"
    deposit_data = {
        "id": deposit_id,
        "user_id": user_id,
        "first_name": message.from_user.first_name,
        "username": message.from_user.username,
        "amount": amount,
        "time": datetime.now().isoformat(),
        "status": "pending",
    }
    DEPOSITS_DB.append(deposit_data)
    save_all()
    
    # Админге жіберу
    admin_text = (
        f'🔔 <b>ЖАҢА ТОЛТЫРУ</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'👤 {message.from_user.first_name}\n'
        f'🆔 <code>{user_id}</code>\n'
        f'📛 @{message.from_user.username or "—"}\n'
        f'💰 Сома: <b>{amount}₸</b>\n'
        f'🆔 ID: <code>{deposit_id}</code>\n\n'
        f'👇 Растау / Қабылдамау:'
    )
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Растау", callback_data=f"adm_ok_{deposit_id}", style="success")],
        [InlineKeyboardButton(text="❌ Қабылдамау", callback_data=f"adm_no_{deposit_id}", style="danger")],
    ])
    
    try:
        if message.photo:
            await bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id,
                                 caption=admin_text, reply_markup=admin_kb)
        elif message.document:
            await bot.send_document(ADMIN_ID, document=message.document.file_id,
                                    caption=admin_text, reply_markup=admin_kb)
    except Exception as e:
        print(f"❌ Admin send error: {e}")
    
    await message.answer(
        f'✅ <b>{t(lang, "receipt_sent")}</b>\n\n'
        f'⏳ {t(lang, "receipt_thanks")}'
    )
    WAITING[user_id] = None


# =========================================================
# 🎯 PROFILE
# =========================================================
@dp.callback_query(F.data.startswith("adm_ok_"))
async def adm_approve(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    dep_id = callback.data[7:]
    for d in DEPOSITS_DB:
        if d["id"] == dep_id:
            d["status"] = "approved"
            user_id = d["user_id"]
            amount = d["amount"]
            
            # ПАЙДАЛАНУШЫНЫҢ БАЛАНСЫНА ҚОСУ
            add_user_balance(user_id, amount)
            
            # BALA балансына да қосамыз (сіздің кабинет)
            # Бұл — опциональды, себебі BALA API-де пополнение жоқ
            
            save_all()
            
            try:
                new_balance = get_user_balance(user_id)
                await bot.send_message(
                    user_id,
                    f"✅ <b>Баланс толтырылды!</b>\n\n"
                    f"💰 +{amount}₸\n"
                    f"💵 Жаңа баланс: <b>{new_balance}₸</b>"
                )
            except Exception:
                pass
            
            await callback.message.edit_caption(
                caption=(callback.message.caption or "") + "\n\n✅ <b>РАСТАЛДЫ</b>"
            )
            break
    await callback.answer("✅")


# =========================================================
# 📖 HOW TO USE
# =========================================================
@dp.callback_query(F.data == "how_to")
async def how_to_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    text = t(lang, "how_to_use_text")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_menu",
                              icon_custom_emoji_id=E_BACK, style="danger")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# =========================================================
# 🎁 LUCKY
# =========================================================
@dp.callback_query(F.data == "lucky")
async def lucky_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    user_id = str(callback.from_user.id)
    now = datetime.now()
    
    # Апта тексеру
    if user_id in LUCKY_DB:
        last_time = datetime.fromisoformat(LUCKY_DB[user_id])
        week_ago = now - timedelta(days=7)
        if last_time > week_ago:
            days_left = 7 - (now - last_time).days
            text = (
                f'❌ <b>{t(lang, "lucky_already")}</b>\n\n'
                f'⏳ Қалды: <b>{days_left}</b> күн'
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_menu",
                                      icon_custom_emoji_id=E_BACK, style="danger")]
            ])
            await callback.message.edit_text(text, reply_markup=kb)
            await callback.answer()
            return
    
    # Ойнау
    reward = round(random.uniform(0.1, 10.0), 2)
    LUCKY_DB[user_id] = now.isoformat()
    save_all()
    
    # Балансқа қосу (BALA арқылы емес, жергілікті)
    if "lucky_balance" not in USERS_DB.get(user_id, {}):
        USERS_DB.setdefault(user_id, {})["lucky_balance"] = 0
    USERS_DB[user_id]["lucky_balance"] = USERS_DB[user_id].get("lucky_balance", 0) + reward
    save_all()
    
    text = (
        f'{t(lang, "lucky_win")}<b>{reward}₸</b>\n\n'
        f'📅 Келесі ойын: 7 күннен кейін'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_menu",
                              icon_custom_emoji_id=E_BACK, style="danger")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer("🎉", show_alert=True)


# =========================================================
# 🔗 SHARE (REFERRAL)
# =========================================================
@dp.callback_query(F.data == "share")
async def share_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    user_id = callback.from_user.id
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    
    ref_count = 0
    for uid, ref_data in REFERRAL_DB.items():
        if str(ref_data.get("referrer_id")) == str(user_id):
            ref_count += 1
    
    text = (
        f'{t(lang, "share_text")}\n'
        f'<code>{ref_link}</code>\n\n'
        f'👥 Шақырғандар: <b>{ref_count}</b>'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Бөлісу", url=f"https://t.me/share/url?url={ref_link}&text=🎁 XERZZ KEYSHOP - премиум кілттер!", style="success")],
        [InlineKeyboardButton(text="📋 Көшіру", copy_text={"text": ref_link}, style="primary")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_menu",
                              icon_custom_emoji_id=E_BACK, style="danger")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# =========================================================
# 🆘 SUPPORT
# =========================================================
@dp.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    text = t(lang, "support_text")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ " + t(lang, "back"), callback_data="back_menu",
                              icon_custom_emoji_id=E_BACK, style="danger")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
    WAITING[callback.from_user.id] = "support_message"


@dp.message(F.text)
async def support_message_handler(message: types.Message):
    user_id = message.from_user.id
    if WAITING.get(user_id) != "support_message":
        return
    WAITING[user_id] = None
    lang = get_user_lang(user_id)
    
    # Админге жіберу
    admin_text = (
        f'🆘 <b>ҚОЛДАУ ХАБАРЛАМАСЫ</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'👤 {message.from_user.first_name}\n'
        f'🆔 <code>{user_id}</code>\n'
        f'📛 @{message.from_user.username or "—"}\n\n'
        f'💬 <b>Хабарлама:</b>\n{message.text}'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Жауап беру", callback_data=f"adm_reply_{user_id}", style="primary")]
    ])
    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb)
    except Exception:
        pass
    
    await message.answer(f'✅ {t(lang, "support_sent")}')


# =========================================================
# ⬅️ BACK
# =========================================================
@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name or "User"
    
    print(f"🔍 BACK: user_id={user_id}, name={user_name}")
    
    await callback.message.delete()
    await show_main_menu(
        callback.message,
        lang=lang,
        user_id=user_id,
        user_name=user_name
    )
    await callback.answer()


# =========================================================
# 🛡️ ADMIN PANEL
# =========================================================
@dp.callback_query(F.data == "admin_panel")
async def admin_panel_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True)
        return
    lang = "kz"
    
    pending = sum(1 for d in DEPOSITS_DB if d.get("status") == "pending")
    
    text = (
        f'🛡️ <b>ADMIN PANEL</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'📊 Catalog: <b>{len(CATALOG)}</b> тауар\n'
        f'📂 Санаттар: <b>{len(GROUPS)}</b>\n'
        f'👥 Пайдаланушылар: <b>{len(USERS_DB)}</b>\n'
        f'💰 Күтіп тұрған чектер: <b>{pending}</b>\n\n'
        f'👇 Таңдаңыз:'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data="adm_stats", style="primary")],
        [InlineKeyboardButton(text="👥 Users", callback_data="adm_users", style="primary")],
        [InlineKeyboardButton(text="💰 Deposits", callback_data="adm_deposits", style="success")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast", style="danger")],
        [InlineKeyboardButton(text="🔄 Reload", callback_data="adm_reload", style="success")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back_menu", style="danger")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "adm_stats")
async def adm_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    total_deposits = sum(d.get("amount", 0) for d in DEPOSITS_DB if d.get("status") == "approved")
    pending = sum(1 for d in DEPOSITS_DB if d.get("status") == "pending")
    
    text = (
        f'📊 <b>STATISTICS</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'📦 Catalog: <b>{len(CATALOG)}</b>\n'
        f'📂 Groups: <b>{len(GROUPS)}</b>\n'
        f'👥 Users: <b>{len(USERS_DB)}</b>\n'
        f'💰 Approved: <b>{total_deposits}₸</b>\n'
        f'⏳ Pending: <b>{pending}</b>'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_panel", style="danger")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "adm_users")
async def adm_users(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    users_list = ""
    for uid, data in list(USERS_DB.items())[:20]:
        name = data.get("first_name", "—")
        users_list += f"• <code>{uid}</code> — {name}\n"
    if not users_list:
        users_list = "—"
    text = f'👥 <b>USERS ({len(USERS_DB)})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n{users_list}'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_panel", style="danger")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "adm_deposits")
async def adm_deposits(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    pending = [d for d in DEPOSITS_DB if d.get("status") == "pending"]
    if not pending:
        text = "💰 <b>DEPOSITS</b>\n\n❌ Күтіп тұрған чектер жоқ"
    else:
        lines = ["💰 <b>Күтіп тұрған чектер:</b>\n"]
        for d in pending[:10]:
            lines.append(
                f"• <code>{d['id']}</code>\n"
                f"  👤 {d.get('first_name', '—')}\n"
                f"  💵 {d.get('amount', 0)}₸\n"
            )
        text = "\n".join(lines)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_panel", style="danger")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("adm_ok_"))
async def adm_approve(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    dep_id = callback.data[7:]
    for d in DEPOSITS_DB:
        if d["id"] == dep_id:
            d["status"] = "approved"
            user_id = d["user_id"]
            amount = d["amount"]
            save_all()
            
            # Хабарлау
            try:
                await bot.send_message(
                    user_id,
                    f"✅ <b>Баланс толтырылды!</b>\n\n💰 +{amount}₸"
                )
            except Exception:
                pass
            
            await callback.message.edit_caption(
                caption=(callback.message.caption or "") + "\n\n✅ <b>РАСТАЛДЫ</b>"
            )
            break
    await callback.answer("✅")


@dp.callback_query(F.data.startswith("adm_no_"))
async def adm_reject(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    dep_id = callback.data[7:]
    for d in DEPOSITS_DB:
        if d["id"] == dep_id:
            d["status"] = "rejected"
            user_id = d["user_id"]
            save_all()
            try:
                await bot.send_message(user_id, "❌ <b>Чек қабылданбады</b>")
            except Exception:
                pass
            await callback.message.edit_caption(
                caption=(callback.message.caption or "") + "\n\n❌ <b>ҚАБЫЛДАНБАДЫ</b>"
            )
            break
    await callback.answer("❌")


@dp.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_ask(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    text = "📢 <b>BROADCAST</b>\n\nХабарлама мәтінін жазыңыз:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_panel", style="danger")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
    WAITING[ADMIN_ID] = "broadcast"


@dp.message(F.text)
async def broadcast_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if WAITING.get(ADMIN_ID) != "broadcast":
        return
    WAITING[ADMIN_ID] = None
    text = message.text
    
    status = await message.answer("⏳ Жіберілуде...")
    success = 0
    failed = 0
    for uid in USERS_DB.keys():
        try:
            await bot.send_message(int(uid), text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    
    await status.edit_text(
        f"✅ <b>Жіберілді!</b>\n\n✅ Сәтті: {success}\n❌ Қате: {failed}"
    )


@dp.callback_query(F.data == "adm_reload")
async def adm_reload(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    await load_catalog()
    await callback.answer("✅ Reloaded", show_alert=True)


# =========================================================
# 🚀 ІСКЕ ҚОСУ
# =========================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    await load_catalog()
    me = await bala_me()
    print(f"✅ BALA: {me.get('balance_pcoins')} Pcoin")
    print(f"✅ ADMIN_ID: {ADMIN_ID}")
    print(f"✅ Users: {len(USERS_DB)}")
    print("Бот іске қосылды ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())