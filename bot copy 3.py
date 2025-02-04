import asyncio
import aiohttp
import nest_asyncio  # ✅ פתרון לשגיאת event loop
nest_asyncio.apply()  # ✅ מונע התנגשות לולאות asyncio ב-VS Code

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
   Application, CommandHandler, ContextTypes, 
   CallbackQueryHandler, MessageHandler, filters
)

TOKEN = "7638590946:AAEBmjySQmkYKYPQwfr0mn0EQFdr1GhuaQM"  # ✅ ודא שהכנסת את הטוקן שלך!
running_tasks = {}
user_settings = {}

DEFAULT_SETTINGS = {
   "update_interval": 10,
   "price_alerts": [],
   "percent_change_alert": 1.0,
   "volume_alert": 1000000,
   "last_price": 0,
   "last_alert_time": 0
}

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

async def check_alerts(price_data, user_id):
   settings = user_settings[user_id]
   alerts = []
   current_price = price_data["price"]
   last_price = settings["last_price"]
   
   for alert_price in settings["price_alerts"]:
       if (last_price < alert_price <= current_price) or (last_price > alert_price >= current_price):
           alerts.append(f"🚨 מחיר חצה {alert_price}$")
   
   if last_price > 0:
       percent_change = ((current_price - last_price) / last_price) * 100
       if abs(percent_change) >= settings["percent_change_alert"]:
           direction = "📈 עלה" if percent_change > 0 else "📉 ירד"
           alerts.append(f"{direction} ב-{abs(percent_change):.2f}%")
   
   if price_data["volume"] > settings["volume_alert"]:
       alerts.append(f"🔄 נפח מסחר גבוה: ${price_data['volume']:,.0f}")
   
   settings["last_price"] = current_price
   return alerts

async def send_crypto_updates(context: ContextTypes.DEFAULT_TYPE, user_id: int):
   while running_tasks.get(user_id, False):
       try:
           price_data = await get_kaspa_price()
           alerts = await check_alerts(price_data, user_id)
           
           message = f"💰 Kaspa: ${price_data['price']}\n"
           message += f"24h Change: {price_data['change_24h']}%"
           
           if alerts:
               message += "\n\n" + "\n".join(alerts)
           
           await context.bot.send_message(chat_id=user_id, text=message)
           await asyncio.sleep(user_settings[user_id]["update_interval"])
       except Exception as e:
           print(f"Error: {e}")
           await asyncio.sleep(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
   user_id = update.message.chat_id
   
   if user_id not in user_settings:
       user_settings[user_id] = DEFAULT_SETTINGS.copy()
   
   welcome_message = (
       "🤖 **ברוכים הבאים לבוט Kaspa!**\n\n"
       "/start - התחל מעקב\n"
       "/stop - עצור מעקב\n"
       "/settings - הגדרות\n"
       "/status - מצב נוכחי"
   )
   
   await update.message.reply_text(welcome_message, parse_mode="Markdown")
   
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
       f"⚙️ הגדרות נוכחיות:\n"
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

async def change_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.message.chat_id

    if query.data == "change_update_interval":
        user_settings[user_id]["update_interval"] = 30  # ניתן להחליף בערך דינמי ממשתמש
        await query.message.reply_text("⏱️ זמן ההתראה שונה ל-30 שניות!")
    
    elif query.data == "change_price_alerts":
        user_settings[user_id]["price_alerts"] = [0.02, 0.05]  # ניתן להחליף בערך דינמי
        await query.message.reply_text("💵 התראות המחיר עודכנו!")
    
    elif query.data == "change_percent_alert":
        user_settings[user_id]["percent_change_alert"] = 2.5
        await query.message.reply_text("📊 אחוזי השינוי עודכנו ל-2.5%!")
    
    elif query.data == "change_volume_alert":
        user_settings[user_id]["volume_alert"] = 5000000
        await query.message.reply_text("📈 התראת נפח עודכנה ל-5,000,000!")

async def main():
   print("🚀 הבוט התחיל לפעול!")
   app = Application.builder().token(TOKEN).build()

   app.add_handler(CommandHandler("start", start))
   app.add_handler(CommandHandler("stop", stop))
   app.add_handler(CommandHandler("status", status))
   app.add_handler(CommandHandler("settings", settings_menu))
   app.add_handler(CallbackQueryHandler(change_setting))

   await app.run_polling()

if __name__ == "__main__":
    import asyncio
    nest_asyncio.apply()
    asyncio.run(main())
