import os
import sys
import asyncio
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import ApplicationBuilder, Defaults
from telegram.constants import ParseMode

# إضافة المسار الرئيسي للمشروع
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BOT_TOKEN, WEBHOOK_URL

app = FastAPI()

bot_app = None
bot_initialized = False

def get_telegram_app():
    global bot_app
    if bot_app is None:
        from handlers.user_handlers import register_user_handlers
        from handlers.search_handlers import register_search_handlers
        from handlers.admin_handlers import register_admin_handlers

        defaults = Defaults(parse_mode=ParseMode.HTML)
        clean_token = BOT_TOKEN.strip().strip('"').strip("'")
        bot_app = (
            ApplicationBuilder()
            .token(clean_token)
            .defaults(defaults)
            .build()
        )
        register_admin_handlers(bot_app)
        register_search_handlers(bot_app)
        register_user_handlers(bot_app)
    return bot_app

async def ensure_bot_initialized():
    global bot_initialized
    app_obj = get_telegram_app()
    if not bot_initialized:
        try:
            await app_obj.initialize()
            await app_obj.start()
        except Exception as e:
            print(f"Error starting Telegram app: {e}\n{traceback.format_exc()}", flush=True)
        bot_initialized = True
    return app_obj

async def execute_set_webhook():
    try:
        clean_webhook_url = WEBHOOK_URL.strip().strip('"').strip("'") if WEBHOOK_URL else "https://school-books-bot-jrt8.vercel.app"
        app_obj = await ensure_bot_initialized()
        target_url = f"{clean_webhook_url.rstrip('/')}/api/webhook"
        success = await app_obj.bot.set_webhook(url=target_url)
        return JSONResponse(status_code=200, content={"success": success, "webhook_url": target_url})
    except Exception as e:
        print(f"Error setting webhook: {e}\n{traceback.format_exc()}", flush=True)
        return JSONResponse(status_code=200, content={"status": "error", "message": str(e), "traceback": traceback.format_exc()})

async def execute_webhook(request: Request):
    try:
        data = await request.json()
        app_obj = await ensure_bot_initialized()
        update = Update.de_json(data, app_obj.bot)
        if update:
            await app_obj.process_update(update)
        return JSONResponse(status_code=200, content={"status": "ok"})
    except Exception as e:
        print(f"Error handling Telegram webhook update: {e}\n{traceback.format_exc()}", flush=True)
        return JSONResponse(status_code=200, content={"status": "error", "message": str(e)})

@app.api_route("/{full_path:path}", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def handle_routes(request: Request, full_path: str = ""):
    action = request.query_params.get("action", "").lower()
    path = (full_path or request.url.path or "").lower().strip("/")
    
    if action == "set_webhook" or "set_webhook" in path:
        return await execute_set_webhook()
    
    if request.method == "POST" and (action == "webhook" or "webhook" in path):
        return await execute_webhook(request)
        
    return {
        "status": "ok",
        "message": "Bot is active and running on Vercel Serverless!"
    }
