# ⏳ Путешествия во времени — Time Travel Bot

Telegram-бот: интерактивные путешествия по историческим эпохам и квиз «Что существовало тогда?» с настоящими музейными артефактами из коллекции Europeana.

Учебный проект по теме №10 «Путешествия во времени»: интерактивная экскурсия по эпохам, генерация артефактов/моды/событий, квиз «Что из этого существовало тогда?», ссылки на AR-реконструкции (виртуальные туры).

**API:** Europeana, Wikipedia, Google Arts & Culture / Street View.

---

## ✨ Возможности

### 🏛 Путешествие по эпохам

4 эпохи: **Древний мир, Средневековье, Новое время, XX век**. По каждой эпохе:

- ключевые исторические события со ссылками на Википедию;
- описание моды эпохи;
- живые артефакты с фотографиями из музеев Европы (Europeana API);
- ссылки на виртуальные туры Google Arts & Culture (360°) и панорамы Google Street View (Помпеи, Мон-Сен-Мишель, Версаль, Ист-Сайд-Галерея);
- краткая выжимка из статьи Википедии.

### ❓ Квиз «Что существовало тогда?»

5 случайных вопросов по выбранной эпохе + фото-бонус «угадай эпоху по реальному артефакту». После каждого ответа — пояснение с историческим фактом.

### 🏆 Геймификация

- **XP:** +10 за верный ответ, +25 за идеальный квиз.
- **Уровни со званиями:** Стажёр времени → Хронист → Архивариус → Хранитель эпох → Мастер времени.
- 7 достижений, история игр, топ-10 игроков.

### ⚙️ Настройки

- ежедневная рассылка «Факт дня» (вкл/выкл);
- сброс прогресса с подтверждением.

**Команды:** `/start` `/help` `/travel` `/quiz` `/profile` `/leaderboard` `/settings` `/fact`

---

## 🛠 Технологии

| Технология | Назначение |
|---|---|
| Python 3.12 | язык проекта |
| aiogram 3 | асинхронный фреймворк Telegram Bot API, FSM, роутеры |
| SQLAlchemy 2 (async) | ORM, параметризованные запросы к БД |
| aiosqlite | асинхронный драйвер SQLite (по умолчанию) |
| asyncpg | асинхронный драйвер PostgreSQL (опционально) |
| httpx | асинхронный HTTP-клиент для внешних API |
| cachetools | кэш в памяти с TTL |
| tenacity | retry с экспоненциальной задержкой |
| python-dotenv | конфигурация через переменные окружения |

---

## 🔌 Используемые API

| API | Для чего | Ключ |
|---|---|---|
| Europeana Search API v2 | фото и описания артефактов из музеев Европы | бесплатный: https://www.europeana.eu/en/get-api |
| Wikipedia REST / Action API | выжимки статей и поиск по Википедии | не требуется |
| Google Arts & Culture | ссылки на виртуальные экскурсии (360°) | не требуется (ссылки) |
| Google Street View | панорамы исторических мест | не требуется (ссылки) |

> 💡 Без ключа Europeana бот продолжает работать: раздел «Артефакты» показывает кураторский список из локального архива (graceful degradation, см. ниже).

---

## 🚀 Инструкция по развертыванию

### Требования

- Python 3.12+
- Git

### 1. Клонировать репозиторий

```bash
git clone https://github.com/<твой-ник>/time-travel-bot.git
cd time-travel-bot
```

### 2. Виртуальное окружение и зависимости

**Windows (PowerShell):**

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Получить ключи API

**Токен Telegram-бота:**

1. В Telegram открой [@BotFather](https://t.me/BotFather) → команда `/newbot`.
2. Задай имя и юзернейм (заканчивается на `bot`).
3. Скопируй токен вида `123456789:AAH...` — это `BOT_TOKEN`.

**Ключ Europeana:**

1. Зарегистрируйся на https://www.europeana.eu и подтверди e-mail (проверь папку «Спам»).
2. Открой https://www.europeana.eu/en/get-api → **Get your personal API key**.
3. Заполни форму (назначение: education / non-commercial) и скопируй ключ.

### 4. Настроить переменные окружения

```bash
cp .env.example .env   # Windows: скопировать файл вручную
```

Заполни `.env`:

```env
BOT_TOKEN=токен_от_BotFather
DB_URL=sqlite+aiosqlite:///time_travel.db
EUROPEANA_API_KEY=ключ_с_europeana
WIKI_LANG=ru
CACHE_TTL_SECONDS=3600
LOG_LEVEL=INFO
PROXY_URL=
```

> ⚠️ Файл `.env` содержит секреты и не коммитится — он исключён через `.gitignore`. В репозитории лежит только шаблон `.env.example`.

### 5. Настроить базу данных

По умолчанию используется **SQLite** — ничего настраивать не нужно: файл `time_travel.db` и все таблицы создаются автоматически при первом запуске.

**PostgreSQL (опционально):**

```sql
CREATE DATABASE timetravel;
```

и в `.env`:

```env
DB_URL=postgresql+asyncpg://user:password@localhost:5432/timetravel
```

### 6. Запустить

```bash
python -m bot.main
```

В консоли появится `Start polling` — бот работает. Проверка: `/start` в чате с ботом. Остановка: `Ctrl+C`.

---

## 🗄 Схема базы данных

```mermaid
erDiagram
    USERS ||--o{ GAME_HISTORY : "играет"
    USERS ||--o{ BADGES : "получает"

    USERS {
        int id PK
        bigint telegram_id UK "ID в Telegram, unique"
        string username "@username"
        string first_name "имя"
        int xp "очки опыта"
        int level "уровень = xp // 100 + 1"
        bool notifications_enabled "рассылка Факта дня"
        datetime created_at "дата регистрации"
    }

    GAME_HISTORY {
        int id PK
        int user_id FK
        string mode "quiz | travel"
        string epoch "antiquity | medieval | modern | xx"
        int correct "верных ответов"
        int total "всего вопросов"
        int xp_gained "получено XP"
        datetime played_at "дата игры"
    }

    BADGES {
        int id PK
        int user_id FK
        string code "ключ достижения"
        datetime awarded_at "дата выдачи"
    }
```

- **users** — профили пользователей (ID, имя, настройки уведомлений, прогресс).
- **game_history** — история игр (очки, результат по эпохам).
- **badges** — выданные достижения; уникальность пары `(user_id, code)` защищает от повторной выдачи.

**Связи:** `users 1 — ∞ game_history`, `users 1 — ∞ badges`. Доступ к данным — только через SQLAlchemy ORM (параметризованные запросы).

---

## 🔄 Конечный автомат (FSM)

```mermaid
stateDiagram-v2
    [*] --> menu : /start
    menu --> choosing_epoch : 🏛 Путешествие
    menu --> answering : ❓ Квиз
    choosing_epoch --> answering : Квиз по эпохе
    answering --> answering : вопрос → ответ → пояснение → дальше
    answering --> results : все вопросы отвечены
    results --> menu : state.clear()
```

- `TravelStates.choosing_epoch` — выбор эпохи для экскурсии;
- `QuizStates.answering` — цикл квиза (защита от «протухших» кнопок и двойного ответа на вопрос);
- итоги квиза: подсчёт XP, выдача достижений, `state.clear()`.

---

## 🛡 Надёжность и безопасность

- **Retry:** `tenacity` — 3 попытки, экспоненциальная задержка 0.5–4 с при сетевых сбоях внешних API.
- **Кэш в памяти (TTL):** Википедия — 1 час, Europeana — 6 часов (maxsize 128). Снижает нагрузку на API и ускоряет повторные ответы.
- **Graceful degradation:** Europeana недоступен → кураторский архив артефактов; Википедия недоступна → блок пропускается; квиз полностью работает на локальном контенте.
- **Обработка ошибок:** глобальный error-handler логирует сбой и корректно отвечает пользователю; защита от двойного начисления XP при повторном нажатии.
- **Безопасность:**
  - ORM SQLAlchemy (параметризованные запросы → защита от SQL-инъекций);
  - навигация только через белый список `callback_data`;
  - валидация и отсечение длины пользовательских строк;
  - логирование действий только по `telegram_id`, без персональных данных;
  - секреты — только в `.env`.

---

## 📁 Структура проекта

```text
time-travel-bot/
├── bot/
│   ├── main.py          # точка входа: Bot, Dispatcher, роутеры
│   ├── config.py        # конфигурация из .env
│   ├── states.py        # FSM-состояния
│   ├── db/              # движок (engine) и ORM-модели (models)
│   ├── data/            # доменный контент: эпохи, вопросы квиза, факты
│   ├── handlers/        # start, travel, quiz, profile, leaderboard, common
│   ├── services/        # клиенты API (europeana, wikipedia), логика (quiz, users, facts)
│   ├── keyboards/       # inline-клавиатуры и callback-фабрики
│   └── utils/           # TTL-кэш, retry-декоратор
├── .env.example         # шаблон переменных окружения (без секретов)
├── requirements.txt     # зависимости
├── .gitignore           # venv, .env, кэш, IDE
└── README.md
```

---

## 👤 Автор

**Саков Даниил Сергеевич** группа-141-ПМо— тема №10 «Путешествия во времени»
Бот в Telegram: [@time_travel_epohi_bot](https://t.me/@time_travel_epohi_bot)
