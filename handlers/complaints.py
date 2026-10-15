import asyncio
import html
import logging

from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from admins import is_admin, is_super, notify_ids
from database import get_connection
from middleware import forget_user
from settings import (
    ADMIN_CONTACT, BAN_DAYS, FINE_AMOUNT, HELPERS_SEE_PRIVATE,
    MAX_REPORTS_PER_DAY, REPORT_THRESHOLD, money,
)

router = Router()

REASONS = {
    "fraud": "Firibgarlik",
    "fake": "Soxta narx yoki rasm",
    "banned": "Taqiqlangan narsa",
    "abuse": "Haqorat yoki uyatsiz",
    "other": "Boshqa",
}


def file_report(ad_id, reporter_id, reason):
    """Shikoyatni bazaga yozadi. Agar sotuvchiga kerakli sondagi turli odam shikoyat qilgan bo'lsa,
    sotuvchini qora ro'yxatga tushiradi va e'lonlarini bloklaydi. Natijani lug'at sifatida qaytaradi."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT a.user_id, a.title, a.description, a.price, a.photo_id, "
            "u.full_name, u.username, u.phone "
            "FROM ads a JOIN users u ON u.user_id = a.user_id WHERE a.id = %s;",
            (ad_id,),
        )
        ad = cur.fetchone()
        if not ad:
            return {"status": "gone"}
        seller_id, title, description, price, photo_id, s_name, s_username, s_phone = ad

        if seller_id == reporter_id:
            return {"status": "own"}

        cur.execute(
            "SELECT COUNT(*) FROM reports WHERE reporter_id = %s AND created_at > NOW() - INTERVAL '24 hours';",
            (reporter_id,),
        )
        if cur.fetchone()[0] >= MAX_REPORTS_PER_DAY:
            return {"status": "limit"}

        cur.execute(
            "INSERT INTO reports (ad_id, seller_id, reporter_id, reason) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (ad_id, reporter_id) DO NOTHING;",
            (ad_id, seller_id, reporter_id, reason),
        )
        if cur.rowcount == 0:
            return {"status": "dup"}

        cur.execute(
            "SELECT COUNT(DISTINCT reporter_id) FROM reports WHERE seller_id = %s AND resolved = FALSE;",
            (seller_id,),
        )
        count = cur.fetchone()[0]

        blacklisted = False
        ban_until = None
        if count >= REPORT_THRESHOLD and not is_admin(seller_id):
            cur.execute("SELECT is_banned FROM users WHERE user_id = %s;", (seller_id,))
            row = cur.fetchone()
            if row and not row[0]:
                cur.execute(
                    "UPDATE users SET is_banned = TRUE, ban_reason = 'reports', "
                    "ban_until = NOW() + make_interval(days => %s) WHERE user_id = %s RETURNING ban_until;",
                    (BAN_DAYS, seller_id),
                )
                ban_until = cur.fetchone()[0]
                cur.execute(
                    "UPDATE ads SET status = 'blocked' WHERE user_id = %s AND status IN ('active', 'pending');",
                    (seller_id,),
                )
                blacklisted = True

        conn.commit()
        return {
            "status": "ok", "ad_id": ad_id, "seller_id": seller_id, "title": title, "price": price,
            "photo_id": photo_id, "s_name": s_name, "s_username": s_username, "s_phone": s_phone,
            "count": count, "blacklisted": blacklisted, "ban_until": ban_until,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def admin_notice(r, viewer_id, reason_name, reporter):
    """Adminga boradigan xabar matni (telefon faqat ruxsati borlarga ko'rinadi)."""
    lines = []
    if r["blacklisted"]:
        lines.append("⚫ <b>SOTUVCHI QORA RO'YXATGA TUSHDI</b>")
        if r["ban_until"]:
            lines.append(f"⏳ {r['ban_until']:%d.%m.%Y} gacha bloklandi, e'lonlari yashirildi.")
        lines.append("")
    lines.append(f"🚩 <b>Yangi shikoyat</b>: {html.escape(reason_name)}")
    lines.append(f"📦 E'lon: <b>{html.escape(r['title'] or '')}</b> ({html.escape(r['price'] or '')})")
    seller = f"👤 Sotuvchi: {html.escape(r['s_name'] or '-')}"
    if r["s_username"]:
        seller += f" (@{html.escape(r['s_username'])})"
    seller += f"\nID: <code>{r['seller_id']}</code>"
    if (is_super(viewer_id) or HELPERS_SEE_PRIVATE) and r["s_phone"]:
        seller += f"\n📞 {html.escape(r['s_phone'])}"
    lines.append(seller)
    lines.append(f"📊 Shikoyat qilgan turli odamlar: <b>{r['count']}</b> ta (chegara: {REPORT_THRESHOLD})")
    lines.append(f"🙋 Shikoyatchi: {html.escape(reporter.full_name)} (ID: <code>{reporter.id}</code>)")
    return "\n".join(lines)


def admin_notice_kb(r):
    b = InlineKeyboardBuilder()
    b.button(text="🗑 E'lonni o'chirish", callback_data=f"adm:rdel:{r['ad_id']}")
    if r["blacklisted"]:
        b.button(text="✅ Blokdan chiqarish", callback_data=f"adm:unban:{r['seller_id']}")
    else:
        b.button(text="🚫 Sotuvchini bloklash", callback_data=f"adm:ban:{r['seller_id']}")
    b.button(text="✅ Shikoyat asossiz", callback_data=f"adm:rok:{r['ad_id']}")
    b.adjust(1)
    return b.as_markup()


def seller_notice(r):
    contact = f"\nAdmin: {ADMIN_CONTACT}" if ADMIN_CONTACT else ""
    return (
        f"🚫 Sizga {r['count']} ta foydalanuvchidan shikoyat tushdi.\n\n"
        f"Qoidalarga ko'ra e'lonlaringiz bloklandi va botdan foydalanish {BAN_DAYS} kunga "
        f"to'xtatildi ({r['ban_until']:%d.%m.%Y} gacha).\n\n"
        f"Muddatdan oldin qaytish uchun {money(FINE_AMOUNT)} so'm jarima to'lab, admin bilan "
        f"bog'lanishingiz mumkin. Shikoyat asossiz deb hisoblasangiz, shu admin orqali murojaat qiling.{contact}"
    )


@router.callback_query(F.data.startswith("rep:"))
async def report_start(cb: types.CallbackQuery):
    ad_id = int(cb.data.split(":")[1])
    b = InlineKeyboardBuilder()
    for code, name in REASONS.items():
        b.button(text=name, callback_data=f"repr:{ad_id}:{code}")
    b.adjust(1)
    await cb.message.answer("🚩 Shikoyat sababini tanlang:", reply_markup=b.as_markup())
    await cb.answer()


@router.callback_query(F.data.startswith("repr:"))
async def report_send(cb: types.CallbackQuery):
    _, ad_id, code = cb.data.split(":")
    if code not in REASONS:
        await cb.answer()
        return

    try:
        r = await asyncio.to_thread(file_report, int(ad_id), cb.from_user.id, code)
    except Exception:
        logging.exception("Shikoyatni saqlashda xatolik")
        await cb.answer("❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.", show_alert=True)
        return

    refusals = {
        "gone": "Bu e'lon endi mavjud emas.",
        "own": "O'z e'loningizga shikoyat qila olmaysiz.",
        "dup": "Siz bu e'londan allaqachon shikoyat qilgansiz.",
        "limit": "Bugun juda ko'p shikoyat yubordingiz. Keyinroq urinib ko'ring.",
    }
    if r["status"] != "ok":
        await cb.answer(refusals[r["status"]], show_alert=True)
        try:
            await cb.message.delete()
        except Exception:
            pass
        return

    try:
        await cb.message.edit_text("✅ Shikoyatingiz qabul qilindi. Rahmat!")
    except Exception:
        pass
    await cb.answer("Qabul qilindi")

    if r["blacklisted"]:
        forget_user(r["seller_id"])
        try:
            await cb.bot.send_message(r["seller_id"], seller_notice(r))
        except Exception:
            pass

    reason_name = REASONS[code]
    for admin_id in notify_ids():
        text = admin_notice(r, admin_id, reason_name, cb.from_user)
        kb = admin_notice_kb(r)
        try:
            if r["photo_id"]:
                await cb.bot.send_photo(admin_id, r["photo_id"], caption=text[:1000],
                                        parse_mode="HTML", reply_markup=kb)
            else:
                await cb.bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            logging.warning("Adminga shikoyat xabari yetmadi: %s", admin_id)
