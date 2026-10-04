import html
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database import get_connection, get_user
from keyboards import main_menu

router = Router()


class Reg(StatesGroup):
    location = State()
    phone = State()
    name = State()


def location_kb():
    b = ReplyKeyboardBuilder()
    b.add(types.KeyboardButton(text="✅ Ha, joylashuvni yuborish", request_location=True))
    b.add(types.KeyboardButton(text="❌ Yo'q"))
    b.adjust(1)
    return b.as_markup(resize_keyboard=True)


def phone_kb():
    b = ReplyKeyboardBuilder()
    b.add(types.KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True))
    return b.as_markup(resize_keyboard=True)


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)
    if user and user["is_registered"]:
        await message.answer(
            f"Assalomu alaykum, <b>{html.escape(user['full_name'] or '')}</b>!\n\n"
            "Bu yerda siz kerakli mahsulot va xizmatlarni topishingiz yoki "
            "o'z e'lonlaringizni bepul joylashtirishingiz mumkin.\n\n"
            "Quyidagi tugmalardan birini tanlang:",
            reply_markup=main_menu(message.from_user.id),
            parse_mode="HTML",
        )
        return
    await message.answer(
        "Assalomu alaykum! Botdan foydalanish uchun avval ro'yxatdan o'tamiz.\n\n"
        "📍 Joylashuvingizni yuborasizmi?",
        reply_markup=location_kb(),
    )
    await state.set_state(Reg.location)


@router.message(Reg.location, F.location)
async def got_location(message: types.Message, state: FSMContext):
    if getattr(message, "forward_origin", None) or getattr(message, "forward_date", None):
        await message.answer("❌ Boshqa joydan yo'naltirilgan lokatsiya qabul qilinmaydi. Tugma orqali yuboring.")
        return
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    await message.answer("📞 Endi telefon raqamingizni yuboring (tugmani bosing):", reply_markup=phone_kb())
    await state.set_state(Reg.phone)


@router.message(Reg.location)
async def location_other(message: types.Message):
    await message.answer(
        "Joylashuvsiz botdan foydalanib bo'lmaydi. Davom etish uchun "
        "«✅ Ha, joylashuvni yuborish» tugmasini bosing.",
        reply_markup=location_kb(),
    )


@router.message(Reg.phone, F.contact)
async def got_phone(message: types.Message, state: FSMContext):
    c = message.contact
    if c.user_id != message.from_user.id:
        await message.answer("❌ Faqat o'zingizning raqamingizni tugma orqali yuboring.")
        return
    await state.update_data(phone=c.phone_number)
    await message.answer("👤 Ismingizni kiriting:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Reg.name)


@router.message(Reg.phone)
async def phone_other(message: types.Message):
    await message.answer("Iltimos, «📞 Telefon raqamni yuborish» tugmasini bosing.", reply_markup=phone_kb())


@router.message(Reg.name, F.text)
async def got_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("Ism 2 dan 50 tagacha belgi bo'lishi kerak. Qaytadan kiriting:")
        return
    data = await state.get_data()
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO users (user_id, username, full_name, phone, latitude, longitude, is_registered)
               VALUES (%s, %s, %s, %s, %s, %s, TRUE)
               ON CONFLICT (user_id) DO UPDATE SET
                 username = EXCLUDED.username, full_name = EXCLUDED.full_name,
                 phone = EXCLUDED.phone, latitude = EXCLUDED.latitude,
                 longitude = EXCLUDED.longitude, is_registered = TRUE;""",
            (message.from_user.id, message.from_user.username, name,
             data.get("phone"), data.get("lat"), data.get("lon")),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logging.exception("Ro'yxatdan o'tkazishda xatolik")
        await message.answer(f"❌ Xatolik: {str(e)[:150]}")
        return
    await state.clear()
    await message.answer(
        f"✅ Rahmat, <b>{html.escape(name)}</b>! Ro'yxatdan o'tdingiz.\n"
        "Endi botdan to'liq foydalanishingiz mumkin.",
        reply_markup=main_menu(message.from_user.id),
        parse_mode="HTML",
    )
