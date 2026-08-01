"""
سكربت التعبئة التلقائية لجميع المراحل والصفوف الدراسية
(المرحلة الابتدائية، المتوسطة، والإعدادية بصفوف العلمي والأدبي)
"""
import asyncio
from database.connection import init_db
from database import repository
from utils.logger import logger

async def seed():
    await init_db()
    logger.info("جاري إضافة الهيكلية الدراسية الكاملة...")

    # 1. المرحلة الابتدائية
    stg_elem = await repository.add_stage("المرحلة الابتدائية")
    if stg_elem:
        await repository.add_class(stg_elem, "الأول الابتدائي")
        await repository.add_class(stg_elem, "الثاني الابتدائي")
        await repository.add_class(stg_elem, "الثالث الابتدائي")
        await repository.add_class(stg_elem, "الرابع الابتدائي")
        await repository.add_class(stg_elem, "الخامس الابتدائي")
        await repository.add_class(stg_elem, "السادس الابتدائي")

    # 2. المرحلة المتوسطة
    stg_mid = await repository.add_stage("المرحلة المتوسطة")
    if stg_mid:
        await repository.add_class(stg_mid, "الأول المتوسط")
        await repository.add_class(stg_mid, "الثاني المتوسط")
        await repository.add_class(stg_mid, "الثالث المتوسط")

    # 3. المرحلة الإعدادية (العلمي والأدبي)
    stg_prep = await repository.add_stage("المرحلة الإعدادية")
    if stg_prep:
        await repository.add_class(stg_prep, "الرابع العلمي")
        await repository.add_class(stg_prep, "الرابع الأدبي")
        await repository.add_class(stg_prep, "الخامس العلمي")
        await repository.add_class(stg_prep, "الخامس الأدبي")
        await repository.add_class(stg_prep, "السادس العلمي")
        await repository.add_class(stg_prep, "السادس الأدبي")

    logger.info("كتمل بناء الهيكلية الدراسية بنجاح! 📚")

if __name__ == "__main__":
    asyncio.run(seed())
