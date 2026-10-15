import os

# Shikoyat va jarima qoidalari. Raqamlarni shu yerda o'zgartirasiz.

REPORT_THRESHOLD = 3          # nechta TURLI odamdan shikoyat kelsa, sotuvchi qora ro'yxatga tushadi
BAN_DAYS = 30                 # qora ro'yxatdagi sotuvchi necha kun botdan foydalana olmaydi
FINE_AMOUNT = 120000          # muddatdan oldin qaytish uchun jarima (so'm)
MAX_REPORTS_PER_DAY = 10      # bir odam kuniga ko'pi bilan nechta shikoyat yubora oladi

NOTIFY_HELPERS = True         # shikoyat xabarlari yordamchi adminlarga ham borsinmi
HELPERS_SEE_PRIVATE = False   # yordamchi adminlar telefon va joylashuvni ko'ra oladimi

# Jarima to'lash uchun bog'lanish: Render Environment'ga ADMIN_CONTACT qo'shing (masalan @sizning_username)
ADMIN_CONTACT = os.environ.get("ADMIN_CONTACT", "")


def money(n):
    return f"{n:,}".replace(",", " ")
