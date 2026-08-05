import os
import sys
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

@app.get("/")
@app.get("/api")
def root():
    return {"status": "ok", "message": "Bot is running on Vercel"}

@app.post("/api/webhook")
async def process_webhook(request: Request):
    data = await request.json()
    async with bot_app:
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
    return {"status": "ok"}

@app.get("/api/set_webhook")
async def set_webhook():
    if not WEBHOOK_URL:
        return {"error": "WEBHOOK_URL environment variable is missing"}
    
    target_url = f"{WEBHOOK_URL.rstrip('/')}/api/webhook"
    async with bot_app:
        success = await bot_app.bot.set_webhook(url=target_url)
    return {"success": success, "webhook_url": target_url}
