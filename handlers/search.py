import html
from aiogram import Router, types, F
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from database import get_connection
from keyboards import main_menu

router = Router()

# 1. E'lon qidirish tugmasi bosilganda kategoriyalarni chiqarish
@router.message(F.text == "🔍 E'lon qidirish")
async def search_ads_menu(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.button(text="🚗 Transport")
    builder.button(text="🏠 Ko'chmas mulk")
    builder.button(text="📱 Elektronika")
    builder.button(text="👕 Kiyim-kechak")
    builder.button(text="🛠 Boshqalar")
    builder.button(text="🔙 Asosiy menyu")
    builder.adjust(2, 2, 1, 1)

    await message.answer(
        "Qaysi kategoriyadan e'lon qidirmoqchisiz?",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# Asosiy menyuga qaytish
@router.message(F.text == "🔙 Asosiy menyu")
async def back_to_main(message: types.Message):
    await message.answer("Asosiy menyugiz:", reply_markup=main_menu(message.from_user.id))

# 2. Tanlangan kategoriya bo'yicha e'lonlarni chiqarish
CATEGORIES = ["🚗 Transport", "🏠 Ko'chmas mulk", "📱 Elektronika", "👕 Kiyim-kechak", "🛠 Boshqalar"]

@router.message(F.text.in_(CATEGORIES))
async def show_ads_by_category(message: types.Message):
    category = message.text

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, description, price, photo_id, user_id FROM ads WHERE category = %s AND status = 'active' ORDER BY id DESC LIMIT 10;",
        (category,)
    )
    ads = cursor.fetchall()
    cursor.close()
    conn.close()

    if not ads:
        await message.answer(f"❌ '{category}' kategoriyasida hozircha e'lonlar mavjud emas.")
        return

    await message.answer(f"<b>📌 '{category}' bo'yicha topilgan e'lonlar:</b>", parse_mode="HTML")

    for ad in ads:
        ad_id, title, description, price, photo_id, user_id = ad

        text = (
            f"🏷 <b>{html.escape(title or '')}</b>\n\n"
            f"📝 {html.escape(description or '')}\n"
            f"💰 <b>Narxi:</b> {html.escape(price or '')}\n"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="📞 Sotuvchi bilan bog'lanish", callback_data=f"contact_{user_id}")

        if photo_id:
            await message.answer_photo(
                photo=photo_id,
                caption=text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                text=text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )

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
        contact_info = f"👤 <b>Sotuvchi:</b> {html.escape(full_name or '')}\n📞 <b>Telefon:</b> {html.escape(phone or '')}"
        if username:
            contact_info += f"\n🔗 <b>Telegram:</b> @{html.escape(username)}"

        await callback.message.answer(contact_info, parse_mode="HTML")
    else:
        await callback.message.answer("❌ Sotuvchi ma'lumotlari topilmadi.")

    await callback.answer()

# 3. Mening e'lonlarim bo'limi
@router.message(F.text == "👤 Mening e'lonlarim")
async def my_ads(message: types.Message):
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
