# Cleaning Service Telegram Bot

Асинхронный Telegram-бот на `aiogram 3.x` для сервиса уборки с ролями:
- `admin` (управление пользователями, финансами, отчётами)
- `manager` (создание заявок, счёт PDF+QR, свои отчёты)
- `cleaner` (взятие заказов, фото до/после, реквизиты)

## 1. Что уже реализовано
- Ролевая модель с хранением пользователей в PostgreSQL.
- Авторизация менеджера по паролю, выданному админом.
- Пошаговое создание заявки (FSM).
- Публикация заявки в супергруппу/топик (если задан `SUPPORT_CHAT_ID` + `topic_id` города).
- Принятие заказа клинером по inline-кнопке `🧹 Взять заказ`.
- Обмен контактами менеджер/клинер при принятии заказа.
- Загрузка фото `before/after` (по подписи `order:<id>|before|after`).
- Статистика `/stats` с ролевой фильтрацией.
- Экспорт отчётов в CSV/XLSX/PDF из inline-кнопок.
- Генерация счёта PDF + QR для оплаты.
- Финансовые статусы: подтверждение оплаты клиента и выплата клинеру.
- Логи в файл `logs/bot.log` и таблицу аудита `audit_logs`.
- Базовая мультиязычность RU/EN (`/lang`).

## 2. Структура проекта
```text
project/
 ┣ bot.py
 ┣ config.py
 ┣ handlers/
 ┃ ┣ admin.py
 ┃ ┣ manager.py
 ┃ ┣ cleaner.py
 ┃ ┣ common.py
 ┃ ┗ common_utils.py
 ┣ states/
 ┃ ┗ manager_state.py
 ┣ database/
 ┃ ┣ db.py
 ┃ ┗ models.py
 ┣ services/
 ┃ ┣ auth.py
 ┃ ┗ service.py
 ┣ middlewares/
 ┃ ┗ db.py
 ┣ utils/
 ┃ ┣ keyboards.py
 ┃ ┣ pdf_generator.py
 ┃ ┗ exporters.py
 ┣ locales/
 ┃ ┗ texts.py
 ┣ requirements.txt
 ┗ .env.example
```

## 3. Быстрый старт (локально)
### 3.1. Подготовка
```powershell
cd c:\apex_clean
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3.2. PostgreSQL
Создай БД, например `cleaning_bot`.

Пример строки подключения:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cleaning_bot
```

### 3.3. Настройка .env
1. Скопируй `.env.example` в `.env`.
2. Заполни:
- `BOT_TOKEN` (получи у @BotFather)
- `ADMIN_IDS` (telegram id админа, можно несколько через запятую)
- `SUPPORT_CHAT_ID` (id супергруппы, куда публикуются заявки)
- `DATABASE_URL`

### 3.4. Запуск
```powershell
.\venv\Scripts\python.exe bot.py
```

При первом запуске таблицы создаются автоматически.

## 4. Настройка Telegram
### 4.1. Создание бота
1. Открой @BotFather.
2. Выполни `/newbot`.
3. Сохрани токен в `.env`.

### 4.2. Группа и топики по городам
1. Создай супергруппу для заказов.
2. Добавь туда бота и выдай права на отправку сообщений.
3. Включи `Topics` в группе.
4. Создай топики (например: Москва, СПб).
5. Добавь города в боте командой:
```text
/add_city Москва 123
/add_city СПб 124
```
`123/124` это `topic_id` нужного топика.

### 4.3. Получение `chat_id` группы
- Добавь бота в группу.
- Отправь сообщение в группу.
- Посмотри `chat_id` через любой getUpdates-инструмент.
- Запиши в `.env` как `SUPPORT_CHAT_ID=-100...`.

## 5. Сценарии ролей
## Администратор
1. Нажимает `👥 Пользователи`.
2. Создает менеджера/клинера через inline-кнопки.
3. Менеджеру автоматически генерируется пароль и отправляется в личку.
4. Управляет финансами через:
- `/confirm_payment <order_id>`
- `/pay_cleaner <order_id>`
5. Смотрит статистику `/stats` и выгружает CSV/XLSX/PDF.
6. Настройки цены/комиссии:
- `/set_config <price> <commission>`

## Менеджер
1. Получает пароль от админа.
2. Входит `/login`.
3. Нажимает `🧾 Новая заявка` и заполняет шаги:
- город
- клиент
- телефон
- адрес
- услуга
- цена
- дата/время
4. Заявка публикуется в нужном топике группы.
5. После принятия заказа клинером получает уведомление.
6. Может скачать `💳 Счёт PDF + QR`.
7. Смотрит только свои данные в `/stats`.

## Клинер
1. Нажимает `🆕 Заявки в моем городе`.
2. Берет заказ кнопкой `🧹 Взять заказ`.
3. Получает контакт менеджера.
4. Загружает фото в чат с подписью:
- `order:15|before`
- `order:15|after`
5. Заполняет реквизиты через `💼 Мои реквизиты`.
6. Получает уведомление о выплате.

## 6. Команды
- `/start` открыть главное меню
- `/menu` показать меню
- `/lang` переключить RU/EN
- `/stats` статистика по роли
- `/login` вход менеджера по паролю
- `/add_city <name> [topic_id]` добавить город (admin)
- `/set_config <price> <commission>` настройки (admin)
- `/confirm_payment <order_id>` подтвердить оплату клиента (admin)
- `/pay_cleaner <order_id>` отметить выплату клинеру (admin)

## 7. Интерфейс и кнопки
Бот ориентирован на inline-flow и эмодзи:
- `👥 Пользователи`
- `🧾 Новая заявка`
- `🆕 Заявки в моем городе`
- `🧹 Взять заказ`
- `📊 Статистика`
- `💳 Счёт PDF + QR`

## 8. Развёртывание на Timeweb VPS
## 8.1. На сервере
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql
```

## 8.2. Клонирование и запуск
```bash
git clone <your_repo_url> /opt/cleaning-bot
cd /opt/cleaning-bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# отредактируй .env
python bot.py
```

## 8.3. systemd
Скопируй файл `deploy/cleaning-bot.service` в `/etc/systemd/system/cleaning-bot.service`, затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cleaning-bot
sudo systemctl start cleaning-bot
sudo systemctl status cleaning-bot
```

## 9. CI (GitHub Actions)
Файл `.github/workflows/ci.yml` запускает:
- установку зависимостей
- compile-check (`python -m compileall .`)

## 10. Для человека, который видит систему впервые
1. Админ создает город(а) и пользователей.
2. Менеджер получает пароль и входит `/login`.
3. Менеджер создает заявку через кнопку.
4. Клинер берет заявку в групповом топике.
5. Клинер отправляет фото до/после.
6. Менеджер подтверждает выполнение.
7. Админ подтверждает оплату и выплату.
8. Отчеты выгружаются в CSV/XLSX/PDF.

## 11. Что добавить в следующей итерации
- Alembic миграции и seed-скрипты.
- Реальный платёжный провайдер вместо demo link.
- Полноценный чат-прокси менеджер↔клинер внутри бота.
- Напоминания по cron/APScheduler.
- Unit/integration тесты (pytest + test DB).
