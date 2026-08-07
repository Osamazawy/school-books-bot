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
from database.connection import init_db
from handlers.user_handlers import register_user_handlers
from handlers.search_handlers import register_search_handlers
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
    register_admin_handlers(bot_app)
    register_search_handlers(bot_app)
    register_user_handlers(bot_app)
    return bot_app

bot_app = create_telegram_app()

async def ensure_bot_initialized():
    global bot_initialized
    if not bot_initialized:
        try:
            await init_db()
        except Exception as e:
            print(f"Error initializing DB in serverless: {e}", flush=True)
        try:
            await bot_app.initialize()
            await bot_app.start()
        except Exception as e:
            print(f"Error starting bot_app: {e}", flush=True)
        bot_initialized = True

async def execute_set_webhook():
    clean_webhook_url = WEBHOOK_URL.strip().strip('"').strip("'")
    if not clean_webhook_url:
        return {"error": "WEBHOOK_URL environment variable is missing"}
    
    await ensure_bot_initialized()
    target_url = f"{clean_webhook_url.rstrip('/')}/api/webhook"
    success = await bot_app.bot.set_webhook(url=target_url)
    return {"success": success, "webhook_url": target_url}

async def execute_webhook(request: Request):
    try:
        data = await request.json()
        await ensure_bot_initialized()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        await asyncio.sleep(0.5)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error handling Telegram webhook update: {e}\n{traceback.format_exc()}", flush=True)
        return {"status": "error", "message": str(e)}

@app.get("/")
@app.get("/api")
async def root():
    return {"status": "ok", "message": "School Books Bot API is active"}

@app.get("/set_webhook")
@app.get("/api/set_webhook")
async def set_webhook_route(request: Request):
    try:
        clean_webhook_url = WEBHOOK_URL.strip().strip('"').strip("'")
        if not clean_webhook_url:
            return {"error": "WEBHOOK_URL environment variable is missing"}
        
        await ensure_bot_initialized()
        target_url = f"{clean_webhook_url.rstrip('/')}/api/webhook"
        success = await bot_app.bot.set_webhook(url=target_url)
        return {"success": success, "webhook_url": target_url}
    except Exception as e:
        print(f"Error setting webhook: {e}\n{traceback.format_exc()}", flush=True)
        return {"success": False, "error": str(e)}

@app.post("/webhook")
@app.post("/api/webhook")
async def webhook_route(request: Request):
    try:
        data = await request.json()
        await ensure_bot_initialized()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error handling Telegram webhook update: {e}\n{traceback.format_exc()}", flush=True)
        return {"status": "error", "message": str(e)}

@app.api_route("/{full_path:path}", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def fallback_route(request: Request, full_path: str = ""):
    path = request.url.path.lower()
    action = request.query_params.get("action", "").lower()
    
    if action == "set_webhook" or "set_webhook" in path or "set_webhook" in full_path:
        return await set_webhook_route(request)
    
    if action == "webhook" or "webhook" in path or "webhook" in full_path:
        if request.method == "POST":
            return await webhook_route(request)
        return {"status": "ok", "message": "Webhook endpoint active"}
        
    return {
        "status": "ok",
        "message": "Bot is active and running on Vercel Serverless!"
    }
