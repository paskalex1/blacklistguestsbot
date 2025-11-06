from html import escape
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InputMediaPhoto,
    ReplyKeyboardRemove,
)
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatMemberStatus
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .config import CHANNEL_USERNAME, ADMIN_IDS
from .states import ReportGuest
from .keyboards import start_keyboard, countries_keyboard, photos_keyboard
from .countries import load_countries, save_countries

router = Router()
MAX_PHOTOS = 10

# Память для заявок на модерацию: id -> словарь с данными
pending_reports: dict[str, dict] = {}


async def check_subscription(bot: Bot, user_id: int) -> bool:
    member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
    return member.status in {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    }


def build_post_text(
    country: str,
    city: str,
    guest_name: str,
    phone: str,
    description: str,
) -> str:
    """Форматируем текст поста для канала/модерации (HTML)."""
    country_html = escape(country)
    city_html = escape(city)
    guest_name_html = escape(guest_name)
    phone_html = escape(phone)
    description_html = escape(description)

    title = "⚠️ <b>Нежелательный гость</b>"
    meta = (
        f"<b>Страна:</b> {country_html}\n"
        f"<b>Город:</b> {city_html}\n"
        f"<b>ФИО гостя:</b> {guest_name_html}\n"
        f"<b>Телефон:</b> {phone_html}"
    )
    body = f"<b>Описание ситуации:</b>\n{description_html}"

    return f"{title}\n\n{meta}\n\n{body}"


def moderation_keyboard(report_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Опубликовать", callback_data=f"mod_approve:{report_id}")
    kb.button(text="🚫 Отклонить", callback_data=f"mod_reject:{report_id}")
    kb.adjust(2)
    return kb.as_markup()


async def queue_report_for_moderation(
    message: Message,
    state: FSMContext,
    bot: Bot,
    with_photos: bool,
):
    """Сохраняем заявку и отправляем её на модерацию админам."""

    data = await state.get_data()
    country = data["country"]
    city = data["city"]
    guest_name = data["guest_name"]
    phone = data["phone"]
    description = data["description"]
    photo_ids: list[str] = data.get("photo_ids", [])

    post_text = build_post_text(
        country=country,
        city=city,
        guest_name=guest_name,
        phone=phone,
        description=description,
    )

    # id заявки: userId_timestamp
    report_id = f"{message.from_user.id}_{int(datetime.now().timestamp())}"

    report = {
        "id": report_id,
        "user_id": message.from_user.id,
        "user_username": message.from_user.username,
        "user_first_name": message.from_user.first_name,
        "country": country,
        "city": city,
        "guest_name": guest_name,
        "phone": phone,
        "description": description,
        "photo_ids": photo_ids if with_photos else [],
        "created_at": datetime.now().isoformat(),
    }

    pending_reports[report_id] = report

    # Уведомляем пользователя
    await message.answer(
        "Ваш кейс отправлен на модерацию. "
        "После проверки он будет опубликован в канале или отклонён модератором.",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Сбрасываем состояния и возвращаем на старт
    await state.clear()
    await message.answer(
        f"Чтобы добавить нежелательного гостя, вы должны быть подписаны на канал {CHANNEL_USERNAME}",
        reply_markup=start_keyboard(),
    )

    # Отправляем заявку всем админам
    admins = ADMIN_IDS or []
    sender_username = (
        f"@{message.from_user.username}" if message.from_user.username else "без никнейма"
    )

    for admin_id in admins:
        try:
            # 1) если есть фото — сначала медиа-группа с полным текстом
            if report["photo_ids"]:
                media = []
                for i, pid in enumerate(report["photo_ids"]):
                    if i == 0:
                        # первая фотка с подписью (весь текст поста)
                        media.append(InputMediaPhoto(media=pid, caption=post_text))
                    else:
                        media.append(InputMediaPhoto(media=pid))
                await bot.send_media_group(chat_id=admin_id, media=media)

                control_text = (
                    f"Новая заявка <b>#{report_id}</b> на публикацию в {CHANNEL_USERNAME}\n\n"
                    f"Отправитель: {sender_username} (ID: <code>{message.from_user.id}</code>)\n\n"
                    f"Фото: {len(report['photo_ids'])} шт.\n"
                )
            else:
                # 2) если фото нет — всё в одном тексте
                control_text = (
                    f"Новая заявка <b>#{report_id}</b> на публикацию в {CHANNEL_USERNAME}\n\n"
                    f"Отправитель: {sender_username} (ID: <code>{message.from_user.id}</code>)\n\n"
                    f"{post_text}"
                )

            # Сообщение с кнопками модерации (всегда отдельное)
            await bot.send_message(
                admin_id,
                text=control_text,
                reply_markup=moderation_keyboard(report_id),
            )
        except Exception:
            # если какому-то админу нельзя написать, просто пропускаем
            continue


async def publish_report_to_channel(report: dict, bot: Bot):
    """Публикуем уже одобренный пост в канал."""

    post_text = build_post_text(
        country=report["country"],
        city=report["city"],
        guest_name=report["guest_name"],
        phone=report["phone"],
        description=report["description"],
    )
    photo_ids: list[str] = report.get("photo_ids") or []

    if photo_ids:
        media = []
        for i, pid in enumerate(photo_ids):
            if i == 0:
                media.append(InputMediaPhoto(media=pid, caption=post_text))
            else:
                media.append(InputMediaPhoto(media=pid))
        await bot.send_media_group(chat_id=CHANNEL_USERNAME, media=media)
    else:
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=post_text)


# =========================
# ОСНОВНОЙ СЦЕНАРИЙ ПОЛЬЗОВАТЕЛЯ
# =========================


# /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "Чтобы добавить нежелательного гостя, вы должны быть подписаны "
        f"на канал {CHANNEL_USERNAME}"
    )
    await message.answer(text, reply_markup=start_keyboard())


# Нажатие кнопки «Добавить нежелательного гостя»
@router.callback_query(F.data == "add_guest")
async def cb_add_guest(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id

    if not await check_subscription(bot, user_id):
        await callback.message.answer(
            f"Доступ ограничен из-за отсутствия подписки на канал {CHANNEL_USERNAME}"
        )
        await callback.answer()
        return

    await callback.message.answer(
        'Отлично! Вы успешно подписались на канал "Нежелательные гости"👍'
    )
    await callback.message.answer(
        "Из какой вы страны?", reply_markup=countries_keyboard()
    )
    await state.set_state(ReportGuest.country)
    await callback.answer()


# Выбор страны
@router.callback_query(
    ReportGuest.country,
    F.data.startswith("country:"),
)
async def cb_country(callback: CallbackQuery, state: FSMContext):
    country = callback.data.split(":", 1)[1]
    await state.update_data(country=country)
    await callback.message.answer("Отлично!")
    await callback.message.answer("Теперь напишите ваш город.")
    await state.set_state(ReportGuest.city)
    await callback.answer()


# Город
@router.message(ReportGuest.city)
async def get_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await message.answer("Хорошо!")
    await message.answer("Напишите ФИО нежелательного гостя.")
    await state.set_state(ReportGuest.guest_name)


# ФИО
@router.message(ReportGuest.guest_name)
async def get_guest_name(message: Message, state: FSMContext):
    await state.update_data(guest_name=message.text.strip())
    await message.answer("Записал!")
    await message.answer(
        "Напишите номер телефона нежелательного гостя без плюса, пробелов, "
        "дефисов и скобок. Пример: 79781234567"
    )
    await state.set_state(ReportGuest.phone)


def valid_phone(phone: str) -> bool:
    return phone.isdigit() and len(phone) == 11 and phone.startswith("7")


# Телефон
@router.message(ReportGuest.phone)
async def get_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not valid_phone(phone):
        await message.answer(
            "Похоже, номер указан некорректно.\n"
            "Пожалуйста, введите номер в формате 79781234567"
        )
        return

    await state.update_data(phone=phone)
    await message.answer("Телефон записан!")
    await message.answer(
        "Опишите ситуацию, связанную с этим гостем. "
        "Даты заезда и выезда, в чем конфликт, чем все закончилось и т.д."
    )
    await state.set_state(ReportGuest.description)


# Описание
@router.message(ReportGuest.description)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())

    text = (
        "Спасибо, что подробно описали вашу ситуацию с данным гостем.\n\n"
        "Прикрепите фото последствий (по желанию). Сломанное имущество, "
        "беспорядок в помещении, скриншот вашего общения с этим гостем и т.п.\n\n"
        "_⚠️ Пожалуйста, не присылайте фото паспортов и других личных документов гостей! "
        "Такие посты будут удаляться, а пользователи блокироваться._"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=photos_keyboard(),   # меню внизу: Подтвердить / Пропустить
    )
    await state.update_data(photo_ids=[])
    await state.set_state(ReportGuest.photos)


# Приём фото
@router.message(ReportGuest.photos, F.photo)
async def collect_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_ids: list[str] = data.get("photo_ids", [])

    if len(photo_ids) >= MAX_PHOTOS:
        await message.answer(
            f"Можно загрузить не более {MAX_PHOTOS} фото. "
            "Нажмите «Подтвердить» или «Пропустить».",
            reply_markup=photos_keyboard(),
        )
        return

    file_id = message.photo[-1].file_id
    photo_ids.append(file_id)
    await state.update_data(photo_ids=photo_ids)

    await message.answer(
        f"Фото добавлено ({len(photo_ids)}/{MAX_PHOTOS}).",
        reply_markup=photos_keyboard(),
    )


# Нажали «Пропустить» — отправляем на модерацию без фото
@router.message(ReportGuest.photos, F.text == "Пропустить")
async def msg_skip_photos(message: Message, state: FSMContext, bot: Bot):
    await queue_report_for_moderation(message, state, bot, with_photos=False)


# Нажали «Подтвердить» — отправляем на модерацию с фото (если есть)
@router.message(ReportGuest.photos, F.text == "Подтвердить")
async def msg_confirm_photos(message: Message, state: FSMContext, bot: Bot):
    await queue_report_for_moderation(message, state, bot, with_photos=True)


# =========================
# ХЕНДЛЕРЫ МОДЕРАЦИИ (для админов)
# =========================


@router.callback_query(F.data.startswith("mod_approve:"))
async def cb_mod_approve(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для модерации.", show_alert=True)
        return

    report_id = callback.data.split(":", 1)[1]
    report = pending_reports.pop(report_id, None)

    if not report:
        await callback.answer(
            "Заявка не найдена или уже обработана.",
            show_alert=True,
        )
        return

    await publish_report_to_channel(report, bot)

    # Уведомляем пользователя
    user_id = report["user_id"]
    try:
        await bot.send_message(
            user_id,
            "Ваш кейс прошёл модерацию и опубликован в канале.",
        )
    except Exception:
        pass

    await callback.message.answer(f"Заявка #{report_id} опубликована.")
    await callback.answer("Опубликовано", show_alert=False)


@router.callback_query(F.data.startswith("mod_reject:"))
async def cb_mod_reject(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для модерации.", show_alert=True)
        return

    report_id = callback.data.split(":", 1)[1]
    report = pending_reports.pop(report_id, None)

    if not report:
        await callback.answer(
            "Заявка не найдена или уже обработана.",
            show_alert=True,
        )
        return

    # Уведомляем пользователя об отказе
    user_id = report["user_id"]
    try:
        await bot.send_message(
            user_id,
            "Ваш кейс был отклонён модератором и не был опубликован в канале.",
        )
    except Exception:
        pass

    await callback.message.answer(f"Заявка #{report_id} отклонена.")
    await callback.answer("Отклонено", show_alert=False)


# =========================
# АДМИН-КОМАНДЫ ДЛЯ СТРАН
# =========================


@router.message(Command("list_countries"))
async def cmd_list_countries(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    countries = load_countries()
    await message.answer("Текущий список стран:\n" + "\n".join(countries))


@router.message(Command("add_country"))
async def cmd_add_country(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /add_country НазваниеСтраны")
        return
    new_country = parts[1].strip()
    countries = load_countries()
    if new_country in countries:
        await message.answer("Такая страна уже есть.")
        return
    countries.append(new_country)
    save_countries(countries)
    await message.answer(f"Страна «{new_country}» добавлена.")


@router.message(Command("del_country"))
async def cmd_del_country(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /del_country НазваниеСтраны")
        return
    name = parts[1].strip()
    countries = load_countries()
    if name not in countries:
        await message.answer("Такой страны нет в списке.")
        return
    countries.remove(name)
    save_countries(countries)
    await message.answer(f"Страна «{name}» удалена.")
