import os
import sys
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

async def execute_set_webhook():
    if not WEBHOOK_URL:
        return {"error": "WEBHOOK_URL environment variable is missing"}
    
    target_url = f"{WEBHOOK_URL.rstrip('/')}/api/webhook"
    async with bot_app:
        success = await bot_app.bot.set_webhook(url=target_url)
    return {"success": success, "webhook_url": target_url}

async def execute_webhook(request: Request):
    try:
        data = await request.json()
        async with bot_app:
            update = Update.de_json(data, bot_app.bot)
            await bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error handling Telegram webhook update: {e}\n{traceback.format_exc()}", flush=True)
        return {"status": "error", "message": str(e)}

@app.api_route("/{full_path:path}", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def handle_all_routes(request: Request, full_path: str = ""):
    query_path = request.query_params.get("path", "").lower()
    raw_url = str(request.url).lower()
    raw_path = str(request.url.path).lower()
    combined = f"{full_path} {raw_url} {raw_path} {query_path}".lower()
    
    if "set_webhook" in combined or query_path == "set_webhook":
        return await execute_set_webhook()
    
    if ("webhook" in combined or query_path == "webhook") and request.method == "POST":
        return await execute_webhook(request)
    
    return {
        "status": "ok",
        "message": "Bot is active and running on Vercel Serverless!",
        "path_detected": query_path or full_path
    }
