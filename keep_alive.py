from quart import Quart
import os
import aiohttp
import asyncio
import bot as bot

app = Quart(__name__)

URL = "https://bot-telegram-zfjr.onrender.com"

@app.route("/")
async def home():
    return "Bot is alive!"

@app.route("/ping")
async def ping_render():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as response:
                print(f"Pinged {URL}, Status: {response.status}")
        return "Request sent."
    except Exception as e:
        print(f"Failed to ping {URL}: {e}")
        return f"Failed: {e}"
    
async def ping_periodically():
    while True:
        await ping_render() 
        await asyncio.sleep(10)

async def main():
    port = int(os.getenv("PORT", 8080))  
    server = asyncio.create_task(app.run_task(host='0.0.0.0', port=port))
    pinger = asyncio.create_task(ping_periodically())
    bot_task = asyncio.create_task(bot.main())    
    await asyncio.gather(server, pinger, bot_task)

if __name__ == "__main__":
    asyncio.run(main())
