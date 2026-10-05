import html
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from states import AddAdState
from database import get_connection, get_user
from keyboards import main_menu
from categories import CATEGORIES, CAT_NAMES

router = Router()

STAY_TEXT = "📍 Shu joylashuvda qolaman"
RETRY_TEXT = "🔄 Qayta kiritaman"


def category_kb():
    b = ReplyKeyboardBuilder()
    for i in range(0, len(CAT_NAMES), 2):
        b.row(*[types.KeyboardButton(text=n) for n in CAT_NAMES[i:i + 2]])
    b.row(types.KeyboardButton(text="❌ Bekor qilish"))
    return b.as_markup(resize_keyboard=True)


def sub_choice_kb(category):
    b = ReplyKeyboardBuilder()
    for name in CATEGORIES.get(category, []):
        b.button(text=name)
    b.adjust(2)
    b.row(types.KeyboardButton(text="❌ Bekor qilish"))
    return b.as_markup(resize_keyboard=True)


def loc_choice_kb():
    b = ReplyKeyboardBuilder()
    b.button(text=STAY_TEXT)
    b.button(text=RETRY_TEXT)
    b.button(text="❌ Bekor qilish")
    b.adjust(1)
    return b.as_markup(resize_keyboard=True)


def loc_new_kb():
    b = ReplyKeyboardBuilder()
    b.add(types.KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True))
    b.add(types.KeyboardButton(text="❌ Bekor qilish"))
    b.adjust(1)
    return b.as_markup(resize_keyboard=True)


@router.message(F.text == "➕ E'lon berish")
async def start_add_ad(message: types.Message, state: FSMContext):
    await message.answer(
        "E'lon berish uchun quyidagi kategoriyalardan birini tanlang:",
        reply_markup=category_kb(),
    )
    await state.set_state(AddAdState.category)


@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("E'lon berish bekor qilindi.", reply_markup=main_menu(message.from_user.id))


@router.message(AddAdState.category)
async def process_category(message: types.Message, state: FSMContext):
    if message.text not in CATEGORIES:
        await message.answer("Iltimos, kategoriyani tugmalardan tanlang.", reply_markup=category_kb())
        return
    await state.update_data(category=message.text)
    await message.answer(
        f"{message.text}\nEndi bo'limni tanlang:",
        reply_markup=sub_choice_kb(message.text),
    )
    await state.set_state(AddAdState.subcategory)


@router.message(AddAdState.subcategory)
async def process_subcategory(message: types.Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("category")
    if message.text not in CATEGORIES.get(category, []):
        await message.answer("Iltimos, bo'limni tugmalardan tanlang.", reply_markup=sub_choice_kb(category))
        return
    await state.update_data(subcategory=message.text)
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
    await message.answer(
        "🏪 Do'koningiz manzilini kiriting\n"
        "(masalan: <i>Toshkent, Chilonzor, 7-kvartal, 15-do'kon</i>):",
        parse_mode="HTML",
    )
    await state.set_state(AddAdState.address)


@router.message(AddAdState.address, F.text)
async def process_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 3:
        await message.answer("Manzil juda qisqa. Iltimos, to'liqroq kiriting:")
        return
    await state.update_data(address=address)

    user = get_user(message.from_user.id)
    lat = (user or {}).get("latitude")
    lon = (user or {}).get("longitude")

    if lat is not None and lon is not None:
        await message.answer("📍 Ro'yxatdan o'tganda yuborgan joylashuvingiz:")
        await message.answer_location(lat, lon)
        await message.answer(
            "E'lon shu joylashuv bilan chiqsinmi yoki yangisini kiritasizmi?",
            reply_markup=loc_choice_kb(),
        )
        await state.set_state(AddAdState.loc_choice)
    else:
        await message.answer(
            "📍 Joylashuvingizni yuboring (tugmani bosing):",
            reply_markup=loc_new_kb(),
        )
        await state.set_state(AddAdState.loc_new)


@router.message(AddAdState.loc_choice, F.text == STAY_TEXT)
async def loc_stay(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    lat = (user or {}).get("latitude")
    lon = (user or {}).get("longitude")
    if lat is None or lon is None:
        await message.answer("📍 Joylashuvingizni yuboring (tugmani bosing):", reply_markup=loc_new_kb())
        await state.set_state(AddAdState.loc_new)
        return
    await state.update_data(lat=lat, lon=lon)
    await message.answer("Mahsulot rasmini yuboring:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddAdState.photo)


@router.message(AddAdState.loc_choice, F.text == RETRY_TEXT)
async def loc_retry(message: types.Message, state: FSMContext):
    await message.answer(
        "📍 Yangi joylashuvingizni yuboring (tugmani bosing):",
        reply_markup=loc_new_kb(),
    )
    await state.set_state(AddAdState.loc_new)


@router.message(AddAdState.loc_choice)
async def loc_choice_other(message: types.Message):
    await message.answer("Iltimos, tugmalardan birini tanlang.", reply_markup=loc_choice_kb())


@router.message(AddAdState.loc_new, F.location)
async def loc_new_got(message: types.Message, state: FSMContext):
    if getattr(message, "forward_origin", None) or getattr(message, "forward_date", None):
        await message.answer("❌ Yo'naltirilgan lokatsiya qabul qilinmaydi. Tugma orqali yuboring.")
        return
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    await message.answer("Mahsulot rasmini yuboring:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddAdState.photo)


@router.message(AddAdState.loc_new)
async def loc_new_other(message: types.Message):
    await message.answer(
        "Iltimos, «📍 Joylashuvni yuborish» tugmasini bosing.",
        reply_markup=loc_new_kb(),
    )


@router.message(AddAdState.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    user = get_user(message.from_user.id)
    await state.update_data(phone=(user or {}).get("phone") or "")
    data = await state.get_data()

    text = (
        "<b>📋 E'loningiz quyidagicha ko'rinishda:</b>\n\n"
        f"🏷 <b>Kategoriya:</b> {html.escape(data['category'] or '')}\n"
        f"📂 <b>Bo'lim:</b> {html.escape(data.get('subcategory') or '')}\n"
        f"📌 <b>Sarlavha:</b> {html.escape(data['title'] or '')}\n"
        f"📝 <b>Tavsif:</b> {html.escape(data['description'] or '')}\n"
        f"💰 <b>Narx:</b> {html.escape(data['price'] or '')}\n"
        f"🏪 <b>Manzil:</b> {html.escape(data.get('address') or '')}\n"
    )
    if data.get("lat") is not None and data.get("lon") is not None:
        text += (
            '🗺 <a href="https://www.google.com/maps?q=%s,%s">Joylashuvni xaritada ko\'rish</a>\n'
            % (data["lat"], data["lon"])
        )
    text += (
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
            "INSERT INTO ads (user_id, category, subcategory, title, description, price, photo_id, address, latitude, longitude, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active');",
            (user_id, data["category"], data.get("subcategory"), data["title"], data["description"],
             data["price"], data["photo_id"], data.get("address"), data.get("lat"), data.get("lon")),
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
