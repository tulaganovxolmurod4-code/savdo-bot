from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from states import AddAdState
from database import get_connection

router = Router()

# 1. E'lon berishni boshlash
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
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(AddAdState.category)

# Bekor qilish
@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("E'lon berish bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())

# 2. Kategoriyani qabul qilish va sarlavha so'rash
@router.message(AddAdState.category)
async def process_category(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        return await cancel_handler(message, state)
        
    await state.update_data(category=message.text)
    await message.answer("E'lon sarlavhasini kiriting (masalan: <i>Iphone 13 Pro Max holati yaxshi</i>):", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddAdState.title)

# 3. Sarlavhani qabul qilish va tavsif so'rash
@router.message(AddAdState.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Mahsulot yoki xizmat haqida batafsil ma'lumot (tavsif) kiriting:")
    await state.set_state(AddAdState.description)

# 4. Tavsifni qabul qilish va narx so'rash
@router.message(AddAdState.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Narxini kiriting (masalan: <i>500$ yoki 3000000 so'm</i>):", parse_mode="HTML")
    await state.set_state(AddAdState.price)

# 5. Narxni qabul qilish va rasm so'rash
@router.message(AddAdState.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Mahsulot rasmini yuboring:")
    await state.set_state(AddAdState.photo)

# 6. Rasmni qabul qilish va telefon raqam so'rash
@router.message(AddAdState.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True))
    
    await message.answer(
        "Aloqa uchun telefon raqamingizni yuboring (tugmani bosing yoki yozib yuboring):",
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(AddAdState.phone)

@router.message(AddAdState.photo)
async def process_photo_invalid(message: types.Message):
    await message.answer("Iltimos, rasm formatida yuboring!")

# 7. Telefon raqamni qabul qilish va tasdiqlashga chiqarish
@router.message(AddAdState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    
    data = await state.get_data()
    
    text = (
        "<b>📋 E'loningiz quyidagicha ko'rinishda:</b>\n\n"
        f"🏷 <b>Kategoriya:</b> {data['category']}\n"
        f"📌 <b>Sarlavha:</b> {data['title']}\n"
        f"📝 <b>Tavsif:</b> {data['description']}\n"
        f"💰 <b>Narx:</b> {data['price']}\n"
        f"📞 <b>Tel:</b> {data['phone']}\n\n"
        "Ma'lumotlar to'g'rimi?"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, tasdiqlash", callback_data="confirm_ad")
    builder.button(text="❌ Bekor qilish", callback_data="cancel_ad")
    builder.adjust(2)
    
    await message.answer_photo(
        photo=data['photo_id'],
        caption=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(AddAdState.confirm)

# 8. E'lonni bazaga saqlash va muvaffaqiyatli xabarini chiqarish
@router.callback_query(AddAdState.confirm, F.data == "confirm_ad")
async def confirm_ad(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Foydalanuvchini bazaga qo'shish
    cursor.execute(
        "INSERT INTO users (user_id, username, full_name, phone) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING;",
        (user_id, callback.from_user.username, callback.from_user.full_name, data['phone'])
    )
    
    # E'lonni saqlash
    cursor.execute(
        "INSERT INTO ads (user_id, category, title, description, price, photo_id, status) VALUES (%s, %s, %s, %s, %s, %s, 'active');",
        (user_id, data['category'], data['title'], data['description'], data['price'], data['photo_id'])
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Tasdiqlangach muvaffaqiyatli xabarni chiqarish va menyuni qaytarish
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔍 E'lon qidirish")
    builder.button(text="➕ E'lon berish")
    builder.button(text="👤 Mening e'lonlarim")
    builder.adjust(2, 1)

    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n<b>✅ E'loningiz muvaffaqiyatli qo'shildi va faollashtirildi!</b>",
        parse_mode="HTML"
    )
    await callback.message.answer("Quyidagi menyudan foydalanishingiz mumkin:", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.clear()
    await callback.answer("Muvaffaqiyatli saqlandi!")

@router.callback_query(AddAdState.confirm, F.data == "cancel_ad")
async def cancel_ad_cb(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_caption(caption="❌ E'lon berish bekor qilindi.", reply_markup=None)
    await callback.answer()
