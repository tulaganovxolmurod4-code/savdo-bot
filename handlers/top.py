import asyncio
import html
import logging

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from admins import notify_ids
from categories import CAT_NAMES
from database import get_connection
from keyboards import main_menu
from settings import ADMIN_CONTACT, TOP_CARD_INFO, TOP_PACKAGES, money

router = Router()

TOP_CANCEL = "🔙 TOP'ni bekor qilish"

# Chek kutilayotganda shu tugmalardan biri bosilsa, jarayon bekor qilinadi
MENU_TEXTS = {
    "🔍 E'lon qidirish", "➕ E'lon berish", "👤 Mening e'lonlarim", "🛠 Admin panel",
    "🔎 So'z bilan qidirish", "🔙 Asosiy menyu",
} | set(CAT_NAMES)


class TopState(StatesGroup):
    receipt = State()   # foydalanuvchi chek rasmini yuboradigan bosqich


def cancel_kb():
    b = ReplyKeyboardBuilder()
    b.button(text=TOP_CANCEL)
    return b.as_markup(resize_keyboard=True)


def load_ad(ad_id, user_id):
    """(sarlavha, holat) yoki None. Faqat egasining e'loni."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT title, status FROM ads WHERE id = %s AND user_id = %s;", (ad_id, user_id))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def create_request(ad_id, user_id, days, price, receipt_file_id):
    """Chek so'rovini saqlaydi. Natija: {"status": "ok"|"gone"|"busy", ...}"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT a.title, a.status, u.full_name FROM ads a "
            "JOIN users u ON u.user_id = a.user_id WHERE a.id = %s AND a.user_id = %s;",
            (ad_id, user_id),
        )
        row = cur.fetchone()
        if not row or row[1] != "active":
            return {"status": "gone"}
        cur.execute("SELECT 1 FROM top_requests WHERE ad_id = %s AND status = 'pending';", (ad_id,))
        if cur.fetchone():
            return {"status": "busy"}
        cur.execute(
            "INSERT INTO top_requests (ad_id, user_id, days, price, receipt_file_id) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id, created_at;",
            (ad_id, user_id, days, price, receipt_file_id),
        )
        req_id, created = cur.fetchone()
        conn.commit()
        return {"status": "ok", "id": req_id, "created": created, "title": row[0], "user_name": row[2]}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def request_text(title, user_name, user_id, days, price, created):
    return (
        "🔥 <b>TOP so'rovi</b>\n\n"
        f"📦 E'lon: <b>{html.escape(title or '')}</b>\n"
        f"👤 {html.escape(user_name or '-')} (ID: <code>{user_id}</code>)\n"
        f"⏳ Muddat: {days} kun\n"
        f"💰 Summa: {money(price)} so'm\n"
        f"🕒 {created:%d.%m.%Y %H:%M}\n\n"
        "Chekni tekshirib, pul kartaga tushganini aniqlang, keyin tasdiqlang."
    )


def request_kb(req_id):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Tasdiqlash", callback_data=f"adm:topok:{req_id}")
    b.button(text="❌ Rad etish", callback_data=f"adm:topno:{req_id}")
    b.adjust(2)
    return b.as_markup()


# ---------------- Paketni tanlash ----------------

@router.callback_query(F.data.startswith("top:"))
async def top_start(cb: types.CallbackQuery):
    ad_id = int(cb.data.split(":")[1])
    ad = await asyncio.to_thread(load_ad, ad_id, cb.from_user.id)
    if not ad or ad[1] != "active":
        await cb.answer("Faqat faol e'lonni TOP qilish mumkin", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    for days, price in TOP_PACKAGES.items():
        b.button(text=f"🔥 {days} kun — {money(price)} so'm", callback_data=f"topd:{ad_id}:{days}")
    b.adjust(1)
    await cb.message.answer(
        f"🔥 «{ad[0]}» e'lonini TOP qilasiz.\n\n"
        "TOP e'lon o'z bo'limida va qidiruvda birinchi bo'lib, 🔥 belgisi bilan chiqadi.\n"
        "Muddatni tanlang:",
        reply_markup=b.as_markup(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("topd:"))
async def top_package(cb: types.CallbackQuery, state: FSMContext):
    _, ad_id, days = cb.data.split(":")
    ad_id, days = int(ad_id), int(days)
    if days not in TOP_PACKAGES:
        await cb.answer()
        return
    ad = await asyncio.to_thread(load_ad, ad_id, cb.from_user.id)
    if not ad or ad[1] != "active":
        await cb.answer("Faqat faol e'lonni TOP qilish mumkin", show_alert=True)
        return

    price = TOP_PACKAGES[days]
    if TOP_CARD_INFO:
        card = f"💳 Karta: <code>{html.escape(TOP_CARD_INFO)}</code>"
    else:
        contact = ADMIN_CONTACT or "admin"
        card = f"💳 Karta raqami uchun {html.escape(contact)} bilan bog'laning."

    await state.set_state(TopState.receipt)
    await state.update_data(ad_id=ad_id, days=days)
    await cb.message.answer(
        f"💰 To'lov: <b>{money(price)} so'm</b> ({days} kun TOP)\n"
        f"{card}\n\n"
        "To'lovni amalga oshirgach, <b>chek rasmini shu yerga yuboring</b> 👇",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await cb.answer()


# ---------------- Chek qabul qilish ----------------

@router.message(F.text == TOP_CANCEL)
async def top_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("TOP bekor qilindi.", reply_markup=main_menu(message.from_user.id))


@router.message(TopState.receipt, F.photo)
async def receipt_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ad_id, days = data.get("ad_id"), data.get("days")
    price = TOP_PACKAGES.get(days)
    if not ad_id or price is None:
        await state.clear()
        await message.answer("❌ Seans eskirgan. Qaytadan urinib ko'ring.", reply_markup=main_menu(message.from_user.id))
        return

    receipt_id = message.photo[-1].file_id
    try:
        r = await asyncio.to_thread(create_request, ad_id, message.from_user.id, days, price, receipt_id)
    except Exception:
        logging.exception("TOP so'rovini saqlashda xatolik")
        await message.answer("❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.")
        return

    if r["status"] == "gone":
        await state.clear()
        await message.answer("❌ Bu e'lon endi faol emas.", reply_markup=main_menu(message.from_user.id))
        return
    if r["status"] == "busy":
        await state.clear()
        await message.answer(
            "⏳ Bu e'lon uchun chek allaqachon tekshirilmoqda. Natijani kuting.",
            reply_markup=main_menu(message.from_user.id),
        )
        return

    await state.clear()
    await message.answer(
        "✅ Chek qabul qilindi. Admin tekshirib, natijani shu yerga yuboradi.",
        reply_markup=main_menu(message.from_user.id),
    )

    text = request_text(r["title"], r["user_name"], message.from_user.id, days, price, r["created"])
    for admin_id in notify_ids():
        try:
            await message.bot.send_photo(
                admin_id, receipt_id, caption=text, parse_mode="HTML", reply_markup=request_kb(r["id"])
            )
        except Exception:
            logging.warning("Adminga chek yetmadi: %s", admin_id)


@router.message(TopState.receipt)
async def receipt_other(message: types.Message, state: FSMContext):
    text = message.text or ""
    if text.startswith("/") or text in MENU_TEXTS:
        await state.clear()
        await message.answer(
            "TOP bekor qilindi. Kerakli tugmani qayta bosing.",
            reply_markup=main_menu(message.from_user.id),
        )
        return
    await message.answer("Iltimos, chekni RASM sifatida yuboring (screenshot).", reply_markup=cancel_kb())
