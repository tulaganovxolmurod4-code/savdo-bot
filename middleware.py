import asyncio
import time
from aiogram import BaseMiddleware, types
from admins import is_admin
from database import get_user
from settings import ADMIN_CONTACT, FINE_AMOUNT, money

# Ro'yxatdan o'tgan foydalanuvchi holati shuncha soniya xotirada eslab qolinadi.
CACHE_TTL = 30
CACHE_MAX = 20000

_cache = {}     # user_id -> (vaqt, row)
_sem = None     # bazaga bir vaqtdagi so'rovlar sonini cheklaydi
_inflight = {}  # user_id -> hozir bajarilayotgan bazaga murojaat


def forget_user(user_id):
    """Foydalanuvchi holati o'zgarganda (bloklash, blokdan chiqarish) xotiradagi yozuvni o'chiradi."""
    _cache.pop(user_id, None)


def _get_sem():
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(4)
    return _sem


async def _fetch(user_id):
    async with _get_sem():
        row = await asyncio.to_thread(get_user, user_id)
    # Faqat ro'yxatdan o'tgan yoki bloklanganlar eslab qolinadi:
    # yangi ro'yxatdan o'tayotganlar darrov ishlay boshlashi uchun.
    if row and (row["is_registered"] or row["is_banned"]):
        if len(_cache) > CACHE_MAX:
            _cache.clear()
        _cache[user_id] = (time.monotonic(), row)
    return row


async def load_user(user_id):
    """Foydalanuvchini avval xotiradan, topilmasa bazadan oladi (bot qotib qolmaydi)."""
    hit = _cache.get(user_id)
    if hit and time.monotonic() - hit[0] < CACHE_TTL:
        return hit[1]

    task = _inflight.get(user_id)
    if task is None:
        task = asyncio.ensure_future(_fetch(user_id))
        _inflight[user_id] = task
        task.add_done_callback(lambda _t: _inflight.pop(user_id, None))
    return await task


def ban_text(row):
    if row.get("ban_reason") == "reports":
        until = row.get("ban_until")
        until_text = f" ({until:%d.%m.%Y} gacha)" if until else ""
        contact = f"\nAdmin: {ADMIN_CONTACT}" if ADMIN_CONTACT else ""
        return (
            f"🚫 Sizga ko'p shikoyat tushgani sababli botdan foydalanish to'xtatildi{until_text}.\n\n"
            f"Muddatdan oldin qaytish uchun {money(FINE_AMOUNT)} so'm jarima to'lab, "
            f"admin bilan bog'lanishingiz mumkin.{contact}"
        )
    return "🚫 Siz bloklangansiz."


class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if user is None or is_admin(user.id):
            return await handler(event, data)
        try:
            row = await load_user(user.id)
        except Exception:
            return await handler(event, data)

        if row and row["ban_active"]:
            await self._deny(event, ban_text(row))
            return

        if not (row and row["is_registered"]):
            state = data.get("state")
            raw = (await state.get_state()) if state else data.get("raw_state")
            text = getattr(event, "text", None) or ""
            if (raw or "").startswith("Reg:") or text.startswith("/start"):
                return await handler(event, data)
            await self._deny(event, "Avval /start bosib ro'yxatdan o'ting.")
            return

        return await handler(event, data)

    async def _deny(self, event, text):
        if isinstance(event, types.CallbackQuery):
            await event.answer(text[:190], show_alert=True)
        else:
            await event.answer(text)
