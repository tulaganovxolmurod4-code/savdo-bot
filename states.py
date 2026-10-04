from aiogram.fsm.state import State, StatesGroup

class AddAdState(StatesGroup):
    category = State()      # Kategoriyani tanlash
    title = State()         # Sarlavha
    description = State()   # Tavsif
    price = State()         # Narx
    photo = State()         # Rasm
    phone = State()         # Telefon raqam
    confirm = State()       # Tasdiqlash
