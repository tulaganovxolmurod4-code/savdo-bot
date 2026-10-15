import html
from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject, BaseFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from admins import add_helper, helper_ids, is_admin, is_super, remove_helper
from database import get_connection
from keyboards import main_menu
from middleware import forget_user
from settings import HELPERS_SEE_PRIVATE


class IsAdmin(BaseFilter):
    """Faqat bosh admin va yordamchi adminlar o'tadi."""

    async def __call__(self, event) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user) and is_admin(user.id)


router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PAGE = 8
LOC_PAGE = 10


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


def can_private(viewer_id):
    """Telefon va joylashuvni ko'rish huquqi."""
    return is_super(viewer_id) or HELPERS_SEE_PRIVATE


def nav_row(prefix, page, more):
    row = []
    if page > 0:
        row.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:{page - 1}"))
    row.append(types.InlineKeyboardButton(text="🏠", callback_data="adm:home"))
    if more:
        row.append(types.InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:{page + 1}"))
    return row


async def show(cb, text, kb):
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)


async def replace_notice(cb, text):
    """Shikoyat xabarini (rasmli yoki rasmsiz) yangi matn bilan almashtiradi."""
    try:
        await cb.message.edit_caption(caption=text, reply_markup=None)
    except Exception:
        try:
            await cb.message.edit_text(text, reply_markup=None)
        except Exception:
            pass


# ---------------- Bosh sahifa ----------------

def stats_text():
    u = q("SELECT COUNT(*), COUNT(*) FILTER (WHERE is_registered), COUNT(*) FILTER (WHERE is_banned) FROM users;", mode="one")
    a = q("SELECT COUNT(*), COUNT(*) FILTER (WHERE status='active'), COUNT(*) FILTER (WHERE status='sold') FROM ads;", mode="one")
    r = q("SELECT COUNT(DISTINCT seller_id) FROM reports WHERE resolved = FALSE;", mode="one")
    return (
        "<b>🛠 Admin panel</b>\n\n"
        f"👥 Ro'yxatdan o'tganlar: <b>{u[1]}</b> (bloklangan: {u[2]})\n"
        f"📋 Jami e'lonlar: <b>{a[0]}</b>\n"
        f"✅ Faol: <b>{a[1]}</b>\n"
        f"💰 Sotilgan: <b>{a[2]}</b>\n"
        f"🚩 Shikoyat tushgan sotuvchilar: <b>{r[0]}</b>"
    )


def panel_kb(viewer_id):
    b = InlineKeyboardBuilder()
    b.button(text="👥 Foydalanuvchilar", callback_data="adm:users:0")
    b.button(text="⚫ Qora ro'yxat", callback_data="adm:black:0")
    b.button(text="🚩 Shikoyatlar", callback_data="adm:reps:0")
    b.button(text="🔎 Qidirish", callback_data="adm:find")
    if is_super(viewer_id):
        b.button(text="📍 Joylashuvlar", callback_data="adm:locs:0")
        b.button(text="👮 Adminlar", callback_data="adm:admins")
    b.button(text="🔄 Yangilash", callback_data="adm:home")
    b.adjust(2)
    return b.as_markup()


@router.message(F.text == "🛠 Admin panel")
@router.message(Command("admin"))
async def panel(message: types.Message):
    await message.answer(stats_text(), parse_mode="HTML", reply_markup=panel_kb(message.from_user.id))


@router.callback_query(F.data == "adm:home")
async def home(cb: types.CallbackQuery):
    try:
        await cb.message.edit_text(stats_text(), parse_mode="HTML", reply_markup=panel_kb(cb.from_user.id))
    except Exception:
        pass
    await cb.answer()


# ---------------- Ro'yxatlar ----------------

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
    b.row(*nav_row("adm:users", page, more))
    text = f"<b>👥 Foydalanuvchilar</b> (sahifa {page + 1})\n\nIsm yoki ID bo'yicha topish: /find" if rows \
        else "Hali ro'yxatdan o'tgan foydalanuvchi yo'q."
    await show(cb, text, b.as_markup())
    await cb.answer()


@router.callback_query(F.data.startswith("adm:black:"))
async def black_list(cb: types.CallbackQuery):
    page = int(cb.data.split(":")[2])
    rows = q(
        "SELECT user_id, full_name, ban_reason, ban_until FROM users WHERE is_banned "
        "ORDER BY user_id DESC LIMIT %s OFFSET %s;",
        (PAGE + 1, page * PAGE),
    )
    more = len(rows) > PAGE
    rows = rows[:PAGE]
    b = InlineKeyboardBuilder()
    for uid, name, reason, until in rows:
        tag = "shikoyat" if reason == "reports" else "admin"
        until_txt = f" • {until:%d.%m}" if until else ""
        b.button(text=f"🚫 {name} • {tag}{until_txt}", callback_data=f"adm:user:{uid}")
    b.adjust(1)
    b.row(*nav_row("adm:black", page, more))
    text = f"<b>⚫ Qora ro'yxat</b> (sahifa {page + 1})\n\nBirini bosib, blokdan chiqarishingiz mumkin." if rows \
        else "Qora ro'yxat bo'sh."
    await show(cb, text, b.as_markup())
    await cb.answer()


@router.callback_query(F.data.startswith("adm:reps:"))
async def reports_list(cb: types.CallbackQuery):
    page = int(cb.data.split(":")[2])
    rows = q(
        """SELECT r.seller_id, u.full_name, COUNT(DISTINCT r.reporter_id) AS c
           FROM reports r JOIN users u ON u.user_id = r.seller_id
           WHERE r.resolved = FALSE
           GROUP BY r.seller_id, u.full_name ORDER BY c DESC LIMIT %s OFFSET %s;""",
        (PAGE + 1, page * PAGE),
    )
    more = len(rows) > PAGE
    rows = rows[:PAGE]
    b = InlineKeyboardBuilder()
    for uid, name, count in rows:
        b.button(text=f"🚩 {name} • {count} ta shikoyat", callback_data=f"adm:user:{uid}")
    b.adjust(1)
    b.row(*nav_row("adm:reps", page, more))
    text = f"<b>🚩 Shikoyat tushgan sotuvchilar</b> (sahifa {page + 1})" if rows \
        else "Ko'rib chiqilmagan shikoyat yo'q."
    await show(cb, text, b.as_markup())
    await cb.answer()


@router.callback_query(F.data.startswith("adm:locs:"))
async def locations_list(cb: types.CallbackQuery):
    if not is_super(cb.from_user.id):
        await cb.answer("Bu bo'lim faqat bosh admin uchun", show_alert=True)
        return
    page = int(cb.data.split(":")[2])
    rows = q(
        """SELECT user_id, full_name, username, phone, latitude, longitude, created_at
           FROM users WHERE is_registered
           ORDER BY created_at DESC LIMIT %s OFFSET %s;""",
        (LOC_PAGE + 1, page * LOC_PAGE),
    )
    more = len(rows) > LOC_PAGE
    rows = rows[:LOC_PAGE]

    if not rows:
        text = "Hali ro'yxatdan o'tgan foydalanuvchi yo'q."
    else:
        lines = [f"<b>📍 Joylashuvlar</b> (sahifa {page + 1})\n"]
        for uid, name, username, phone, lat, lon, created in rows:
            uname = f"@{html.escape(username)}" if username else "—"
            if lat is not None and lon is not None:
                loc = f'<a href="https://www.google.com/maps?q={lat},{lon}">🗺 Xaritada ochish</a>'
            else:
                loc = "joylashuv yo'q"
            lines.append(
                f"👤 <b>{html.escape(name or '-')}</b> ({uname})\n"
                f"📞 {html.escape(phone or '—')}\n"
                f"📍 {loc}\n"
                f"🕒 {created:%Y-%m-%d %H:%M}\n"
            )
        text = "\n".join(lines)

    b = InlineKeyboardBuilder()
    b.row(*nav_row("adm:locs", page, more))
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=b.as_markup(), disable_web_page_preview=True)
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=b.as_markup(), disable_web_page_preview=True)
    await cb.answer()


# ---------------- Qidirish ----------------

FIND_HELP = (
    "🔎 <b>Foydalanuvchini topish</b>\n\n"
    "Yozing:\n"
    "<code>/find Ali</code> (ism)\n"
    "<code>/find @username</code>\n"
    "<code>/find 123456789</code> (Telegram ID)"
)


@router.callback_query(F.data == "adm:find")
async def find_help(cb: types.CallbackQuery):
    await cb.message.answer(FIND_HELP, parse_mode="HTML")
    await cb.answer()


@router.message(Command("find"))
async def find_cmd(message: types.Message, command: CommandObject):
    text = (command.args or "").strip().lstrip("@")
    if len(text) < 2:
        await message.answer(FIND_HELP, parse_mode="HTML")
        return
    safe = text.replace("%", "").replace("_", "")
    pattern = f"%{safe}%"
    conds = "full_name ILIKE %s OR username ILIKE %s OR user_id::text = %s"
    params = [pattern, pattern, safe]
    if can_private(message.from_user.id):
        conds += " OR phone ILIKE %s"
        params.append(pattern)
    rows = q(
        f"SELECT user_id, full_name, username, is_banned FROM users "
        f"WHERE is_registered AND ({conds}) ORDER BY created_at DESC LIMIT 8;",
        tuple(params),
    )
    if not rows:
        await message.answer("Hech kim topilmadi.")
        return
    b = InlineKeyboardBuilder()
    for uid, name, username, banned in rows:
        uname = f" (@{username})" if username else ""
        b.button(text=f"{'🚫 ' if banned else ''}{name}{uname}", callback_data=f"adm:user:{uid}")
    b.adjust(1)
    await message.answer("Topilganlar:", reply_markup=b.as_markup())


# ---------------- Foydalanuvchi kartasi ----------------

def user_kb(uid, banned, viewer_id):
    b = InlineKeyboardBuilder()
    # Bitta tugma: holatga qarab "Bloklash" yoki "Blokdan chiqarish"
    if banned:
        b.button(text="✅ Blokdan chiqarish", callback_data=f"adm:unban:{uid}")
    else:
        b.button(text="🚫 Bloklash", callback_data=f"adm:ban:{uid}")
    b.button(text="📋 E'lonlari", callback_data=f"adm:ads:{uid}")
    b.button(text="🗑 Barcha e'lonlarini o'chirish", callback_data=f"adm:delads:{uid}")
    if is_super(viewer_id) and uid != viewer_id:
        if uid in helper_ids():
            b.button(text="👮 Adminlikdan olish", callback_data=f"adm:rmadm:{uid}")
        else:
            b.button(text="👮 Admin qilish", callback_data=f"adm:mkadm:{uid}")
    b.button(text="⬅️ Ro'yxat", callback_data="adm:users:0")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data.startswith("adm:user:"))
async def user_card(cb: types.CallbackQuery):
    uid = int(cb.data.split(":")[2])
    viewer = cb.from_user.id
    u = q(
        "SELECT full_name, username, phone, latitude, longitude, is_banned, created_at, ban_reason, ban_until "
        "FROM users WHERE user_id=%s;",
        (uid,), "one",
    )
    if not u:
        await cb.answer("Topilmadi", show_alert=True)
        return
    name, username, phone, lat, lon, banned, created, ban_reason, ban_until = u
    s = q(
        "SELECT COUNT(*), COUNT(*) FILTER (WHERE status='active'), COUNT(*) FILTER (WHERE status='sold') "
        "FROM ads WHERE user_id=%s;",
        (uid,), "one",
    )
    rep = q("SELECT COUNT(DISTINCT reporter_id) FROM reports WHERE seller_id=%s AND resolved=FALSE;", (uid,), "one")

    if is_super(uid):
        role = "👑 Bosh admin"
    elif uid in helper_ids():
        role = "👮 Yordamchi admin"
    else:
        role = None

    lines = [
        f"👤 <b>{html.escape(name or '-')}</b>" + (f"  {role}" if role else ""),
        f"🆔 <code>{uid}</code>",
        f"🔗 {('@' + html.escape(username)) if username else '—'}",
    ]
    if can_private(viewer):
        lines.append(f"📞 {html.escape(phone or '—')}")
    lines.append(f"📅 {created:%Y-%m-%d %H:%M}")
    lines.append("")
    lines.append(f"📋 E'lonlar: {s[0]} (faol {s[1]}, sotilgan {s[2]})")
    lines.append(f"🚩 Ko'rib chiqilmagan shikoyat: {rep[0]} ta odamdan")
    if banned:
        why = "shikoyatlar sababli" if ban_reason == "reports" else "admin tomonidan"
        until_txt = f", {ban_until:%d.%m.%Y} gacha" if ban_until else ""
        lines.append(f"Holati: 🚫 Bloklangan ({why}{until_txt})")
    else:
        lines.append("Holati: ✅ Faol")

    await cb.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=user_kb(uid, banned, viewer))
    if can_private(viewer) and lat is not None and lon is not None:
        await cb.message.answer_location(lat, lon)
    await cb.answer()


# ---------------- Bloklash va blokdan chiqarish ----------------

@router.callback_query(F.data.startswith("adm:ban:"))
async def ban(cb: types.CallbackQuery):
    uid = int(cb.data.split(":")[2])
    if is_admin(uid):
        await cb.answer("Adminni bloklab bo'lmaydi", show_alert=True)
        return
    q("UPDATE users SET is_banned=TRUE, ban_reason='admin', ban_until=NULL WHERE user_id=%s;", (uid,), "count")
    q("UPDATE ads SET status='blocked' WHERE user_id=%s AND status='active';", (uid,), "count")
    forget_user(uid)
    try:
        await cb.message.edit_reply_markup(reply_markup=user_kb(uid, True, cb.from_user.id))
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
    q("UPDATE users SET is_banned=FALSE, ban_until=NULL, ban_reason=NULL WHERE user_id=%s;", (uid,), "count")
    q("UPDATE ads SET status='active' WHERE user_id=%s AND status='blocked';", (uid,), "count")
    q("UPDATE reports SET resolved=TRUE WHERE seller_id=%s AND resolved=FALSE;", (uid,), "count")
    forget_user(uid)
    try:
        await cb.message.edit_reply_markup(reply_markup=user_kb(uid, False, cb.from_user.id))
    except Exception:
        pass
    try:
        await cb.bot.send_message(uid, "✅ Siz blokdan chiqarildingiz. Botdan yana foydalanishingiz mumkin.")
    except Exception:
        pass
    await cb.answer("✅ Blokdan chiqarildi", show_alert=True)


# ---------------- Shikoyat xabaridagi tugmalar ----------------

@router.callback_query(F.data.startswith("adm:rdel:"))
async def report_delete_ad(cb: types.CallbackQuery):
    ad_id = int(cb.data.split(":")[2])
    q("DELETE FROM ads WHERE id=%s;", (ad_id,), "count")
    await replace_notice(cb, "🗑 E'lon o'chirildi.")
    await cb.answer("O'chirildi")


@router.callback_query(F.data.startswith("adm:rok:"))
async def report_dismiss(cb: types.CallbackQuery):
    ad_id = int(cb.data.split(":")[2])
    q("UPDATE reports SET resolved=TRUE WHERE ad_id=%s;", (ad_id,), "count")
    await replace_notice(cb, "✅ Shikoyat asossiz deb belgilandi.")
    await cb.answer("Yopildi")


# ---------------- E'lonlarni boshqarish ----------------

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
    await replace_notice(cb, "🗑 E'lon o'chirildi.")
    await cb.answer("O'chirildi")


# ---------------- Yordamchi adminlar (faqat bosh admin) ----------------

async def render_admins(cb):
    ids = helper_ids()
    names = {}
    if ids:
        for uid, name in q("SELECT user_id, full_name FROM users WHERE user_id = ANY(%s);", (ids,)):
            names[uid] = name
    b = InlineKeyboardBuilder()
    for uid in ids:
        b.button(text=f"❌ {names.get(uid, uid)} ni olib tashlash", callback_data=f"adm:rmadm:{uid}")
    b.button(text="🏠", callback_data="adm:home")
    b.adjust(1)
    if ids:
        lines = "\n".join(f"• {html.escape(str(names.get(uid, uid)))} (ID: <code>{uid}</code>)" for uid in ids)
    else:
        lines = "Hozircha yordamchi admin yo'q."
    text = (
        "<b>👮 Yordamchi adminlar</b>\n\n" + lines + "\n\n"
        "Yangi admin tayinlash: <b>/find</b> bilan odamni toping yoki «👥 Foydalanuvchilar» dan tanlang, "
        "kartasidagi «👮 Admin qilish» tugmasini bosing."
    )
    await show(cb, text, b.as_markup())


@router.callback_query(F.data == "adm:admins")
async def admins_screen(cb: types.CallbackQuery):
    if not is_super(cb.from_user.id):
        await cb.answer("Bu bo'lim faqat bosh admin uchun", show_alert=True)
        return
    await render_admins(cb)
    await cb.answer()


@router.callback_query(F.data.startswith("adm:mkadm:"))
async def make_admin(cb: types.CallbackQuery):
    if not is_super(cb.from_user.id):
        await cb.answer("Faqat bosh admin admin tayinlay oladi", show_alert=True)
        return
    uid = int(cb.data.split(":")[2])
    if uid == cb.from_user.id:
        await cb.answer("Siz allaqachon bosh adminsiz", show_alert=True)
        return
    exists = q("SELECT 1 FROM users WHERE user_id=%s AND is_registered;", (uid,), "one")
    if not exists:
        await cb.answer("Bu odam botdan ro'yxatdan o'tmagan", show_alert=True)
        return
    add_helper(uid, cb.from_user.id)
    forget_user(uid)
    try:
        await cb.bot.send_message(
            uid,
            "👮 Siz yordamchi admin etib tayinlandingiz.\nMenyuda «🛠 Admin panel» tugmasi paydo bo'ldi.",
            reply_markup=main_menu(uid),
        )
    except Exception:
        pass
    try:
        await cb.message.edit_reply_markup(reply_markup=user_kb(uid, False, cb.from_user.id))
    except Exception:
        pass
    await cb.answer("👮 Admin tayinlandi", show_alert=True)


@router.callback_query(F.data.startswith("adm:rmadm:"))
async def remove_admin(cb: types.CallbackQuery):
    if not is_super(cb.from_user.id):
        await cb.answer("Faqat bosh admin adminlikdan ola oladi", show_alert=True)
        return
    uid = int(cb.data.split(":")[2])
    remove_helper(uid)
    forget_user(uid)
    try:
        await cb.bot.send_message(uid, "Siz endi yordamchi admin emassiz.", reply_markup=main_menu(uid))
    except Exception:
        pass
    if cb.message.text and "Yordamchi adminlar" in cb.message.text:
        await render_admins(cb)
    else:
        try:
            await cb.message.edit_reply_markup(reply_markup=user_kb(uid, False, cb.from_user.id))
        except Exception:
            pass
    await cb.answer("Adminlikdan olindi", show_alert=True)
