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
from handlers.user_handlers import register_user_handlers
from handlers.search_handlers import get_search_handler
from handlers.admin_handlers import register_admin_handlers

app = FastAPI()

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        err = f"Unhandled Exception: {exc}\n{traceback.format_exc()}"
        print(err, flush=True)
        return JSONResponse(status_code=500, content={"error": str(exc), "traceback": traceback.format_exc()})

bot_initialized = False

def create_telegram_app():
    defaults = Defaults(parse_mode=ParseMode.HTML)
    clean_token = BOT_TOKEN.strip().strip('"').strip("'")
    bot_app = (
        ApplicationBuilder()
        .token(clean_token)
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

@app.get("/{full_path:path}")
@app.get("/")
async def handle_get_requests(request: Request, full_path: str = ""):
    headers_str = str(dict(request.headers)).lower()
    raw_path = str(request.url.path).lower()
    query_str = str(request.query_params).lower()
    combined = f"{full_path} {raw_path} {query_str} {headers_str}".lower()
    
    if "set_webhook" in combined:
        clean_webhook_url = WEBHOOK_URL.strip().strip('"').strip("'")
        if not clean_webhook_url:
            return {"error": "WEBHOOK_URL environment variable is missing"}
        
        await ensure_bot_initialized()
        target_url = f"{clean_webhook_url.rstrip('/')}/api/webhook"
        success = await bot_app.bot.set_webhook(url=target_url)
        return {"success": success, "webhook_url": target_url}

    return {"status": "ok", "message": "Bot is active and running on Vercel Serverless!"}

@app.post("/{full_path:path}")
@app.post("/")
async def handle_post_requests(request: Request, full_path: str = ""):
    headers_str = str(dict(request.headers)).lower()
    raw_path = str(request.url.path).lower()
    combined = f"{full_path} {raw_path} {headers_str}".lower()
    
    if "webhook" in combined:
        try:
            data = await request.json()
            await ensure_bot_initialized()
            update = Update.de_json(data, bot_app.bot)
            await bot_app.process_update(update)
            await asyncio.sleep(1.2)
            return {"status": "ok"}
        except Exception as e:
            print(f"Error handling Telegram webhook update: {e}\n{traceback.format_exc()}", flush=True)
            return {"status": "error", "message": str(e)}
    return {"status": "ok"}
