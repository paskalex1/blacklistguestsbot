from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .countries import load_countries


def start_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить нежелательного гостя", callback_data="add_guest")
    kb.adjust(1)
    return kb.as_markup()


def countries_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for country in load_countries():
        kb.button(text=country, callback_data=f"country:{country}")

    # Добавляем кнопку "Другая страна"
    kb.button(text="Другая страна", callback_data="country:other")

    # ОДНА кнопка в строке
    kb.adjust(1)
    return kb.as_markup()


def photos_keyboard() -> ReplyKeyboardMarkup:
    # Клавиатура внизу экрана с двумя кнопками
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Подтвердить"),
                KeyboardButton(text="Пропустить"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
