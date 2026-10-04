import html
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from states import AddAdState
from database import get_connection, get_user
from keyboards import main_menu

router = Router()

@router.message(F.text == "➕ E'lon berish")
async def start_add_ad(message: types.Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    builder.button(text="🚗 Transport")
    builder.button(text="🏠 Ko'chmas mulk")
    builder.button(text="📱 Elektronika")
    builder.button(text="👕 Kiyim-kechak")
    builder.button(text="🛠 Boshqalar")
    builder.button(text="❌ Bekor qilish")
    builder.adjust(2, 2, 1, 1)
    await message.answer(
        "E'lon berish uchun quyidagi kategoriyalardan birini tanlang:",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )
    await state.set_state(AddAdState.category)

@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("E'lon berish bekor qilindi.", reply_markup=main_menu(message.from_user.id))

@router.message(AddAdState.category)
async def process_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer(
        "E'lon sarlavhasini kiriting (masalan: <i>Iphone 13 Pro Max holati yaxshi</i>):",
        parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove(),
    )
    await state.set_state(AddAdState.title)

@router.message(AddAdState.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Mahsulot yoki xizmat haqida batafsil ma'lumot (tavsif
