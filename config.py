import os
from dotenv import load_dotenv

# Agar .dotenv fayl bo'lsa o'qiydi (Render'da esa Environment variables'dan oladi)
load_dotenv()

# BotFather'dan olingan token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# PostgreSQL ma'lumotlar bazasi URL manzili
DATABASE_URL = os.getenv("DATABASE_URL")

# Token tekshiruvi
if not BOT_TOKEN:
    raise ValueError("Xatolik: BOT_TOKEN topilmadi! Render yoki .env muhitida BOT_TOKEN ni kiriting.")

if not DATABASE_URL:
    raise ValueError("Xatolik: DATABASE_URL topilmadi! Ma'lumotlar bazasi manzilini kiriting.")
