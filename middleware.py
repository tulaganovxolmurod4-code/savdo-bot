from aiogram import BaseMiddleware, types
from database import get_user
from keyboards import ADMIN_ID

class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if user is None or user.id == ADMIN_ID:
            return await handler(event, data)
        try:
            row = get_user(user.id)
        except Exception:
            return await handler(event, data)

        if row and row["is_banned"]:
            await self._deny(event, "🚫 Siz bloklangansiz.")
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
            await event.answer(text, show_alert=True)
        else:
            await event.answer(text)
