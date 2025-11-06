# 🕵️‍♂️ Telegram Bot — @blacklistguestsbot  
### Проект: «Нежелательные гости»

Бот для сбора и модерации кейсов от отельеров о недобросовестных гостях.  
Работает на **aiogram 3**, размещён на сервере под управлением **Ubuntu**.  
Посты публикуются в канал **[@blacklistguests](https://t.me/blacklistguests)** после модерации.

---

## ⚙️ Основные функции

- Проверка подписки на канал перед добавлением кейса  
- Пошаговое заполнение: страна → город → ФИО → телефон → описание → фото  
- Проверка корректности номера телефона  
- Возможность добавить до 10 фото  
- Модерация: посты отправляются администраторам для одобрения или отклонения  
- После одобрения — автоматическая публикация в канал  
- После отклонения — уведомление пользователю  
- Управление странами через команды `/add_country`, `/del_country`, `/list_countries`

---

## 📁 Структура проекта

```text
blacklistguestsbot/
│
├── bot/
│   ├── __init__.py
│   ├── config.py              # Подгрузка .env, токен, список админов
│   ├── handlers.py            # Основная логика бота + модерация
│   ├── keyboards.py           # Клавиатуры (меню, кнопки)
│   ├── states.py              # FSM-состояния
│   └── countries.py           # Загрузка и сохранение списка стран
│
├── data/
│   └── countries.json         # Файл со списком стран
│
├── .env                       # Секретные данные (см. ниже)
├── requirements.txt           # Список зависимостей
├── run.py                     # Точка входа (запуск бота)
└── .venv/                     # Виртуальное окружение Python

---

## 🔐 Файл `.env` (пример)

Создаётся в корне проекта:

```env
BOT_TOKEN=1234567890:AAAbbbCCCDDDeeeFFFgggHHHiiiJJJkkk
CHANNEL_USERNAME=@blacklistguests
ADMIN_IDS=123456789,987654321
ADMIN_IDS — Telegram ID модераторов через запятую
Узнать свой ID можно у бота @userinfobot

🚀 Установка на сервер (Ubuntu)
sudo apt update
sudo apt install -y git python3-venv
sudo mkdir -p /opt/blacklistguestsbot
sudo chown $USER:$USER /opt/blacklistguestsbot
cd /opt/blacklistguestsbot

git clone https://github.com/<ТВОЙ_ЛОГИН>/blacklistguestsbot.git .
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

nano .env    # вставь данные из примера выше

Проверка работы:
python run.py
Если бот отвечает в Telegram → всё ок ✅
Останавливаешь (Ctrl + C) и создаёшь systemd-сервис.

🧩 systemd-сервис /etc/systemd/system/blacklistguestsbot.service
[Unit]
Description=Telegram bot: blacklistguestsbot
After=network.target

[Service]
Type=simple
User=admin               # имя пользователя на сервере
WorkingDirectory=/opt/blacklistguestsbot
ExecStart=/opt/blacklistguestsbot/.venv/bin/python /opt/blacklistguestsbot/run.py
Restart=always

[Install]
WantedBy=multi-user.target

Активировать:
sudo systemctl daemon-reload
sudo systemctl enable blacklistguestsbot
sudo systemctl start blacklistguestsbot
sudo systemctl status blacklistguestsbot

Проверить логи:
sudo journalctl -u blacklistguestsbot -f


🔄 Обновление бота через Git

На локальной машине:
git add .
git commit -m "feat: добавлена модерация постов"
git push origin main

На сервере:
ssh root@your-server
cd /opt/blacklistguestsbot
git pull
source .venv/bin/activate
pip install -r requirements.txt   # если менялись зависимости
sudo systemctl restart blacklistguestsbot
sudo systemctl status blacklistguestsbot

🛠️ Полезные команды
sudo systemctl stop blacklistguestsbot      # остановить
sudo systemctl start blacklistguestsbot     # запустить
sudo systemctl restart blacklistguestsbot   # перезапустить
sudo systemctl status blacklistguestsbot    # статус
sudo journalctl -u blacklistguestsbot -f    # логи

💡 План будущих улучшений
 Предпросмотр поста перед отправкой на модерацию

 Хранение всех кейсов в базе (поиск по номеру телефона)

 Подсветка «злостных нарушителей» (гость встречается несколько раз)

 Возможность модератору запросить уточнение у автора

 Inline-поиск по базе гостей прямо в Telegram

 Отчёты и статистика для админов

Автор: @t0nc0
