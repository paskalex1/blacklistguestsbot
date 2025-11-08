from aiogram.fsm.state import StatesGroup, State


class ReportGuest(StatesGroup):
    country = State()
    custom_country = State()  # <-- пользователь вводит страну вручную
    city = State()
    guest_name = State()
    phone = State()
    description = State()
    photos = State()
