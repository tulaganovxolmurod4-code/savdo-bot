import asyncio
import logging
import sys
import os
import http.server
import socketserver
import threading
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import start, add_ad, search, admin
from middleware import AccessMiddleware

class OkHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, *args):
        pass

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    with socketserver.TCPServer(("", port), OkHandler) as httpd:
        logging.info(f"Veb-server {port}-portda ishga tushdi")
        httpd.serve_forever()

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    threading.Thread(target=run_dummy_server, daemon=True).start()

    try:
        init_db()
        logging.info("Ma'lumotlar bazasi muvaffaqiyatli ulandi va sozlandi.")
    except Exception as e:
        logging.error(f"Ma'lumotlar bazasiga ulanishda xatolik: {e}")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.message.outer_middleware(AccessMiddleware())
    dp.callback_query.outer_middleware(AccessMiddleware())

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(add_ad.router)
    dp.include_router(search.router)

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot ishga tushdi va ulanishni kutmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")

