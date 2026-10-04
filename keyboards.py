import os
from aiogram.utils.keyboard import ReplyKeyboardBuilder

ADMIN_ID = int(os.environ.get("ADMIN_ID") or 0)

def main_menu(user_id):
    b = ReplyKeyboardBuilder()
    b.button(text="🔍 E'lon qidirish")
    b.button(text="➕ E'lon berish")
    b.button(text="👤 Mening e'lonlarim")
    if user_id == ADMIN_ID:
        b.button(text="🛠 Admin panel")
        b.adjust(2, 1, 1)
    else:
        b.adjust(2, 1)
    return b.as_markup(resize_keyboard=True)
