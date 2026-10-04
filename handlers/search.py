from aiogram import Router, types, F
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from database import get_connection

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
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔍 E'lon qidirish")
    builder.button(text="➕ E'lon berish")
    builder.button(text="👤 Mening e'lonlarim")
    builder.adjust(2, 1)
    
    await message.answer("Asosiy menyugiz:", reply_markup=builder.as_markup(resize_keyboard=True))

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
        await message.answer(f"❌ '{category'}' kategoriyasida hozircha e'lonlar mavjud emas.")
        return
    
    await message.answer(f"<b>📌 '{category}' bo'yicha topilgan e'lonlar:</b>", parse_mode="HTML")
    
    for ad in ads:
        ad_id, title, description, price, photo_id, user_id = ad
        
        text = (
            f"🏷 <b>{title}</b>\n\n"
            f"📝 {description}\n"
            f"💰 <b>Narxi:</b> {price}\n"
        )
        
        # Sotuvchi bilan bog'lanish uchun inline tugma
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

# Sotuvchi haqida ma'lumot yoki telefon raqamini chiqarish
@router.callback_query(F.data.startswith("contact_"))
async def contact_seller(callback: types.CallbackQuery):
    seller_id = callback.data.split("_")[1]
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT phone, full_name, username FROM users WHERE user_id = %s;", (seller_id,))
    seller = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if seller:
        phone, full_name, username = seller
        contact_info = f"👤 <b>Sotuvchi:</b> {full_name}\n📞 <b>Telefon:</b> {phone}"
        if username:
            contact_info += f"\n🔗 <b>Telegram:</b> @{username}"
        
        await callback.message.answer(contact_info, parse_mode="HTML")
    else:
        await callback.message.answer("❌ Sotuvchi ma'lumotlari topilmadi.")
        
    await callback.answer()

# 3. Mening e'lonlarim bo'limi
@router.message(F.text == "👤 Mening e'lonlarim")
async def my_ads(message: types.Message):
    user_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, price, status FROM ads WHERE user_id = %s ORDER BY id DESC;",
        (user_id,)
    )
    ads = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not ads:
        await message.answer("Siz hali e'lon bermagansiz.")
        return
    
    text = "<b>📋 Sizning e'lonlaringiz:</b>\n\n"
    for ad in ads:
        ad_id, title, price, status = ad
        status_emoji = "✅ Faol" if status == 'active' else "⏳ Kutilmoqda"
        text += f"🔹 <b>{title}</b> — {price} ({status_emoji})\n"
        
    await message.answer(text, parse_mode="HTML")
