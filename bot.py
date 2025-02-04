import asyncio
import aiohttp
import nest_asyncio
nest_asyncio.apply()

from telegram import BotCommand, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler,
    ConversationHandler, ContextTypes
)

TOKEN = "7638590946:AAEBmjySQmkYKYPQwfr0mn0EQFdr1GhuaQM"

running_tasks = {}
user_settings = {}

DEFAULT_SETTINGS = {
    "update_interval": 10,
    "price_alerts": [],
    "percent_change_alert": 1.0,
    "volume_alert": 1000000
}

(SET_UPDATE_INTERVAL, SET_PRICE_ALERTS, SET_PERCENT_ALERT, SET_VOLUME_ALERT) = range(4)

async def get_kaspa_price():
    async with aiohttp.ClientSession() as session:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=kaspa&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true"
        async with session.get(url) as response:
            data = await response.json()
            return {
                "price": round(data["kaspa"]["usd"], 4),
                "change_24h": round(data["kaspa"]["usd_24h_change"], 2),
                "volume": data["kaspa"]["usd_24h_vol"]
            }

async def send_crypto_updates(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    while running_tasks.get(user_id, False):
        try:
            price_data = await get_kaspa_price()
            settings = user_settings[user_id]
            message = f"💰 Kaspa: ${price_data['price']}\n24h Change: {price_data['change_24h']}%"
            await context.bot.send_message(chat_id=user_id, text=message)
            await asyncio.sleep(settings["update_interval"])
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id not in user_settings:
        user_settings[user_id] = DEFAULT_SETTINGS.copy()
    
    await update.message.reply_text(
        "🤖 **ברוכים הבאים לבוט Kaspa!**\n\n"
        "/start - התחל מעקב\n"
        "/stop - עצור מעקב\n"
        "/settings - הגדרות\n"
        "/status - מצב נוכחי",
        parse_mode="Markdown"
    )
    
    if not running_tasks.get(user_id, False):
        running_tasks[user_id] = True
        asyncio.create_task(send_crypto_updates(context, user_id))

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if running_tasks.get(user_id, False):
        running_tasks[user_id] = False
        await update.message.reply_text("🛑 העדכונים הופסקו!")
    else:
        await update.message.reply_text("❌ אין עדכונים פעילים כרגע.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    settings = user_settings.get(user_id, DEFAULT_SETTINGS)
    
    status_message = (
        f"⚙️ **הגדרות נוכחיות:**\n"
        f"⏱️ זמן בין התראות: {settings['update_interval']} שניות\n"
        f"💵 התראות מחיר: {', '.join(map(str, settings['price_alerts']))}$\n"
        f"📊 התראת שינוי: {settings['percent_change_alert']}%\n"
        f"📈 התראת נפח: ${settings['volume_alert']:,}"
    )
    
    await update.message.reply_text(status_message)

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⏱️ שינוי זמן התראה", callback_data="change_update_interval")],
        [InlineKeyboardButton("💵 עריכת התראות מחיר", callback_data="change_price_alerts")],
        [InlineKeyboardButton("📊 שינוי אחוזי שינוי", callback_data="change_percent_alert")],
        [InlineKeyboardButton("📈 שינוי התראת נפח", callback_data="change_volume_alert")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚙️ **בחר אפשרות לשינוי ההגדרות:**", reply_markup=reply_markup, parse_mode="Markdown")

async def setting_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.message.chat_id
    await query.answer()


    # שמירת ההגדרה שבחר המשתמש
    if query.data == "change_update_interval":
        context.user_data["setting_state"] = SET_UPDATE_INTERVAL
        await query.message.reply_text("⏱️ שלח את הזמן בין התראות בשניות:")
    
    elif query.data == "change_price_alerts":
        context.user_data["setting_state"] = SET_PRICE_ALERTS
        await query.message.reply_text("💵 שלח רשימה של מחירים להתראה (מופרדים בפסיק, למשל: 0.02, 0.05):")
    
    elif query.data == "change_percent_alert":
        context.user_data["setting_state"] = SET_PERCENT_ALERT
        await query.message.reply_text("📊 שלח את אחוז השינוי להתראה (למשל: 2.5):")
    
    elif query.data == "change_volume_alert":
        context.user_data["setting_state"] = SET_VOLUME_ALERT
        await query.message.reply_text("📈 שלח את נפח המסחר המינימלי להתראה (למשל: 5000000):")

    return context.user_data["setting_state"]


async def set_bot_commands(application: Application):
    commands = [
        BotCommand("start", "התחל מעקב"),
        BotCommand("stop", "עצור מעקב"),
    ]
    await application.bot.set_my_commands(commands)
    

async def set_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    text = update.message.text
    state = context.user_data.get("setting_state")  # בטוח יותר נגד שגיאות

    if state == SET_UPDATE_INTERVAL:
        user_settings[user_id]["update_interval"] = int(text)
        await update.message.reply_text(f"⏱️ זמן ההתראה שונה ל-{text} שניות!")

    elif state == SET_PRICE_ALERTS:
        user_settings[user_id]["price_alerts"] = [float(x.strip()) for x in text.split(",")]
        await update.message.reply_text("💵 התראות המחיר עודכנו!")

    elif state == SET_PERCENT_ALERT:
        user_settings[user_id]["percent_change_alert"] = float(text)
        await update.message.reply_text(f"📊 התראת שינוי עודכנה ל-{text}%!")

    elif state == SET_VOLUME_ALERT:
        user_settings[user_id]["volume_alert"] = int(text)
        await update.message.reply_text(f"📈 התראת נפח עודכנה ל-{text}!")

    return ConversationHandler.END

async def main():
    print("🚀 הבוט התחיל לפעול!")
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(setting_selected)],
        states={
            SET_UPDATE_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_value)],
            SET_PRICE_ALERTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_value)],
            SET_PERCENT_ALERT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_value)],
            SET_VOLUME_ALERT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_value)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("settings", settings_menu))
    app.add_handler(conv_handler)
    await set_bot_commands(app)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
