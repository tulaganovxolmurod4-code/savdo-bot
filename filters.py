import re

# E'longa ruxsat etilmaydigan narsalarni shu yerda boshqarasiz.
# Yangi so'z qo'shish uchun BANNED ro'yxatlariga kichik harf bilan yozing.

LINK_PATTERNS = [
    re.compile(r"https?://", re.I),
    re.compile(r"www\.", re.I),
    re.compile(r"(t\.me|telegram\.me|telegram\.dog|wa\.me|bit\.ly|tg://)", re.I),
    # @username (email ichidagi @ ni ushlamaydi)
    re.compile(r"(^|[\s(\[,;:])@[a-z0-9_]{3,}", re.I),
    # sayt nomlari: nimadir.com, nimadir.uz va h.k.
    re.compile(
        r"\b[a-z0-9-]{2,}\.(com|uz|ru|net|org|io|me|xyz|info|biz|ly|app|site|online|shop|link)\b",
        re.I,
    ),
]

BANNED = {
    "weapon": [
        "qurol", "yarog'", "to'pponcha", "toponcha", "tabancha", "miltiq", "pistolet",
        "o'q-dori", "oq-dori", "granata", "kalashnikov", "kalashnikof", "ak-47", "ak47",
        "snayper", "karabin", "portlovchi",
        "оружие", "оружия", "пистолет", "ружье", "винтовка", "калашников",
        "боеприпас", "граната", "снайпер", "карабин", "взрывчат",
    ],
    "drugs": [
        "narkotik", "geroin", "kokain", "marixuana", "marihuana", "metamfetamin",
        "amfetamin", "gashish", "xashish", "mefedron",
        "наркотик", "героин", "кокаин", "марихуана", "анаша", "мефедрон", "гашиш",
    ],
    "fake": [
        "soxta pasport", "soxta diplom", "soxta hujjat", "soxta guvohnoma", "soxta pul",
        "fals pul", "sertifikat sotiladi",
        "поддельн", "фальшив",
    ],
    "adult": [
        "intim xizmat", "eskort", "porno",
        "интим услуг", "проститутк", "порно",
    ],
}

# So'kinish va uyatsiz so'zlar. Qisqa so'zlar alohida so'z sifatida tekshiriladi,
# shuning uchun oddiy so'zlar ichidagi o'xshash harflar xato ushlanmaydi.
# Yangi so'z qo'shmoqchi bo'lsangiz, shu ro'yxatlarga yozing.
PROFANITY_PATTERNS = [
    re.compile(
        r"\b(siktir|sikaman|sikdim|sikay|qo'tag'?(im|i)?|qotaq|jalab|dalbayob|haromi|pidor|pidar|mudak|gandon|suka)\b",
        re.I,
    ),
    re.compile(r"(хуй|хуе|хуя|пизд|бляд|блять|ебат|ебан|ебал|ебну|мудак|гандон|пидор|пидар|залуп)", re.I),
    re.compile(r"\bсук[аиу]\b", re.I),
]

REJECT_TEXT = {
    "link": (
        "❌ E'londa havola yoki @username yozish mumkin emas.\n"
        "Mijozlar siz bilan ro'yxatdan o'tganda kiritilgan raqam orqali bog'lanadi."
    ),
    "weapon": "❌ Qurol-yarog' va shunga o'xshash mahsulotlarni e'lon qilish taqiqlangan.\nBoshqa matn kiriting.",
    "drugs": "❌ Giyohvand va taqiqlangan moddalarni e'lon qilish taqiqlangan.\nBoshqa matn kiriting.",
    "fake": "❌ Soxta hujjat, pul va shunga o'xshash narsalarni e'lon qilish taqiqlangan.\nBoshqa matn kiriting.",
    "adult": "❌ Bunday mazmundagi e'lonlar taqiqlangan.\nBoshqa matn kiriting.",
    "profanity": "❌ E'londa so'kinish va uyatsiz so'zlar ishlatish mumkin emas.\nMatnni o'zgartirib yozing.",
    "ai": (
        "❌ E'lon matni qoidalarga mos kelmaydi (taqiqlangan yoki haqoratli mazmun).\n"
        "Matnni o'zgartirib qayta yozing."
    ),
}


def _normalize(text):
    text = text.lower()
    for ch in ("‘", "’", "ʻ", "ʼ", "`", "´"):
        text = text.replace(ch, "'")
    return text.replace("ё", "е")


def _squash(text):
    """Bo'sh joy va belgilarni olib tashlaydi: 'q u r o l' -> 'qurol'."""
    return re.sub(r"[^a-z0-9а-я]", "", text)


# Uzun so'zlar uchun harflar orasiga belgi qo'yib aldash urinishini ham tutadi
_SQUASHED = {
    kind: [w for w in (_squash(_normalize(x)) for x in words) if len(w) >= 6]
    for kind, words in BANNED.items()
}


def check_text(text):
    """'link', taqiqlangan tur ('weapon', 'drugs', ...) yoki None qaytaradi."""
    norm = _normalize(text or "")

    for pattern in LINK_PATTERNS:
        if pattern.search(norm):
            return "link"

    for pattern in PROFANITY_PATTERNS:
        if pattern.search(norm):
            return "profanity"

    for kind, words in BANNED.items():
        for word in words:
            if word in norm:
                return kind

    squashed = _squash(norm)
    for kind, words in _SQUASHED.items():
        for word in words:
            if word in squashed:
                return kind

    return None
