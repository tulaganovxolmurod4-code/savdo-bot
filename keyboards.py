from aiogram.utils.keyboard import ReplyKeyboardBuilder

# ADMIN_ID shu yerdan ham olinadi (boshqa fayllar eskicha import qilishi mumkin)
from admins import ADMIN_ID, is_admin


def main_menu(user_id):
    b = ReplyKeyboardBuilder()
    b.button(text="🔍 E'lon qidirish")
    b.button(text="➕ E'lon berish")
    b.button(text="👤 Mening e'lonlarim")
    if is_admin(user_id):
        b.button(text="🛠 Admin panel")
        b.adjust(2, 1, 1)
    else:
        b.adjust(2, 1)
    return b.as_markup(resize_keyboard=True)
