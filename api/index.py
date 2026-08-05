import os
import sys
import asyncio
import traceback
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, Defaults
from telegram.constants import ParseMode

# إضافة المسار الرئيسي للمشروع
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BOT_TOKEN, WEBHOOK_URL
from handlers.user_handlers import register_user_handlers
from handlers.search_handlers import get_search_handler
from handlers.admin_handlers import register_admin_handlers

app = FastAPI()
bot_initialized = False

def create_telegram_app():
    defaults = Defaults(parse_mode=ParseMode.HTML)
    bot_app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .defaults(defaults)
        .build()
    )
    bot_app.add_handler(get_search_handler())
    register_admin_handlers(bot_app)
    register_user_handlers(bot_app)
    return bot_app

bot_app = create_telegram_app()

async def ensure_bot_initialized():
    global bot_initialized
    if not bot_initialized:
        await bot_app.initialize()
        await bot_app.start()
        bot_initialized = True

@app.get("/")
@app.get("/api")
@app.get("/api/index")
@app.get("/api/index.py")
def root():
    return {"status": "ok", "message": "Bot is active and running on Vercel Serverless!"}

@app.get("/set_webhook")
@app.get("/api/set_webhook")
@app.get("/api/index.py/set_webhook")
async def set_webhook():
    if not WEBHOOK_URL:
        return {"error": "WEBHOOK_URL environment variable is missing"}
    
    await ensure_bot_initialized()
    target_url = f"{WEBHOOK_URL.rstrip('/')}/api/webhook"
    success = await bot_app.bot.set_webhook(url=target_url)
    return {"success": success, "webhook_url": target_url}

@app.post("/webhook")
@app.post("/api/webhook")
@app.post("/api/index.py/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        await ensure_bot_initialized()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        await asyncio.sleep(0.6)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error handling Telegram webhook update: {e}\n{traceback.format_exc()}", flush=True)
        return {"status": "error", "message": str(e)}
