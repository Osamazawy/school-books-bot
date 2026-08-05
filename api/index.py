import os
import sys
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, Defaults
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest

# إدراج مسار المشروع الرئيسي
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BOT_TOKEN, WEBHOOK_URL
from utils.logger import logger
from database.connection import init_db
from handlers.user_handlers import register_user_handlers
from handlers.search_handlers import get_search_handler
from handlers.admin_handlers import register_admin_handlers

app = FastAPI(title="Telegram School Books Bot API")

ptb_application = None

async def get_application():
    global ptb_application
    if ptb_application is None:
        logger.info("جاري تهيئة تطبيق البوت لـ Vercel Serverless...")
        request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=30.0
        )
        defaults = Defaults(parse_mode=ParseMode.HTML)
        ptb_application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .request(request)
            .defaults(defaults)
            .build()
        )
        ptb_application.add_handler(get_search_handler())
        register_admin_handlers(ptb_application)
        register_user_handlers(ptb_application)

        await ptb_application.initialize()
        await init_db()
        logger.info("تم تهيئة البوت وقاعدة البيانات بنجاح.")
    return ptb_application


@app.on_event("startup")
async def on_startup():
    await get_application()


@app.get("/")
@app.get("/api")
async def health_check():
    return {
        "status": "online",
        "service": "Telegram School Books Bot",
        "platform": "Vercel Serverless"
    }


@app.post("/api/webhook")
async def process_webhook(request: Request):
    """استقبال التحديثات من Telegram Webhook وتمريرها للبوت."""
    try:
        application = await get_application()
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"خطأ أثناء معالجة Webhook: {e}")
        return Response(status_code=500)


@app.get("/api/set_webhook")
async def set_webhook():
    """تفعيل رابط الـ Webhook تلقائياً مع سيرفرات تلجرام."""
    if not WEBHOOK_URL:
        return {"error": "لم يتم تعيين متغير البيئة WEBHOOK_URL في Vercel!"}
    
    application = await get_application()
    target_url = f"{WEBHOOK_URL.rstrip('/')}/api/webhook"
    success = await application.bot.set_webhook(url=target_url)
    return {
        "success": success,
        "webhook_url": target_url
    }
