from aiogram.fsm.state import State, StatesGroup


class AddAdState(StatesGroup):
    category = State()      # Kategoriyani tanlash
    title = State()         # Sarlavha
    description = State()   # Tavsif
    price = State()         # Narx
    address = State()       # Do'kon manzili (matn)
    loc_choice = State()    # Eski joylashuvda qolish yoki qayta kiritish
    loc_new = State()       # Yangi joylashuv yuborish
    photo = State()         # Rasm
    phone = State()         # Telefon raqam (ishlatilmaydi, moslik uchun)
    confirm = State()       # Tasdiqlash
