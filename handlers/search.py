import html
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from database import get_connection
from keyboards import main_menu
from categories import CATEGORIES, CAT_NAMES

router = Router()

PAGE = 5  # bir safarda nechta e'lon ko'rsatiladi

AD_COLUMNS = "id, title, description, price, photo_id, user_id, address, latitude, longitude, subcategory"


class SearchState(StatesGroup):
    query = State()


def ad_text(title, description, price, address, lat, lon, sub):
    text = (
        f"🏷 <b>{html.escape(title or '')}</b>\n\n"
        f"📝 {html.escape(description or '')}\n"
        f"💰 <b>Narxi:</b> {html.escape(price or '')}\n"
    )
    if sub:
        text += f"📂 <b>Bo'lim:</b> {html.escape(sub)}\n"
    if address:
        text += f"🏪 <b>Manzil:</b> {html.escape(address)}\n"
    if lat is not None and lon is not None:
        text += (
            '🗺 <a href="https://www.google.com/maps?q=%s,%s">Joylashuvni xaritada ko\'rish</a>\n'
            % (lat, lon)
        )
    return text


async def send_ads(message: types.Message, ads):
    for ad_id, title, description, price, photo_id, user_id, address, lat, lon, sub in ads:
        text = ad_text(title, description, price, address, lat, lon, sub)

        builder = InlineKeyboardBuilder()
        builder.button(text="📞 Sotuvchi bilan bog'lanish", callback_data=f"contact_{user_id}")

        if photo_id:
            await message.answer_photo(
                photo=photo_id, caption=text,
                reply_markup=builder.as_markup(), parse_mode="HTML",
            )
        else:
            await message.answer(
                text=text, reply_markup=builder.as_markup(),
                parse_mode="HTML", disable_web_page_preview=True,
            )


def more_button(cb_data):
    b = InlineKeyboardBuilder()
    b.button(text="⬇️ Yana ko'rsatish", callback_data=cb_data)
    return b.as_markup()


def fetch_ads(extra_sql, params, offset):
    """PAGE ta e'lon va yana bor-yo'qligini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT {AD_COLUMNS} FROM ads WHERE status = 'active'{extra_sql} "
        "ORDER BY id DESC LIMIT %s OFFSET %s;",
        list(params) + [PAGE + 1, offset],
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows[:PAGE], len(rows) > PAGE


def sub_kb(ci):
    b = InlineKeyboardBuilder()
    cat = CAT_NAMES[ci]
    for si, name in enumerate(CATEGORIES[cat]):
        b.button(text=name, callback_data=f"s:{ci}:{si}:0")
    b.button(text="📋 Hammasi", callback_data=f"s:{ci}:a:0")
    b.button(text="🔎 Shu bo'limda qidirish", callback_data=f"q:{ci}")
    b.adjust(2)
    return b.as_markup()


# 1. E'lon qidirish tugmasi bosilganda kategoriyalarni chiqarish
@router.message(F.text == "🔍 E'lon qidirish")
async def search_ads_menu(message: types.Message, state: FSMContext):
    await state.clear()
    builder = ReplyKeyboardBuilder()
    for i in range(0, len(CAT_NAMES), 2):
        builder.row(*[types.KeyboardButton(text=n) for n in CAT_NAMES[i:i + 2]])
    builder.row(types.KeyboardButton(text="🔎 So'z bilan qidirish"))
    builder.row(types.KeyboardButton(text="🔙 Asosiy menyu"))

    await message.answer(
        "Qaysi kategoriyadan e'lon qidirmoqchisiz?",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )


# Asosiy menyuga qaytish
@router.message(F.text == "🔙 Asosiy menyu")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyugiz:", reply_markup=main_menu(message.from_user.id))


# 2. Kategoriya tanlanganda ichki bo'limlarni chiqarish
@router.message(F.text.in_(CAT_NAMES))
async def show_subcats(message: types.Message, state: FSMContext):
    await state.clear()
    ci = CAT_NAMES.index(message.text)
    await message.answer(
        f"<b>{message.text}</b>\nBo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=sub_kb(ci),
    )


# 3. Bo'lim bo'yicha e'lonlarni sahifalab chiqarish
@router.callback_query(F.data.startswith("s:"))
async def browse(cb: types.CallbackQuery):
    _, ci, si, off = cb.data.split(":")
    ci = int(ci)
    off = int(off)
    cat = CAT_NAMES[ci]
    sub = None if si == "a" else CATEGORIES[cat][int(si)]

    extra = " AND category = %s"
    params = [cat]
    if sub:
        extra += " AND subcategory = %s"
        params.append(sub)

    ads, more = fetch_ads(extra, params, off)
    title = cat if not sub else f"{cat} → {sub}"

    if not ads:
        if off == 0:
            await cb.message.answer(f"❌ «{title}» bo'limida hozircha e'lonlar yo'q.")
        await cb.answer()
        return

    if off > 0:
        try:
            await cb.message.delete()
        except Exception:
            pass
    else:
        await cb.message.answer(f"<b>📌 {title}</b>", parse_mode="HTML")

    await send_ads(cb.message, ads)

    if more:
        await cb.message.answer(
            "Yana e'lonlar bor 👇",
            reply_markup=more_button(f"s:{ci}:{si}:{off + PAGE}"),
        )
    else:
        await cb.message.answer("Bu bo'limdagi barcha e'lonlar ko'rsatildi.")
    await cb.answer()


# Sotuvchi haqida ma'lumot
@router.callback_query(F.data.startswith("contact_"))
async def contact_seller(callback: types.CallbackQuery):
    seller_id = int(callback.data.split("_")[1])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT phone, full_name, username FROM users WHERE user_id = %s;", (seller_id,))
    seller = cursor.fetchone()
    cursor.close()
    conn.close()

    if seller:
        phone, full_name, username = seller
        contact_info = (
            f"👤 <b>Sotuvchi:</b> {html.escape(full_name or '')}\n"
            f"📞 <b>Telefon:</b> {html.escape(phone or '')}"
        )
        if username:
            contact_info += f"\n🔗 <b>Telegram:</b> @{html.escape(username)}"
        await callback.message.answer(contact_info, parse_mode="HTML")
    else:
        await callback.message.answer("❌ Sotuvchi ma'lumotlari topilmadi.")

    await callback.answer()


# 4. Mening e'lonlarim bo'limi
@router.message(F.text == "👤 Mening e'lonlarim")
async def my_ads(message: types.Message, state: FSMContext):
    await state.clear()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, price, status FROM ads WHERE user_id = %s ORDER BY id DESC LIMIT 20;",
        (message.from_user.id,),
    )
    ads = cursor.fetchall()
    cursor.close()
    conn.close()

    if not ads:
        await message.answer("Siz hali e'lon bermagansiz.")
        return

    labels = {"active": "✅ Faol", "sold": "💰 Sotilgan", "blocked": "🚫 Bloklangan", "pending": "⏳ Kutilmoqda"}
    for ad_id, title, price, status in ads:
        b = InlineKeyboardBuilder()
        if status == "active":
            b.button(text="✅ Sotildi", callback_data=f"sold_{ad_id}")
        b.button(text="🗑 O'chirish", callback_data=f"del_{ad_id}")
        b.adjust(2)
        await message.answer(
            f"🔹 <b>{html.escape(title or '')}</b> — {html.escape(price or '')}\n{labels.get(status, status)}",
            parse_mode="HTML", reply_markup=b.as_markup(),
        )


@router.callback_query(F.data.startswith("sold_"))
async def mark_sold(callback: types.CallbackQuery):
    ad_id = int(callback.data.split("_")[1])
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE ads SET status='sold', sold_at=NOW() WHERE id=%s AND user_id=%s AND status='active';",
        (ad_id, callback.from_user.id),
    )
    n = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    if n:
        try:
            await callback.message.edit_text(f"{callback.message.text}\n\n💰 Sotilgan deb belgilandi", reply_markup=None)
        except Exception:
            pass
    await callback.answer("💰 Sotilgan!" if n else "Topilmadi")


@router.callback_query(F.data.startswith("del_"))
async def delete_my_ad(callback: types.CallbackQuery):
    ad_id = int(callback.data.split("_")[1])
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ads WHERE id=%s AND user_id=%s;", (ad_id, callback.from_user.id))
    conn.commit()
    cursor.close()
    conn.close()
    try:
        await callback.message.edit_text("🗑 E'lon o'chirildi.", reply_markup=None)
    except Exception:
        pass
    await callback.answer("O'chirildi")


# 5. So'z bilan qidirish (hamma joydan yoki tanlangan kategoriya ichidan)
def normalize(s):
    for ch in ("‘", "’", "ʻ", "ʼ", "`", "´"):
        s = s.replace(ch, "'")
    return s.lower().strip()


def back_kb():
    b = ReplyKeyboardBuilder()
    b.button(text="🔙 Asosiy menyu")
    return b.as_markup(resize_keyboard=True)


@router.message(F.text == "🔎 So'z bilan qidirish")
async def ask_query(message: types.Message, state: FSMContext):
    await state.set_state(SearchState.query)
    await state.update_data(ci=None, words=None)
    await message.answer(
        "Nimani qidiryapsiz? So'z yozing.\nMasalan: <i>iphone</i>, <i>nexia</i>, <i>kvartira</i>",
        parse_mode="HTML",
        reply_markup=back_kb(),
    )


@router.callback_query(F.data.startswith("q:"))
async def ask_query_in_category(cb: types.CallbackQuery, state: FSMContext):
    ci = int(cb.data.split(":")[1])
    await state.set_state(SearchState.query)
    await state.update_data(ci=ci, words=None)
    await cb.message.answer(
        f"«{CAT_NAMES[ci]}» bo'limida nimani qidiryapsiz? So'z yozing.\n"
        "Masalan: <i>iphone</i>, <i>samsung</i>",
        parse_mode="HTML",
        reply_markup=back_kb(),
    )
    await cb.answer()


async def search_page(message: types.Message, state: FSMContext, offset: int):
    data = await state.get_data()
    words = data.get("words") or []
    ci = data.get("ci")

    extra = ""
    params = []
    if ci is not None:
        extra += " AND category = %s"
        params.append(CAT_NAMES[ci])
    for w in words:
        extra += " AND (LOWER(title) LIKE %s OR LOWER(description) LIKE %s)"
        params += [f"%{w}%", f"%{w}%"]

    ads, more = fetch_ads(extra, params, offset)

    if not ads:
        if offset == 0:
            await message.answer("❌ Bunday e'lon topilmadi. Boshqa so'z bilan urinib ko'ring.")
        return

    if offset == 0:
        await message.answer("<b>🔎 Topilgan e'lonlar:</b>", parse_mode="HTML")

    await send_ads(message, ads)

    if more:
        await message.answer("Yana e'lonlar bor 👇", reply_markup=more_button(f"w:{offset + PAGE}"))
    else:
        await message.answer("Yana qidirish uchun boshqa so'z yozing yoki 🔙 Asosiy menyu ni bosing.")


@router.message(SearchState.query, F.text)
async def do_search(message: types.Message, state: FSMContext):
    text = normalize(message.text).replace("%", "").replace("_", "")
    words = [w for w in text.split() if len(w) >= 2][:5]
    if not words:
        await message.answer("Kamida 2 ta harfdan iborat so'z yozing.")
        return
    await state.update_data(words=words)
    await search_page(message, state, 0)


@router.callback_query(F.data.startswith("w:"))
async def more_words(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("words"):
        await cb.answer("Qidiruv eskirgan. Qaytadan so'z yozing.", show_alert=True)
        return
    offset = int(cb.data.split(":")[1])
    try:
        await cb.message.delete()
    except Exception:
        pass
    await search_page(cb.message, state, offset)
    await cb.answer()
