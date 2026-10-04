from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Start buyrug'i uchun asosiy menyu"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔍 E'lon qidirish")
    builder.button(text="➕ E'lon berish")
    builder.button(text="👤 Mening e'lonlarim")
    builder.adjust(2, 1) # Tugmalar joylashuvi: 2 tasi tepada, 1 tasi pastda
    
    welcome_text = (
        f"Assalomu alaykum, <b>{message.from_user.full_name}</b>!\n\n"
        "Bu yerda siz kerakli mahsulot va xizmatlarni topishingiz yoki o'z e'lonlaringizni "
        "bepul joylashtirishingiz mumkin.\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=builder.as_markup(resize_keyboard=True),
        parse_mode="HTML"
    )
