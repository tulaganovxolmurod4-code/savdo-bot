import os

# Shikoyat va jarima qoidalari. Raqamlarni shu yerda o'zgartirasiz.

REPORT_THRESHOLD = 3          # nechta TURLI odamdan shikoyat kelsa, sotuvchi qora ro'yxatga tushadi
BAN_DAYS = 30                 # qora ro'yxatdagi sotuvchi necha kun botdan foydalana olmaydi
FINE_AMOUNT = 120000          # muddatdan oldin qaytish uchun jarima (so'm)
MAX_REPORTS_PER_DAY = 10      # bir odam kuniga ko'pi bilan nechta shikoyat yubora oladi

NOTIFY_HELPERS = True         # shikoyat xabarlari yordamchi adminlarga ham borsinmi
HELPERS_SEE_PRIVATE = False   # yordamchi adminlar telefon va joylashuvni ko'ra oladimi

# TOP e'lon narxlari: kun -> so'm
TOP_PACKAGES = {5: 15000, 10: 23000}

# TOP uchun to'lov qabul qilinadigan karta. Render Environment'ga TOP_CARD_INFO nomi bilan qo'ying
# (masalan: 8600 1234 5678 9012, Ism Familiya). Kodga yozmang.
TOP_CARD_INFO = os.environ.get("TOP_CARD_INFO", "")

# Rasm bo'limga mos kelmasa, necha urinishdan keyin e'lon admin tekshiruviga yuboriladi
IMAGE_MAX_ATTEMPTS = 3

# Jarima to'lash uchun bog'lanish: Render Environment'ga ADMIN_CONTACT qo'shing (masalan @sizning_username)
ADMIN_CONTACT = os.environ.get("ADMIN_CONTACT", "")


def money(n):
    return f"{n:,}".replace(",", " ")
