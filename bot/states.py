from aiogram.fsm.state import StatesGroup, State


class ReportGuest(StatesGroup):
    country = State()
    city = State()
    guest_name = State()
    phone = State()
    description = State()
    photos = State()
