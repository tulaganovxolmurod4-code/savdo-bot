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
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    await state.set_state(AddAdState.title)


@router.message(AddAdState.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Mahsulot yoki xizmat haqida batafsil ma'lumot (tavsif) kiriting:")
    await state.set_state(AddAdState.description)


@router.message(AddAdState.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Narxini kiriting (masalan: <i>500$ yoki 3000000 so'm</i>):", parse_mode="HTML")
    await state.set_state(AddAdState.price)


@router.message(AddAdState.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Mahsulot rasmini yuboring:")
    await state.set_state(AddAdState.photo)


@router.message(AddAdState.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    user = get_user(message.from_user.id)
    await state.update_data(phone=(user or {}).get("phone") or "")
    data = await state.get_data()

    text = (
        "<b>📋 E'loningiz quyidagicha ko'rinishda:</b>\n\n"
        f"🏷 <b>Kategoriya:</b> {html.escape(data['category'] or '')}\n"
        f"📌 <b>Sarlavha:</b> {html.escape(data['title'] or '')}\n"
        f"📝 <b>Tavsif:</b> {html.escape(data['description'] or '')}\n"
        f"💰 <b>Narx:</b> {html.escape(data['price'] or '')}\n"
        f"📞 <b>Tel:</b> {html.escape(data['phone'])}\n\n"
        "Ma'lumotlar to'g'rimi?"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, tasdiqlash", callback_data="confirm_ad")
    builder.button(text="❌ Bekor qilish", callback_data="cancel_ad")
    builder.adjust(2)
    await message.answer_photo(
        photo=data["photo_id"],
        caption=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await state.set_state(AddAdState.confirm)


@router.message(AddAdState.photo)
async def process_photo_invalid(message: types.Message):
    await message.answer("Iltimos, rasm formatida yuboring!")


@router.callback_query(F.data == "confirm_ad")
async def confirm_ad(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id

    if not data or "category" not in data:
        await callback.message.answer("❌ Seans eskirgan. Iltimos, qaytadan e'lon bering.")
        await state.clear()
        await callback.answer()
        return

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (user_id, username, full_name, phone) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING;",
            (user_id, callback.from_user.username, callback.from_user.full_name, data.get("phone", "")),
        )
        cur.execute(
            "INSERT INTO ads (user_id, category, title, description, price, photo_id, status) VALUES (%s, %s, %s, %s, %s, %s, 'active');",
            (user_id, data["category"], data["title"], data["description"], data["price"], data["photo_id"]),
        )
        conn.commit()
        cur.close()
    except Exception as e:
        logging.exception("E'lonni saqlashda xatolik")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        await callback.answer("❌ Saqlashda xatolik: " + str(e)[:150], show_alert=True)
        return
    finally:
        if conn:
            conn.close()

    try:
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n✅ E'loningiz muvaffaqiyatli qo'shildi va faollashtirildi!",
            reply_markup=None,
        )
    except Exception:
        pass
    await callback.message.answer("Quyidagi menyudan foydalanishingiz mumkin:", reply_markup=main_menu(user_id))
    await state.clear()
    await callback.answer("Muvaffaqiyatli saqlandi!")


@router.callback_query(F.data == "cancel_ad")
async def cancel_ad_cb(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_caption(caption="❌ E'lon berish bekor qilindi.", reply_markup=None)
    except Exception:
        pass
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu(callback.from_user.id))
    await callback.answer("Bekor qilindi")

