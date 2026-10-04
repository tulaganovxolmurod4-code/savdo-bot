import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import start, add_ad, search

async def main():
    # Logging sozlamalari
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Ma'lumotlar bazasini ishga tushirish (jadvallarni yaratish)
    try:
        init_db()
        logging.info("Ma'lumotlar bazasi muvaffaqiyatli ulandi va sozlandi.")
    except Exception as e:
        logging.error(f"Ma'lumotlar bazasiga ulanishda xatolik: {e}")
        return

    # Bot va Dispatcher obyektini yaratish
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Routerlarni ulash
    dp.include_router(start.router)
    dp.include_router(add_ad.router)
    dp.include_router(search.router)

    # Eski xabarlarni o'tkazib yuborish va botni ishga tushirish
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot ishga tushdi va ulanishni kutmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")
