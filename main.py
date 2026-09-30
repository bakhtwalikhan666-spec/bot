import os
import re
import logging
import random
import string
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ==================== ۱. بنسټیز تنظیمات او لاګونه ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دلته ستاسو نوی ټوکن ځای پر ځای شو
BOT_TOKEN = "8515700089:AAGPdkr81tOhs5peygQquwlo_isL206Gvjg"
OFFICIAL_CHANNEL = "@AfghanSparkOfficial"
PAYOUT_CHANNEL = "@AfghanSparkPay"

# دلته ستاسو اډمین آیډي تنظیم شوه
ADMIN_IDS = [6956795081]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ==================== ۲. د ډیټابیس او جدولونو جوړښت ====================
def init_db():
    conn = sqlite3.connect('afghan_spark.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            referrer_id INTEGER,
            penalty_status INTEGER DEFAULT 0,
            wallet_account TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            account TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gift_codes (
            code TEXT PRIMARY KEY,
            reward_amount REAL,
            is_used INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== ۳. د محرمیت او نمبرونو د پټولو فنکشن ====================
def mask_wallet(account: str) -> str:
    if len(account) >= 7:
        return account[:3] + "****" + account[-2:]
    return "account****XX"

# ==================== ۴. د /start او د ریفرل سیسټم او خبرتیاوو برخه ====================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "کاروونکی"
    args = message.get_args()
    
    conn = sqlite3.connect('afghan_spark.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    is_new_user = False
    inviter_id = None
    
    if not user:
        is_new_user = True
        if args and args.startswith("ref_"):
            try:
                inviter_id = int(args.split("_")[1])
                if inviter_id != user_id:
                    cursor.execute("UPDATE users SET balance = balance + 1.5 WHERE user_id = ?", (inviter_id,))
            except ValueError:
                pass
        
        cursor.execute("INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", (user_id, username, inviter_id))
        conn.commit()
    conn.close()

    if is_new_user and inviter_id:
        try:
            conn = sqlite3.connect('afghan_spark.db')
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE user_id = ?", (inviter_id,))
            inviter_data = cursor.fetchone()
            conn.close()
            
            inviter_name = inviter_data[0] if inviter_data and inviter_data[0] else "کاروونکی"
            
            try:
                await bot.send_message(
                    inviter_id,
                    f"🎉 **مبارک وي!**\n\n"
                    f"يو نوي غړي ستاسو د اختصاصي لینک له لارې رب ته لاسرسی وموند!\n"
                    f"💰 ستاسو په بیلانس کې `1.5 $` امتیاز اضافه شو. 🚀",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            referral_broadcast_text = (
                f"👥 **د راجع کولو (Referral) نوی راپور** ⚡\n\n"
                f"👤 **بلونکی کاروونکی:** `{inviter_name}***`\n"
                f"👤 **نوی راغلی غړی:** `{username}***`\n"
                f"🎁 **وضعیت:** امتیاز په بریالیتوب سره ثبت شو! 🟢\n\n"
                f"🚀 خلک په چټکۍ سره د لینکونو له لارې رب ته را روان دي. تاسو هم خپل لینک شریک کړئ!"
            )
            await bot.send_message(PAYOUT_CHANNEL, referral_broadcast_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error sending referral broadcast: {e}")

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📌 رسمي چینل جوین کړئ", url=f"https://t.me/AfghanSparkOfficial".replace('@', '')),
        InlineKeyboardButton("💰 د تادیاتو چینل جوین کړئ", url=f"https://t.me/AfghanSparkPay".replace('@', '')),
        InlineKeyboardButton("✅ غړیتوب تصدیق کړئ (Check)", callback_data="verify_membership")
    )
    
    await message.reply(
        f"سلام **{message.from_user.first_name}**! ⚡\n\n"
        "د **Afghan Spark** مسلکي سیسټم ته په خیر راغلئ.\n"
        "د رب د ځانګړتیاو د کارولو لپاره، لومړی لاندې چینلونه جوین کړئ:",
        reply_markup=keyboard, parse_mode="Markdown"
    )

# ==================== ۵. د غړیتوب معاینه ====================
@dp.callback_query_handler(text="verify_membership")
async def verify_membership(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    try:
        member = await bot.get_chat_member(chat_id=OFFICIAL_CHANNEL, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            await bot.answer_callback_query(callback_query.id, "✅ غړیتوب تایید شو!", show_alert=True)
            
            main_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            main_menu.add(
                KeyboardButton("👤 پروفایل او بیلانس"),
                KeyboardButton("👥 د راجع کولو (Ref) لینک"),
                KeyboardButton("💳 د پېوټ/ویډرا حساب ثبتول"),
                KeyboardButton("💸 د پېوټ غوښتنه (Withdraw)"),
                KeyboardButton("🧪 د فیک ویډرا ازموينه (Fake Pay)"),
                KeyboardButton("🛠 د ملاتړ ټکټ")
            )
            await bot.send_message(user_id, "🎉 مینو فعاله شوه. خپله برخه وټاکئ:", reply_markup=main_menu)
        else:
            await bot.answer_callback_query(callback_query.id, "❌ لومړی رسمي چینل جوین کړئ!", show_alert=True)
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        await bot.answer_callback_query(callback_query.id, "⚠ تخنیکي ستونزه رامنځته شوه.", show_alert=True)

# ==================== ۶. پروفایل او بیلانس ====================
@dp.message_handler(text="👤 پروفایل او بیلانس")
async def profile_handler(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('afghan_spark.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, wallet_account FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    
    if data:
        balance, wallet = data
        wallet_text = mask_wallet(wallet) if wallet else "تراوسه نه دی ثبت شوی ❌"
        
        await message.reply(
            f"👤 **ستاسو پروفایل معلومات:**\n\n"
            f"🆔 آیډي: `{user_id}`\n"
            f"💰 شته بیلانس: `{balance} $`\n"
            f"💳 ثبت شوی حساب: `{wallet_text}`",
            parse_mode="Markdown"
        )

# ==================== ۷. د راجع کولو (Ref) لینک برخه ====================
@dp.message_handler(text="👥 د راجع کولو (Ref) لینک")
async def referral_link_handler(message: types.Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    await message.reply(
        f"👥 **ستاسو د بلنې او راجع کولو اختصاصي لینک:**\n\n"
        f"`{ref_link}`\n\n"
        f"📌 دا لینک خپلو ملګرو ته واستوئ. کله چې دوی د دې لینک له لارې رب ته راشي، تاسو ته به جایزه درکړل شي او په پېوټ چینل کې به راپور شي! 🚀",
        parse_mode="Markdown"
    )

# ==================== ۸. د ملاتړ ټکټ برخه ====================
@dp.message_handler(text="🛠 د ملاتړ ټکټ")
async def support_ticket_prompt(message: types.Message):
    await message.reply(
        "🛠 **د ملاتړ او مرستې برخه:**\n\n"
        "که ستونزه لرئ، په لاندې بڼه یې ولیکئ:\n"
        "`/support ستاسو پیغام دلته...`",
        parse_mode="Markdown"
    )

@dp.message_handler(commands=['support'])
async def send_support_ticket(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "نامعلوم"
    args = message.get_args()
    
    if not args:
        await message.reply("❌ مهرباني وکړئ خپل پیغام هم ولیکئ.", parse_mode="Markdown")
        return
        
    ticket_text = f"🛠 **نوی ملاتړی ټکټ** ✉\n\n👤 کاروونکی: `@{username}` (ID: `{user_id}`)\n💬 پیغام:\n{args}"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, ticket_text, parse_mode="Markdown")
        except:
            pass
            
    await message.reply("✅ ستاسو ټکټ اډمینانو ته واستول شو.")

# ==================== ۹. د حساب ثبتول د پالیسۍ سره ====================
@dp.message_handler(text="💳 د پېوټ/ویډرا حساب ثبتول")
async def set_wallet_handler(message: types.Message):
    await message.reply(
        "💳 **د تادیاتو د حساب ثبتولو برخه:**\n\n"
        "🇦🇫 **افغاني نمبر:** باید په `07` پیل او ۱۰ عدده وي (`/setwallet 0781234567`).\n"
        "🌐 **حساب پې (HesabPay):** د خپل حساب نمبر یا ادرس ولیکئ (`/setwallet hesabpay_user`).\n\n"
        "⚠ *یادونه: د غلط ادرس مسؤلیت په خپله ستاسو دی.*",
        parse_mode="Markdown"
    )

@dp.message_handler(commands=['setwallet'])
async def save_wallet(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    
    if not args:
        await message.reply("❌ بېلګه:\n`/setwallet 0781234567`", parse_mode="Markdown")
        return
    
    input_value = args.strip()
    is_valid = False
    
    if re.fullmatch(r'07\d{8}', input_value) or len(input_value) >= 5:
        is_valid = True
        
    if not is_valid:
        await message.reply("❌ ناسم نمبر یا ادرس!", parse_mode="Markdown")
        return
        
    conn = sqlite3.connect('afghan_spark.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET wallet_account = ? WHERE user_id = ?", (input_value, user_id))
    conn.commit()
    conn.close()
    
    await message.reply(f"✅ حساب په بریا سره ثبت شو:\n`{input_value}`", parse_mode="Markdown")

# ==================== ۱۰. فیک او اصلي ویډرا (مستقیم پېوټ چینل ته) ====================
async def send_payout_broadcast(name, amount, account_masked):
    payout_text = (
        f"💰 **د افغان سپارک (Afghan Spark) تادیاتو راپور** ⚡\n\n"
        f"👤 **کاروونکی:** `{name}***`\n"
        f"💵 **مقدار:** `{amount} $`\n"
        f"💳 **حساب / نمبر:** `{account_masked}`\n"
        f"✅ **وضعیت:** بریالی (Paid) 🟢\n\n"
        f"🚀 سیسټم په پوره صداقت سره پېوټونه رسوي!"
    )
    await bot.send_message(PAYOUT_CHANNEL, payout_text, parse_mode="Markdown")

@dp.message_handler(text="🧪 د فیک ویډرا ازموينه (Fake Pay)")
async def manual_fake_withdrawal(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    names = ["احمد", "بلال", "محمد", "فواد", "عمر"]
    raw_accounts = ["0781234534", "0798765412", "hesabpay_99"]
    await send_payout_broadcast(random.choice(names), round(random.uniform(5.0, 25.0), 2), mask_wallet(random.choice(raw_accounts)))
    await message.reply("✅ فیک پېوټ مستقیم پېوټ چینل ته ولېږل شو.")

async def auto_fake_payout_loop():
    while True:
        await asyncio.sleep(random.randint(3600, 10800))
        try:
            names = ["خان", "نور", "رحمان", "همایون", "قاسم"]
            raw_accounts = ["0789988776", "0792233445", "hesabpay_auto"]
            await send_payout_broadcast(random.choice(names), round(random.uniform(5.0, 20.0), 2), mask_wallet(random.choice(raw_accounts)))
        except Exception as e:
            logger.error(f"Auto fake payout error: {e}")

@dp.message_handler(text="💸 د پېوټ غوښتنه (Withdraw)")
async def withdraw_policy_check(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('afghan_spark.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, wallet_account FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    
    if not data or not data[1]:
        await message.reply("⚠ لومړی خپل حساب ثبت کړئ.")
        return
    if data[0] < 5.0:
        await message.reply(f"❌ ستاسو بیلانس ({data[0]}) تر 5 ډالرو کم دی.")
        return
        
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ هو، پېوټ راکړه", callback_data=f"confirm_wd_{user_id}"),
        InlineKeyboardButton("❌ نه", callback_data="cancel_wd")
    )
    await message.reply(f"💸 غوښتل شوې اندازه: `{data[0]} $`\n💳 حساب: `{mask_wallet(data[1])}`\n\n⚠ د غلط ادرس مسؤلیت په خپله ستاسو دی. ایا ډاډه یاست؟", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('confirm_wd_'))
async def final_execute_withdrawal(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    conn = sqlite3.connect('afghan_spark.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, wallet_account FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    
    if not data or data[0] < 5.0:
        await bot.answer_callback_query(callback_query.id, "❌ تېروتنه!", show_alert=True)
        conn.close()
        return
        
    cursor.execute("INSERT INTO withdrawals (user_id, amount, account, status) VALUES (?, ?, ?, 'pending')", (user_id, data[0], data[1]))
    cursor.execute("UPDATE users SET balance = 0.0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    await bot.answer_callback_query(callback_query.id, "✅ غوښتنه ثبت شوه.")
    await bot.edit_message_text("✅ غوښتنه اډمینانو ته واستول شوه.", chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)

# ==================== ۱۱. د اډمین پینل ====================
@dp.message_handler(commands=['admin_withdrawals', 'payouts'])
async def admin_view_withdrawals(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
        
    conn = sqlite3.connect('afghan_spark.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, amount, account FROM withdrawals WHERE status = 'pending'")
    withdrawals = cursor.fetchall()
    conn.close()
    
    if not withdrawals:
        await message.reply("📭 اوس د تادیاتو هېڅ غوښتنه نشته.")
        return
        
    for wd_id, user_id, amount, account in withdrawals:
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("✅ تادیه (Paid)", callback_data=f"pay_yes_{wd_id}_{user_id}"),
            InlineKeyboardButton("❌ رد کول", callback_data=f"pay_no_{wd_id}")
        )
        await message.answer(
            f"🔔 **غوښتنه (#ID: {wd_id})**\n👤 کاروونکی: `{user_id}`\n💵 اندازه: `{amount} $`\n💳 ادرس: `{account}`",
            reply_markup=kb, parse_mode="Markdown"
        )

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('pay_'))
async def process_admin_payout(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        return
        
    parts = callback_query.data.split('_')
    action = parts[1]
    wd_id = parts[2]
    
    conn = sqlite3.connect('afghan_spark.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, amount, account FROM withdrawals WHERE id = ? AND status = 'pending'", (wd_id,))
    data = cursor.fetchone()
    
    if not data:
        await bot.answer_callback_query(callback_query.id, "❌ مخکې پروسس شوی.", show_alert=True)
        conn.close()
        return
        
    user_id, amount, account = data
    
    if action == 'yes':
        cursor.execute("UPDATE withdrawals SET status = 'paid' WHERE id = ?", (wd_id,))
        conn.commit()
        conn.close()
        
        await bot.answer_callback_query(callback_query.id, "✅ تادیه تایید شوه.")
        await bot.edit_message_text(f"✅ غوښتنه (#ID: {wd_id}) تایید شوه.", chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        
        try:
            await bot.send_message(user_id, f"🎉 مبارک وي! ستاسو د `{amount} $` ویډرا تادیه شوه.")
        except:
            pass
            
        await send_payout_broadcast("کاروونکی", amount, mask_wallet(account))
    else:
        cursor.execute("UPDATE withdrawals SET status = 'rejected' WHERE id = ?", (wd_id,))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()
        
        await bot.answer_callback_query(callback_query.id, "❌ غوښتنه رد شوه.")
        await bot.edit_message_text(f"❌ غوښتنه (#ID: {wd_id}) رد شوه.", chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        try:
            await bot.send_message(user_id, f"❌ ستاسو د `{amount} $` ویډرا غوښتنه اډمین رد کړه او پیسې مو بېرته راوګرځېدې.")
        except:
            pass

# ==================== ۱۲. پیلول ====================
async def on_startup(dispatcher):
    asyncio.create_task(auto_fake_payout_loop())
    logger.info("Afghan Spark bot is running with direct channel notifications!")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
