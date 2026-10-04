import html
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_connection
from keyboards import ADMIN_ID

router = Router()
router.message.filter(F.from_user.id == ADMIN_ID)
router.callback_query.filter(F.from_user.id == ADMIN_ID)
PAGE = 8

def q(sql, params=(), mode="all"):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        res = None
        if mode == "all":
            res = cur.fetchall()
        elif mode == "one":
            res = cur.fetchone()
        elif mode == "count":
            res = cur.rowcount
        conn.commit()
        return res
    finally:
        cur.close()
        conn.close()

def stats_text():
    u = q("SELECT COUNT(*), COUNT(*) FILTER (WHERE is_registered), COUNT(*) FILTER (WHERE is_banned) FROM users;", mode="one")
    a = q("SELECT COUNT(*), COUNT(*) FILTER (WHERE status='active'), COUNT(*) FILTER (WHERE status='sold') FROM ads;", mode="one")
    return (
        "<b>🛠 Admin panel</b>\n\n"
        f"👥 Ro'yxatdan o'tganlar: <b>{u[1]}</b> (bloklangan: {u[2]})\n"
        f"📋 Jami e'lonlar: <b>{a[0]}</b>\n"
        f"✅ Faol: <b>{a[1]}</b>\n"
        f"💰 Sotilgan: <b>{a[2]}</b>"
    )

def panel_kb():
    b = InlineKeyboardBuilder()
    b.button(text="👥 Foydalanuvchilar", callback_data="adm:users:0")
    b.button(text="🔄 Yangilash", callback_data="adm:home")
    b.adjust(1)
    return b.as_markup()

@router.message(F.text == "🛠 Admin panel")
@router.message(Command("admin"))
async def panel(message: types.Message):
    await message.answer(stats_text(), parse_mode="HTML", reply_markup=panel_kb())

@router.callback_query(F.data == "adm:home")
async def home(cb: types.CallbackQuery):
    try:
        await cb.message.edit_text(stats_text(), parse_mode="HTML", reply_markup=panel_kb())
    except Exception:
        pass
    await cb.answer()

@router.callback_query(F.data.startswith("adm:users:"))
async def users_list(cb: types.CallbackQuery):
    page = int(cb.data.split(":")[2])
    rows = q(
        """SELECT u.user_id, u.full_name, u.is_banned, COUNT(a.id),
                  COUNT(a.id) FILTER (WHERE a.status='sold')
           FROM users u LEFT JOIN ads a ON a.user_id = u.user_id
           WHERE u.is_registered
           GROUP BY u.user_id ORDER BY u.created_at DESC LIMIT %s OFFSET %s;""",
        (PAGE + 1, page * PAGE),
    )
    more = len(rows) > PAGE
    rows = rows[:PAGE]
    b = InlineKeyboardBuilder()
    for uid, name, banned, total, sold in rows:
        b.button(
            text=f"{'🚫 ' if banned else ''}{name} • {total} e'lon • {sold} sotilgan",
            callback_data=f"adm:user:{uid}",
        )
    b.adjust(1)
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"adm:users:{page-1}"))
    nav.append(types.InlineKeyboardButton(text="🏠", callback_data="adm:home"))
    if more:
        nav.append(types.InlineKeyboardButton(text="➡️", callback_data=f"adm:users:{page+1}"))
    b.row(*nav)
    text = f"<b>👥 Foydalanuvchilar</b> (sahifa {page+1})" if rows else "Hali ro'yxatdan o'tgan foydalanuvchi yo'q."
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=b.as_markup())
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=b.as_markup())
    await cb.answer()

def user_kb(uid, banned):
    b = InlineKeyboardBuilder()
    if banned:
        b.button(text="✅ Blokdan chiqarish", callback_data=f"adm:unban:{uid}")
    else:
        b.button(text="🚫 Bloklash", callback_data=f"adm:ban:{uid}")
    b.button(text="📋 E'lonlari", callback_data=f"adm:ads:{uid}")
    b.button(text="🗑 Barcha e'lonlarini o'chirish", callback_data=f"adm:delads:{uid}")
    b.button(text="⬅️ Ro'yxat", callback_data="adm:users:0")
    b.adjust(2, 1, 1)
    return b.as_markup()

@router.callback_query(F.data.startswith("adm:user:"))
async def user_card(cb: types.CallbackQuery):
    uid = int(cb.data.split(":")[2])
    u = q("SELECT full_name, username, phone, latitude, longitude, is_banned, created_at FROM users WHERE user_id=%s;", (uid,), "one")
    if not u:
        await cb.answer("Topilmadi", show_alert=True)
        return
    name, username, phone, lat, lon, banned, created = u
    s = q("SELECT COUNT(*), COUNT(*) FILTER (WHERE status='active'), COUNT(*) FILTER (WHERE status='sold') FROM ads WHERE user_id=%s;", (uid,), "one")
    text = (
        f"👤 <b>{html.escape(name or '-')}</b>\n"
        f"🆔 <code>{uid}</code>\n"
        f"🔗 {('@' + username) if username else '—'}\n"
        f"📞 {phone or '—'}\n"
        f"📅 {created:%Y-%m-%d %H:%M}\n\n"
        f"📋 E'lonlar: {s[0]} (faol {s[1]}, sotilgan {s[2]})\n"
        f"Holati: {'🚫 Bloklangan' if banned else '✅ Faol'}"
    )
    await cb.message.answer(text, parse_mode="HTML", reply_markup=user_kb(uid, banned))
    if lat is not None and lon is not None:
        await cb.message.answer_location(lat, lon)
    await cb.answer()

@router.callback_query(F.data.startswith("adm:ban:"))
async def ban(cb: types.CallbackQuery):
    uid = int(cb.data.split(":")[2])
    if uid == ADMIN_ID:
        await cb.answer("O'zingizni bloklab bo'lmaydi", show_alert=True)
        return
    q("UPDATE users SET is_banned=TRUE WHERE user_id=%s;", (uid,), "count")
    q("UPDATE ads SET status='blocked' WHERE user_id=%s AND status='active';", (uid,), "count")
    try:
        await cb.message.edit_reply_markup(reply_markup=user_kb(uid, True))
    except Exception:
        pass
    try:
        await cb.bot.send_message(uid, "🚫 Siz admin tomonidan bloklandingiz.")
    except Exception:
        pass
    await cb.answer("🚫 Bloklandi, e'lonlari yashirildi", show_alert=True)

@router.callback_query(F.data.startswith("adm:unban:"))
async def unban(cb: types.CallbackQuery):
    uid = int(cb.data.split(":")[2])
    q("UPDATE users SET is_banned=FALSE WHERE user_id=%s;", (uid,), "count")
    q("UPDATE ads SET status='active' WHERE user_id=%s AND status='blocked';", (uid,), "count")
    try:
        await cb.message.edit_reply_markup(reply_markup=user_kb(uid, False))
    except Exception:
        pass
    await cb.answer("✅ Blokdan chiqarildi", show_alert=True)

@router.callback_query(F.data.startswith("adm:delads:"))
async def delads_ask(cb: types.CallbackQuery):
    uid = int(cb.data.split(":")[2])
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ha, o'chirish", callback_data=f"adm:delads_yes:{uid}")
    b.button(text="❌ Yo'q", callback_data=f"adm:user:{uid}")
    b.adjust(2)
    await cb.message.answer("Shu foydalanuvchining BARCHA e'lonlari o'chiriladi. Ishonchingiz komilmi?", reply_markup=b.as_markup())
    await cb.answer()

@router.callback_query(F.data.startswith("adm:delads_yes:"))
async def delads_yes(cb: types.CallbackQuery):
    uid = int(cb.data.split(":")[2])
    n = q("DELETE FROM ads WHERE user_id=%s;", (uid,), "count")
    try:
        await cb.message.edit_text(f"✅ {n} ta e'lon o'chirildi.")
    except Exception:
        pass
    await cb.answer()

@router.callback_query(F.data.startswith("adm:ads:"))
async def user_ads(cb: types.CallbackQuery):
    uid = int(cb.data.split(":")[2])
    rows = q("SELECT id, category, title, description, price, photo_id, status FROM ads WHERE user_id=%s ORDER BY id DESC LIMIT 10;", (uid,))
    if not rows:
        await cb.answer("E'lonlari yo'q", show_alert=True)
        return
    for ad_id, cat, title, desc, price, photo, status in rows:
        text = (
            f"🏷 {html.escape(cat or '')}\n<b>{html.escape(title or '')}</b>\n"
            f"{html.escape(desc or '')}\n💰 {html.escape(price or '')}\nHolati: {status}"
        )
        b = InlineKeyboardBuilder()
        b.button(text="🗑 O'chirish", callback_data=f"adm:delad:{ad_id}")
        if photo:
            await cb.message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=b.as_markup())
        else:
            await cb.message.answer(text, parse_mode="HTML", reply_markup=b.as_markup())
    await cb.answer()

@router.callback_query(F.data.startswith("adm:delad:"))
async def del_one(cb: types.CallbackQuery):
    ad_id = int(cb.data.split(":")[2])
    q("DELETE FROM ads WHERE id=%s;", (ad_id,), "count")
    try:
        await cb.message.edit_caption(caption="🗑 E'lon o'chirildi.", reply_markup=None)
    except Exception:
        try:
            await cb.message.edit_text("🗑 E'lon o'chirildi.")
        except Exception:
            pass
    await cb.answer("O'chirildi")
