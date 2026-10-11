import logging
import os

import aiohttp

# Ixtiyoriy ikkinchi himoya qatlami: OpenAI'ning bepul moderatsiya xizmati.
# Render'dagi Environment'ga OPENAI_API_KEY qo'shilsa, yoqiladi.
# Kalit bo'lmasa yoki xizmat javob bermasa, e'lon faqat oddiy filtrdan o'tadi (bot to'xtamaydi).
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
URL = "https://api.openai.com/v1/moderations"


async def ai_flagged(text):
    """True: sun'iy intellekt matnni taqiqlangan yoki haqoratli deb topdi."""
    if not OPENAI_API_KEY or not text:
        return False
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                URL,
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={"model": "omni-moderation-latest", "input": text},
            ) as resp:
                if resp.status != 200:
                    logging.warning("Moderatsiya xizmati javobi: %s", resp.status)
                    return False
                data = await resp.json()
        return bool(data["results"][0].get("flagged"))
    except Exception as e:
        logging.warning("Moderatsiya xizmatiga ulanib bo'lmadi: %s", e)
        return False
