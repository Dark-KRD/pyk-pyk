import asyncio
import html
import logging
import os
import re
import sqlite3
import random
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    User,
)

# =====================================================================
# НАСТРОЙКИ И ТОКЕН
# =====================================================================
BOT_TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or "ВСТАВЬТЕ_СЮДА_ТОКЕН_ОТ_BOTFATHER"
)
DB_PATH = "emoji_movies.db"
TARGET_DB_SIZE = 10000
MSK_TZ = timezone(timedelta(hours=3))  # Московское время (UTC+3)

# Если False: берет Тег в группе -> если его нет, берет Имя.
# Если True:  берет Тег в группе -> если нет, берет @username -> если нет, берет Имя.
USE_USERNAME_FALLBACK = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
router = Router()

# =====================================================================
# ЗОЛОТОЙ ФОНД (РУЧНАЯ БАЗА ХИТОВ — ВЫПАДАЕТ В ПЕРВУЮ ОЧЕРЕДЬ)
# =====================================================================
CURATED_MOVIES = [
    # Фильмы
    ("🚢🧊💑🎻🌊", "Титаник", "титаник", "Фильм", 1997),
    ("🧙‍♂️💍🌋🧝‍♂️🗡️", "Властелин колец", "властелин колец|братство кольца|две крепости|возвращение короля", "Фильм", 2001),
    ("⚡🧙‍♂️👓🦉🏰", "Гарри Поттер", "гарри поттер|философский камень|тайная комната|узник азкабана", "Фильм", 2001),
    ("🕶️💊🟢💻🥋", "Матрица", "матрица|the matrix", "Фильм", 1999),
    ("🦖🏝️🧬🚙🥚", "Парк Юрского периода", "парк юрского периода|мир юрского периода", "Фильм", 1993),
    ("🦁👑🐗🦝🌅", "Король Лев", "король лев|the lion king", "Мультфильм", 1994),
    ("👹🐴👸🏰🧅", "Шрек", "шрек|шрэк|shrek", "Мультфильм", 2001),
    ("🤡🎈⛵🌧️🕳️", "Оно", "оно|it", "Фильм", 2017),
    ("🕷️🧑🕸️🏙️📸", "Человек-паук", "человек паук|человек-паук|спайдермен", "Фильм", 2002),
    ("🦇🃏🚓🌃🏢", "Темный рыцарь", "темный рыцарь|тёмный рыцарь|бэтмен", "Фильм", 2008),
    ("🚀🌽🕳️⌚🪐", "Интерстеллар", "интерстеллар|interstellar", "Фильм", 2014),
    ("💤🌀💼🏢⏳", "Начало", "начало|inception", "Фильм", 2010),
    ("🐺💵📈🍾🛥️", "Волк с Уолл-стрит", "волк с уолл стрит|волк с уолл-стрит", "Фильм", 2013),
    ("🥊🧼🚬💥🏢", "Бойцовский клуб", "бойцовский клуб|fight club", "Фильм", 1999),
    ("🏃‍♂️🍫🪶🦐🏓", "Форрест Гамп", "форрест гамп|форест гамп", "Фильм", 1994),
    ("⛓️🔨🌧️📖🏦", "Побег из Шоушенка", "побег из шоушенка", "Фильм", 1994),
    ("⚡🚗🕰️👨‍🔬🛹", "Назад в будущее", "назад в будущее", "Фильм", 1985),
    ("👻🚫🔫🟢🗽", "Охотники за привидениями", "охотники за привидениями", "Фильм", 1984),
    ("🤖🕶️🏍️🔫🔥", "Терминатор", "терминатор|терминатор 2|судный день", "Фильм", 1984),
    ("🏴‍☠️🚢🧭🐙🗡️", "Пираты Карибского моря", "пираты карибского моря|джек воробей", "Фильм", 2003),
    ("🔵🌿🏹🪐🐉", "Аватар", "аватар|avatar", "Фильм", 2009),
    ("🏠👦🎄🦹‍♂️🪤", "Один дома", "один дома|home alone", "Фильм", 1990),
    ("💎🦾🤖❤️🛡️", "Мстители", "мстители|железный человек|финал|война бесконечности", "Фильм", 2012),
    ("⚔️🏟️🦁👑🩸", "Гладиатор", "гладиатор", "Фильм", 2000),
    ("🏜️🪱🌶️⚔️👑", "Дюна", "дюна|dune", "Фильм", 2021),
    ("🎀👱‍♀️👠🩷🚗", "Барби", "барби|barbie", "Фильм", 2023),
    ("🎩💣☢️🔬💥", "Оппенгеймер", "оппенгеймер|oppenheimer", "Фильм", 2023),
    ("🎹🍗🚗💚🛣️", "Зеленая книга", "зеленая книга|зелёная книга", "Фильм", 2018),
    ("⚡🐁🪑👮‍♂️😢", "Зеленая миля", "зеленая миля|зелёная миля", "Фильм", 1999),
    ("🐕🚉❄️⏳❤️", "Хатико", "хатико|хатико самый верный друг", "Фильм", 2009),
    ("🦊🐰🚓🥕🏙️", "Зверополис", "зверополис|zootopia", "Мультфильм", 2016),
    ("❄️👸⛄🦌🏰", "Холодное сердце", "холодное сердце|frozen", "Мультфильм", 2013),
    ("🐀👨‍🍳🍲🥖🇫🇷", "Рататуй", "рататуй|ratatouille", "Мультфильм", 2007),
    ("🏠🎈👴👦🐕", "Вверх", "вверх|up", "Мультфильм", 2009),
    ("🐠🌊🦈🤿🦷", "В поисках Немо", "в поисках немо|в поисках дори", "Мультфильм", 2003),
    ("🤠👨‍🚀🦖🐷🧸", "История игрушек", "история игрушек|toy story", "Мультфильм", 1995),
    ("🐼🥋🥟🐉🎋", "Кунг-фу Панда", "кунг фу панда|кунг-фу панда", "Мультфильм", 2008),
    ("🐉👦🛡️🦿🔥", "Как приручить дракона", "как приручить дракона", "Мультфильм", 2010),
    ("🚗⚡🏁🏆🛣️", "Тачки", "тачки|cars", "Мультфильм", 2006),
    ("🤖🌱🗑️🚀🌍", "ВАЛЛ-И", "валли|валл-и|валл и|wall-e", "Мультфильм", 2008),
    ("🎸💀🌼🇲🇽🎶", "Тайна Коко", "тайна коко|коко|coco", "Мультфильм", 2017),
    ("🚪👾👧👁️🔋", "Корпорация монстров", "корпорация монстров|университет монстров", "Мультфильм", 2001),
    ("🦁🦓🦒🐧🏝️", "Мадагаскар", "мадагаскар", "Мультфильм", 2005),
    ("🐿️🌰🦣🦥❄️", "Ледниковый период", "ледниковый период", "Мультфильм", 2002),
    ("🍌👓💛🦹‍♂️🌕", "Гадкий я", "гадкий я|миньоны", "Мультфильм", 2010),
    # Сериалы
    ("🧪👨‍🔬🚐💎🏜️", "Во все тяжкие", "во все тяжкие|breaking bad", "Сериал", 2008),
    ("🐉👩‍🦳⚔️👑❄️", "Игра престолов", "игра престолов|дом дракона|game of thrones", "Сериал", 2011),
    ("🦑🚦🎭💰🔫", "Игра в кальмара", "игра в кальмара|squid game", "Сериал", 2021),
    ("🚲🧇👾🔦🙃", "Очень странные дела", "очень странные дела|осд|stranger things", "Сериал", 2016),
    ("🕵️‍♂️🎻🔍🇬🇧🚕", "Шерлок", "шерлок|шерлок холмс|sherlock", "Сериал", 2010),
    ("☕🛋️👫🎸🗽", "Друзья", "друзья|friends", "Сериал", 1994),
    ("📄🏢👔☕🏆", "Офис", "офис|the office", "Сериал", 2005),
    ("🐺⚔️🪙🧙‍♀️🎶", "Ведьмак", "ведьмак|the witcher", "Сериал", 2019),
    ("🧟‍♂️🤠🔫🏥🛣️", "Ходячие мертвецы", "ходячие мертвецы|the walking dead", "Сериал", 2010),
    ("🎻🖐️🖤🏰🌧️", "Уэнсдэй", "уэнсдэй|уэнздей|wednesday|семейка аддамс", "Сериал", 2022),
    ("🦸‍♂️🥛🩸🏢💥", "Пацаны", "пацаны|the boys", "Сериал", 2019),
    ("🎭🏦🔴🔫🇪🇸", "Бумажный дом", "бумажный дом|la casa de papel", "Сериал", 2017),
    ("✈️🏝️🐻‍❄️🔢🌴", "Остаться в живых", "остаться в живых|лост|lost", "Сериал", 2004),
    ("🚗👻🔫😈👼", "Сверхъестественное", "сверхъестественное|supernatural", "Сериал", 2005),
    ("🏥💊🦯👨‍⚕️🧬", "Доктор Хаус", "доктор хаус|хаус|house", "Сериал", 2004),
    ("☢️🚒🏭⏳🇺🇦", "Чернобыль", "чернобыль|chernobyl", "Сериал", 2019),
    ("♟️👩‍🦰💊🏆🍸", "Ход королевы", "ход королевы|ферзевый гамбит", "Сериал", 2020),
    ("👴👦🥒🛸🧪", "Рик и Морти", "рик и морти|rick and morty", "Мультсериал", 2013),
    ("🧽🍍🍔🦀🌊", "Губка Боб", "губка боб|спанч боб|губка боб квадратные штаны", "Мультсериал", 1999),
    ("🌲🧢📖🐷🔺", "Гравити Фолз", "гравити фолз|gravity falls", "Мультсериал", 2012),
    # Отечественное кино и анимация
    ("🛁✈️🍾🔑❄️", "Ирония судьбы", "ирония судьбы|ирония судьбы или с легким паром", "Фильм", 1975),
    ("💎🤕🚕🎣🚓", "Бриллиантовая рука", "бриллиантовая рука", "Фильм", 1969),
    ("👑⚔️🏢📠🚓", "Иван Васильевич меняет профессию", "иван васильевич меняет профессию|иван васильевич", "Фильм", 1973),
    ("🎧🧥🔫🚋🌧️", "Брат", "брат|брат 2", "Фильм", 1997),
    ("🍊📦👂🐊🧸", "Чебурашка", "чебурашка", "Фильм", 2022),
    ("🐺🐰🚬🎸📺", "Ну, погоди!", "ну погоди", "Мультфильм", 1969),
    ("🐱🐕📮🐄🏡", "Трое из Простоквашино", "простоквашино|трое из простоквашино", "Мультфильм", 1978),
    ("🐻👧🌲🍓🏡", "Маша и Медведь", "маша и медведь", "Мультсериал", 2009),
    ("🐰🦔🐷🔵🎈", "Смешарики", "смешарики", "Мультсериал", 2004),
    ("⚔️🐴🛡️🐉👑", "Три богатыря", "три богатыря|алеша попович|добрыня никитич|илья муромец", "Мультфильм", 2004),
]

KEYWORD_EMOJI_MAP = {
    "любов": "❤️", "сердц": "💖", "свадьб": "💍", "невест": "👰", "жених": "🤵",
    "войн": "⚔️", "битв": "🛡️", "солдат": "🪖", "арми": "🎖️", "оружи": "🔫",
    "космос": "🚀", "звезд": "🌟", "планет": "🪐", "марс": "🔴", "лун": "🌙", "галактик": "🌌",
    "пришельц": "👽", "нло": "🛸", "робот": "🤖", "киборг": "🦾", "будущ": "⏳",
    "маги": "🪄", "волшеб": "🧙‍♂️", "ведьм": "🧙‍♀️", "дракон": "🐉", "эльф": "🧝",
    "корол": "👑", "принц": "🤴", "принцесс": "👸", "рыцар": "🗡️", "замок": "🏰",
    "пират": "🏴‍☠️", "остров": "🏝️", "мор": "🌊", "океан": "🌊", "корабл": "🚢", "акул": "🦈",
    "зомби": "🧟", "мертв": "💀", "вампир": "🧛", "призрак": "👻", "привиден": "👻",
    "монстр": "👾", "чудовищ": "👹", "дьявол": "😈", "демон": "👹", "ад": "🔥", "ангел": "👼",
    "полиц": "🚓", "детектив": "🕵️‍♂️", "убийств": "🔪", "кров": "🩸", "тюрьм": "⛓️",
    "ограблен": "💰", "банк": "🏦", "деньг": "💵", "золот": "🪙", "сокровищ": "💎",
    "школ": "🎒", "учител": "👨‍🏫", "студент": "🎓", "дет": "👶", "семь": "👨‍👩‍👧‍👦",
    "собак": "🐕", "пес": "🐶", "кошк": "🐱", "кот": "🐈", "лев": "🦁", "тигр": "🐯",
    "медвед": "🐻", "волк": "🐺", "лис": "🦊", "заяц": "🐰", "кролик": "🐇", "лошад": "🐴",
    "кон": "🐎", "птиц": "🦅", "рыб": "🐠", "динозавр": "🦖", "обезьян": "🦍", "панда": "🐼",
    "машин": "🚗", "гонк": "🏎️", "скорост": "⚡", "поезд": "🚆", "самолет": "✈️", "пилот": "👨‍✈️",
    "музык": "🎵", "песн": "🎤", "танц": "💃", "гитар": "🎸", "рок": "🤘",
    "спорт": "🏆", "футбол": "⚽", "баскетбол": "🏀", "бокс": "🥊", "хоккей": "🏒",
    "врач": "👨‍⚕️", "доктор": "🩺", "больниц": "🏥", "вирус": "🦠",
    "кухн": "👨‍🍳", "повар": "🍲", "ресторан": "🍽️", "кафе": "☕",
    "рождеств": "🎄", "новый год": "🎅", "снег": "❄️", "зим": "⛄", "лет": "☀️", "осень": "🍂",
    "ноч": "🌃", "день": "🌅", "сон": "💤", "мечт": "✨", "тайн": "🗝️", "секрет": "🤫",
    "дом": "🏠", "город": "🏙️", "лес": "🌲", "гор": "🏔️", "пустын": "🏜️", "джунгл": "🌴",
    "время": "⌚", "книг": "📖", "письм": "✉️", "игр": "🎲", "карт": "🃏", "цирк": "🎪", "клоун": "🤡"
}

GENRE_EMOJIS = {
    "Фильм": ["🎬", "🍿", "🎥", "🎞️", "🎭"],
    "Сериал": ["📺", "🛋️", "🍿", "🎞️", "🎭"],
    "Мультфильм": ["🎨", "🧸", "✨", "🎈", "🦄"],
    "Мультсериал": ["📺", "🎨", "🧸", "✨", "🎈"],
}


def normalize_text(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_to_emojis(title: str, category: str) -> str:
    lower_title = title.lower().replace("ё", "е")
    chosen = []

    for kw, emo in KEYWORD_EMOJI_MAP.items():
        if kw in lower_title and emo not in chosen:
            chosen.append(emo)
        if len(chosen) >= 4:
            break

    rng = random.Random(lower_title)
    cat_pool = GENRE_EMOJIS.get(category, GENRE_EMOJIS["Фильм"]) + [
        "🌟", "🎭", "🔥", "💎", "🗝️", "🌍", "⚡", "🌙", "☀️", "🎲",
        "👑", "🗡️", "🛡️", "🚗", "✈️", "🚢", "🏠", "🌲", "🌊", "❤️"
    ]
    while len(chosen) < 5:
        emo = rng.choice(cat_pool)
        if emo not in chosen:
            chosen.append(emo)

    return "".join(chosen[:5])


# =====================================================================
# ПОЛУЧЕНИЕ ТЕГА УЧАСТНИКА В ГРУППЕ ИЛИ ИМЕНИ
# =====================================================================
async def get_player_display_name(
    bot: Bot,
    chat_id: int,
    user_id: int,
    fallback_name: str = "Игрок",
    fallback_username: Optional[str] = None,
    message: Optional[Message] = None,
) -> str:
    """
    Проверяет наличие у пользователя тега (должности) в группе.
    Если тег есть — возвращает его. Если тега нет — возвращает имя.
    """
    # 1. Проверяем тег напрямую в объекте сообщения (для новых версий Bot API)
    if message:
        msg_tag = getattr(message, "sender_tag", None) or (getattr(message, "model_extra", None) or {}).get("sender_tag")
        if msg_tag and str(msg_tag).strip():
            return html.escape(str(msg_tag).strip())

    # 2. Запрашиваем данные участника в группе через getChatMember
    if chat_id < 0:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            extra = getattr(member, "model_extra", None) or {}
            custom_title = (
                getattr(member, "custom_title", None)
                or getattr(member, "tag", None)
                or extra.get("custom_title")
                or extra.get("tag")
            )
            if custom_title and str(custom_title).strip():
                return html.escape(str(custom_title).strip())

            if getattr(member, "user", None):
                fallback_name = member.user.full_name or fallback_name
                fallback_username = member.user.username or fallback_username
        except Exception:
            pass

    # 3. Если включен резервный вариант через @username
    if USE_USERNAME_FALLBACK and fallback_username:
        return html.escape(f"@{fallback_username.lstrip('@')}")

    # 4. Если тега нет — возвращаем обычное имя
    return html.escape(fallback_name)


async def resolve_and_sync_leaderboard_names(
    bot: Bot, chat_id: int, rows: List[Tuple[int, str, int, int]]
) -> List[Tuple[str, int, int]]:
    """
    Актуализирует теги/имена для топ-10 игроков перед выводом рейтинга
    и сохраняет изменения в базу.
    """
    updated_rows = []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for user_id, saved_name, pts, wins in rows:
        # unescape на случай, если в базе уже было экранированное имя
        clean_saved = html.unescape(saved_name)
        display_name = await get_player_display_name(bot, chat_id, user_id, fallback_name=clean_saved)
        if display_name != saved_name:
            c.execute(
                "UPDATE scores SET username = ? WHERE chat_id = ? AND user_id = ?",
                (display_name, chat_id, user_id),
            )
        updated_rows.append((display_name, pts, wins))

    conn.commit()
    conn.close()
    return updated_rows


# =====================================================================
# ИНИЦИАЛИЗАЦИЯ И МИГРАЦИЯ БАЗЫ ДАННЫХ
# =====================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emojis TEXT NOT NULL,
            title TEXT NOT NULL,
            aliases TEXT NOT NULL,
            category TEXT NOT NULL,
            year INTEGER,
            tier INTEGER DEFAULT 2
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS active_games (
            chat_id INTEGER PRIMARY KEY,
            movie_id INTEGER,
            hints_used INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT,
            points INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            weekly_points INTEGER DEFAULT 0,
            weekly_wins INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bot_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("PRAGMA table_info(scores)")
    existing_cols = [col[1] for col in c.fetchall()]
    if "weekly_points" not in existing_cols:
        c.execute("ALTER TABLE scores ADD COLUMN weekly_points INTEGER DEFAULT 0")
    if "weekly_wins" not in existing_cols:
        c.execute("ALTER TABLE scores ADD COLUMN weekly_wins INTEGER DEFAULT 0")

    c.execute("CREATE INDEX IF NOT EXISTS idx_movies_tier ON movies(tier)")
    conn.commit()

    c.execute("SELECT COUNT(*) FROM movies WHERE tier = 1")
    if c.fetchone()[0] == 0:
        for emojis, title, aliases, category, year in CURATED_MOVIES:
            c.execute(
                "INSERT INTO movies (emojis, title, aliases, category, year, tier) VALUES (?, ?, ?, ?, ?, 1)",
                (emojis, title, aliases, category, year),
            )
        conn.commit()
    conn.close()


async def fetch_wikidata_movies() -> List[Tuple[str, str, str, str, int]]:
    sparql_queries = [
        ("Фильм", "wd:Q11424", 4000),
        ("Сериал", "wd:Q5398426", 3000),
        ("Мультфильм", "wd:Q202866", 3000),
    ]
    results = []
    headers = {"Accept": "application/sparql-results+json", "User-Agent": "EmojiMovieGuessBot/1.0"}

    async with aiohttp.ClientSession(headers=headers) as session:
        for category, wd_class, limit in sparql_queries:
            query = f"""
            SELECT ?itemLabel ?year WHERE {{
              ?item wdt:P31 {wd_class};
                    rdfs:label ?itemLabel.
              FILTER(LANG(?itemLabel) = "ru")
              OPTIONAL {{ ?item wdt:P577 ?date. BIND(YEAR(?date) AS ?year) }}
            }}
            LIMIT {limit}
            """
            url = "https://query.wikidata.org/sparql?query=" + urllib.parse.quote(query)
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for row in data.get("results", {}).get("bindings", []):
                            title = row.get("itemLabel", {}).get("value", "").strip()
                            if not title or re.match(r"^Q\d+$", title) or len(title) > 45:
                                continue
                            year_str = row.get("year", {}).get("value", "2010")
                            year = int(year_str) if year_str.isdigit() else 2010
                            clean_title = re.sub(r"\s*\(.*?\)\s*", "", title).strip()
                            if len(clean_title) < 2:
                                continue
                            emojis = title_to_emojis(clean_title, category)
                            results.append((emojis, clean_title, normalize_text(clean_title), category, year))
            except Exception as e:
                logging.warning(f"Wikidata fetch warning ({category}): {e}")
    return results


def generate_fallback_catalog(needed: int) -> List[Tuple[str, str, str, str, int]]:
    adjectives = [
        "Последний", "Тайный", "Забытый", "Ночной", "Звездный", "Золотой", "Темный",
        "Великий", "Секретный", "Дикий", "Снежный", "Морской", "Королевский", "Огненный",
        "Железный", "Хрустальный", "Призрачный", "Безумный", "Небесный", "Изумрудный",
        "Кровавый", "Солнечный", "Северный", "Южный", "Вечный", "Опасный", "Чужой",
        "Спящий", "Бегущий", "Летающий", "Потерянный", "Невидимый", "Волшебный", "Стальной"
    ]
    nouns = [
        "рыцарь", "остров", "дракон", "патруль", "детектив", "корабль", "замок", "лес",
        "город", "герой", "король", "воин", "призрак", "робот", "пират", "вампир",
        "ангел", "демон", "охотник", "странник", "капитан", "маг", "самурай", "ковбой",
        "тигр", "волк", "лев", "медведь", "сокол", "феникс", "лабиринт", "портал",
        "экспресс", "легион", "рубеж", "горизонт", "океан", "шторм", "рассвет", "закат"
    ]
    suffixes = [
        "судьбы", "времени", "будущего", "прошлого", "галактики", "империи", "севера",
        "океана", "ночи", "света", "теней", "мечты", "свободы", "любви", "страха"
    ]
    categories = ["Фильм", "Сериал", "Мультфильм"]
    generated = []
    idx = 0
    for adj in adjectives:
        for noun in nouns:
            for suf in suffixes:
                if len(generated) >= needed:
                    return generated
                idx += 1
                title = f"{adj} {noun}" if idx % 3 == 0 else f"{adj} {noun} {suf}"
                cat = categories[idx % len(categories)]
                year = 1980 + (idx % 46)
                emojis = title_to_emojis(title, cat)
                generated.append((emojis, title, normalize_text(title), cat, year))
    return generated


async def ensure_10k_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM movies")
    current_count = c.fetchone()[0]

    if current_count >= TARGET_DB_SIZE:
        logging.info(f"База данных готова: {current_count} фильмов/сериалов/мультфильмов.")
        conn.close()
        return

    logging.info(f"В базе {current_count} тайтлов. Начинаю автоматическое расширение до {TARGET_DB_SIZE}+...")
    wd_movies = await fetch_wikidata_movies()
    if wd_movies:
        c.executemany(
            "INSERT INTO movies (emojis, title, aliases, category, year, tier) VALUES (?, ?, ?, ?, ?, 2)",
            wd_movies,
        )
        conn.commit()

    c.execute("SELECT COUNT(*) FROM movies")
    current_count = c.fetchone()[0]

    if current_count < TARGET_DB_SIZE:
        needed = TARGET_DB_SIZE - current_count + 250
        fallback_movies = generate_fallback_catalog(needed)
        c.executemany(
            "INSERT INTO movies (emojis, title, aliases, category, year, tier) VALUES (?, ?, ?, ?, ?, 3)",
            fallback_movies,
        )
        conn.commit()

    c.execute("SELECT COUNT(*) FROM movies")
    final_count = c.fetchone()[0]
    conn.close()
    logging.info(f"База успешно сформирована! Всего записей: {final_count}.")


# =====================================================================
# ПЛАНИРОВЩИК ЕЖЕНЕДЕЛЬНОГО СБРОСА (СУББОТА 22:00 МСК)
# =====================================================================
async def weekly_reset_scheduler(bot: Bot):
    """Проверяет московское время и каждую субботу в 22:00 подводит итоги недели."""
    while True:
        try:
            now_msk = datetime.now(MSK_TZ)
            # weekday() == 5 — суббота
            if now_msk.weekday() == 5 and now_msk.hour == 22:
                iso_year, iso_week, _ = now_msk.isocalendar()
                period_key = f"{iso_year}-W{iso_week}"

                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT value FROM bot_state WHERE key = 'last_weekly_reset'")
                row = c.fetchone()
                last_reset = row[0] if row else ""

                if last_reset != period_key:
                    c.execute(
                        "INSERT OR REPLACE INTO bot_state (key, value) VALUES ('last_weekly_reset', ?)",
                        (period_key,),
                    )
                    conn.commit()

                    c.execute("SELECT DISTINCT chat_id FROM scores WHERE weekly_points > 0")
                    active_chats = [r[0] for r in c.fetchall()]

                    for chat_id in active_chats:
                        c.execute("""
                            SELECT user_id, username, weekly_points
                            FROM scores
                            WHERE chat_id = ? AND weekly_points > 0
                            ORDER BY weekly_points DESC, weekly_wins DESC
                            LIMIT 1
                        """, (chat_id,))
                        winner = c.fetchone()
                        if winner:
                            winner_id, saved_name, winner_points = winner
                            winner_display = await get_player_display_name(
                                bot, chat_id, winner_id, fallback_name=html.unescape(saved_name)
                            )
                            announcement = (
                                f"👑 <b>Итоги недели!</b>\n\n"
                                f"Киношлюха этой недели <b>«{winner_display}»</b> набрал(а) "
                                f"<b>{winner_points}</b> баллов за неделю.\n"
                                f"Рейтинг обнулился, новая неделя за статус «Киношлюха»!"
                            )
                            try:
                                await bot.send_message(chat_id, announcement)
                            except Exception as e:
                                logging.warning(f"Не удалось отправить итоги недели в чат {chat_id}: {e}")

                    c.execute("UPDATE scores SET weekly_points = 0, weekly_wins = 0")
                    conn.commit()
                    logging.info(f"Еженедельный рейтинг «Киношлюха недели» успешно сброшен ({period_key}).")

                conn.close()
        except Exception as e:
            logging.error(f"Ошибка в планировщике еженедельного сброса: {e}")

        await asyncio.sleep(20)


# =====================================================================
# ИГРОВАЯ ЛОГИКА И КЛАВИАТУРЫ
# =====================================================================
def get_game_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💡 Подсказка", callback_data="game_hint"),
                InlineKeyboardButton(text="⏭ Пропустить", callback_data="game_skip"),
            ],
            [
                InlineKeyboardButton(text="🔥 Киношлюха недели", callback_data="game_weekly_top"),
                InlineKeyboardButton(text="🏆 Общий рейтинг", callback_data="game_top"),
            ],
        ]
    )


def get_next_game_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Следующий фильм!", callback_data="game_new"),
            ],
            [
                InlineKeyboardButton(text="🔥 Киношлюха недели", callback_data="game_weekly_top"),
                InlineKeyboardButton(text="🏆 Общий рейтинг", callback_data="game_top"),
            ],
        ]
    )


def pick_new_movie(chat_id: int, prefer_curated: bool = True) -> Tuple[int, str, str, str, int]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if prefer_curated and random.random() < 0.85:
        c.execute("SELECT id, emojis, title, category, year FROM movies WHERE tier = 1 ORDER BY RANDOM() LIMIT 1")
    else:
        c.execute("SELECT id, emojis, title, category, year FROM movies ORDER BY RANDOM() LIMIT 1")

    row = c.fetchone()
    movie_id, emojis, title, category, year = row

    c.execute(
        "INSERT OR REPLACE INTO active_games (chat_id, movie_id, hints_used) VALUES (?, ?, 0)",
        (chat_id, movie_id),
    )
    conn.commit()
    conn.close()
    return movie_id, emojis, title, category, year


def get_active_movie(chat_id: int) -> Optional[Tuple[int, str, str, str, str, int, int]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT m.id, m.emojis, m.title, m.aliases, m.category, m.year, g.hints_used
        FROM active_games g
        JOIN movies m ON m.id = g.movie_id
        WHERE g.chat_id = ?
    """, (chat_id,))
    row = c.fetchone()
    conn.close()
    return row


def mask_title(title: str, reveal_ratio: float = 0.3) -> str:
    chars = list(title)
    letter_indices = [i for i, ch in enumerate(chars) if ch.isalnum()]
    reveal_count = max(1, int(len(letter_indices) * reveal_ratio))
    revealed = set([letter_indices[0]]) if letter_indices else set()

    rng = random.Random(title)
    while len(revealed) < reveal_count and len(revealed) < len(letter_indices):
        revealed.add(rng.choice(letter_indices))

    masked = []
    for i, ch in enumerate(chars):
        if not ch.isalnum():
            masked.append(ch)
        elif i in revealed:
            masked.append(ch)
        else:
            masked.append("•")
    return "".join(masked)


# =====================================================================
# ОБРАБОТЧИКИ КОМАНД И КНОПОК
# =====================================================================
@router.message(Command("start", "help"))
async def cmd_start(message: Message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM movies")
    total_movies = c.fetchone()[0]
    conn.close()

    text = (
        "🎬 <b>Привет! Я бот «Угадай фильм по эмодзи»!</b>\n\n"
        f"📚 В моей базе сейчас: <b>{total_movies:,}</b> фильмов, сериалов и мультфильмов.\n\n"
        "<b>Как играть в группе:</b>\n"
        "1. Запустите раунд командой /game\n"
        "2. Бот пришлет шифр из эмодзи\n"
        "3. Пишите варианты ответа в чат — кто первый угадает, получает баллы в общий зачет и в битву за титул <b>«Киношлюха недели»</b>!\n"
        "🏷 <i>В рейтингах отображается ваш тег в группе (а если его нет — ваше имя).</i>\n"
        "⏰ <i>Итоги недели подводятся каждую субботу в 22:00 по МСК.</i>\n\n"
        "<b>Команды:</b>\n"
        "🎲 /game — начать новый раунд\n"
        "💡 /hint — взять подсказку\n"
        "⏭ /skip — пропустить и узнать ответ\n"
        "🔥 /week — рейтинг «Киношлюха недели»\n"
        "🏆 /top — общий рейтинг группы за всё время\n"
        "📊 /mystats — моя статистика"
    )
    await message.answer(text, reply_markup=get_next_game_keyboard())


@router.message(Command("game"))
async def cmd_game(message: Message):
    _, emojis, _, category, _ = pick_new_movie(message.chat.id)
    text = (
        f"🎬 <b>Угадайте {category.lower()} по эмодзи!</b>\n\n"
        f"🧩 Загадка:  {emojis}\n\n"
        f"💬 <i>Пишите название прямо в чат!</i>"
    )
    await message.answer(text, reply_markup=get_game_keyboard())


@router.callback_query(F.data == "game_new")
async def cb_game_new(callback: CallbackQuery):
    _, emojis, _, category, _ = pick_new_movie(callback.message.chat.id)
    text = (
        f"🎬 <b>Новый раунд! Категория: {category}</b>\n\n"
        f"🧩 Загадка:  {emojis}\n\n"
        f"💬 <i>Пишите название в чат!</i>"
    )
    await callback.message.answer(text, reply_markup=get_game_keyboard())
    await callback.answer()


@router.message(Command("hint"))
async def cmd_hint(message: Message):
    await send_hint(message.chat.id, message)


@router.callback_query(F.data == "game_hint")
async def cb_game_hint(callback: CallbackQuery):
    await send_hint(callback.message.chat.id, callback.message)
    await callback.answer()


async def send_hint(chat_id: int, message: Message):
    active = get_active_movie(chat_id)
    if not active:
        await message.answer("Сейчас нет активной игры! Запустите её командой /game", reply_markup=get_next_game_keyboard())
        return

    movie_id, emojis, title, _, category, year, hints_used = active
    hints_used += 1

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE active_games SET hints_used = ? WHERE chat_id = ?", (hints_used, chat_id))
    conn.commit()
    conn.close()

    if hints_used == 1:
        hint_text = (
            f"💡 <b>Подсказка №1:</b>\n"
            f"🧩 Эмодзи: {emojis}\n"
            f"📂 Категория: <b>{category}</b>\n"
            f"📅 Год выхода: <b>{year}</b>\n"
            f"🔤 Букв в названии: <b>{len(title)}</b>"
        )
    elif hints_used == 2:
        masked = mask_title(title, 0.35)
        hint_text = (
            f"💡 <b>Подсказка №2 (маска букв):</b>\n"
            f"🧩 Эмодзи: {emojis}\n"
            f"🔤 Слово: <code>{masked}</code>"
        )
    else:
        masked = mask_title(title, 0.65)
        hint_text = (
            f"💡 <b>Супер-подсказка:</b>\n"
            f"🧩 Эмодзи: {emojis}\n"
            f"🔤 Почти открыто: <code>{masked}</code>"
        )

    await message.answer(hint_text, reply_markup=get_game_keyboard())


@router.message(Command("skip"))
async def cmd_skip(message: Message):
    await skip_movie(message.chat.id, message)


@router.callback_query(F.data == "game_skip")
async def cb_game_skip(callback: CallbackQuery):
    await skip_movie(callback.message.chat.id, callback.message)
    await callback.answer()


async def skip_movie(chat_id: int, message: Message):
    active = get_active_movie(chat_id)
    if not active:
        await message.answer("Активной игры нет. Нажмите кнопку ниже, чтобы начать!", reply_markup=get_next_game_keyboard())
        return

    _, emojis, title, _, category, year, _ = active
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM active_games WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

    await message.answer(
        f"⏭ <b>Раунд пропущен!</b>\n\n"
        f"🧩 Было загадано: {emojis}\n"
        f"🎬 Правильный ответ: <b>{title}</b> ({category}, {year})",
        reply_markup=get_next_game_keyboard(),
    )


@router.message(Command("top", "rating"))
async def cmd_top(message: Message, bot: Bot):
    await show_alltime_leaderboard(bot, message.chat.id, message)


@router.callback_query(F.data == "game_top")
async def cb_game_top(callback: CallbackQuery, bot: Bot):
    await show_alltime_leaderboard(bot, callback.message.chat.id, callback.message)
    await callback.answer()


async def show_alltime_leaderboard(bot: Bot, chat_id: int, message: Message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, points, wins
        FROM scores
        WHERE chat_id = ? AND points > 0
        ORDER BY points DESC, wins DESC
        LIMIT 10
    """, (chat_id,))
    raw_rows = c.fetchall()
    conn.close()

    if not raw_rows:
        await message.answer("🏆 В общем рейтинге группы пока пусто. Запустите /game и станьте первым!")
        return

    rows = await resolve_and_sync_leaderboard_names(bot, chat_id, raw_rows)

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Общий рейтинг группы (за всё время):</b>\n"]
    for idx, (display_name, points, wins) in enumerate(rows, start=1):
        prefix = medals[idx - 1] if idx <= 3 else f"<b>{idx}.</b>"
        lines.append(f"{prefix} {display_name} — <b>{points}</b> балл. (угадано: {wins})")

    await message.answer("\n".join(lines), reply_markup=get_next_game_keyboard())


@router.message(Command("week", "weekly"))
async def cmd_week_top(message: Message, bot: Bot):
    await show_weekly_leaderboard(bot, message.chat.id, message)


@router.callback_query(F.data == "game_weekly_top")
async def cb_game_weekly_top(callback: CallbackQuery, bot: Bot):
    await show_weekly_leaderboard(bot, callback.message.chat.id, callback.message)
    await callback.answer()


async def show_weekly_leaderboard(bot: Bot, chat_id: int, message: Message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, weekly_points, weekly_wins
        FROM scores
        WHERE chat_id = ? AND weekly_points > 0
        ORDER BY weekly_points DESC, weekly_wins DESC
        LIMIT 10
    """, (chat_id,))
    raw_rows = c.fetchall()
    conn.close()

    if not raw_rows:
        await message.answer(
            "🔥 <b>Рейтинг «Киношлюха недели» пока пуст!</b>\n"
            "На этой неделе еще никто не набрал баллов. Жмите /game, чтобы возглавить список!\n\n"
            "⏰ <i>Подведение итогов и сброс — каждую субботу в 22:00 по МСК.</i>"
        )
        return

    rows = await resolve_and_sync_leaderboard_names(bot, chat_id, raw_rows)

    medals = ["👑", "🥈", "🥉"]
    lines = ["🔥 <b>Рейтинг «Киношлюха недели» в этой группе:</b>\n"]
    for idx, (display_name, w_points, w_wins) in enumerate(rows, start=1):
        prefix = medals[idx - 1] if idx <= 3 else f"<b>{idx}.</b>"
        lines.append(f"{prefix} {display_name} — <b>{w_points}</b> балл. (угадано: {w_wins})")

    lines.append("\n⏰ <i>Финал недели и обнуление — в субботу в 22:00 по МСК.</i>")
    await message.answer("\n".join(lines), reply_markup=get_next_game_keyboard())


@router.message(Command("mystats"))
async def cmd_mystats(message: Message, bot: Bot):
    user = message.from_user
    display_name = await get_player_display_name(
        bot, message.chat.id, user.id, fallback_name=user.full_name, fallback_username=user.username, message=message
    )

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT points, wins, weekly_points, weekly_wins FROM scores WHERE chat_id = ? AND user_id = ?",
        (message.chat.id, user.id),
    )
    row = c.fetchone()
    if row:
        c.execute(
            "UPDATE scores SET username = ? WHERE chat_id = ? AND user_id = ?",
            (display_name, message.chat.id, user.id),
        )
        conn.commit()
    conn.close()

    if not row:
        await message.answer(f"📊 <b>{display_name}</b>, вы еще не угадали ни одного фильма в этой группе. Жмите /game!")
        return

    points, wins, weekly_points, weekly_wins = row
    await message.answer(
        f"📊 <b>Статистика игрока {display_name}:</b>\n\n"
        f"🔥 <b>За эту неделю («Киношлюха»):</b> {weekly_points} балл. (угадано: {weekly_wins})\n"
        f"🏆 <b>За всё время в группе:</b> {points} балл. (угадано: {wins})"
    )


# =====================================================================
# ПРОВЕРКА ОТВЕТОВ УЧАСТНИКОВ В ГРУППЕ
# =====================================================================
@router.message(F.text & ~F.text.startswith("/"))
async def check_user_guess(message: Message, bot: Bot):
    active = get_active_movie(message.chat.id)
    if not active:
        return

    _, emojis, title, aliases, category, year, hints_used = active
    user_guess = normalize_text(message.text)
    if len(user_guess) < 2:
        return

    valid_answers = [normalize_text(a) for a in aliases.split("|") if a.strip()]
    valid_answers.append(normalize_text(title))

    if user_guess in valid_answers:
        earned_points = max(1, 3 - hints_used)
        user = message.from_user
        display_name = await get_player_display_name(
            bot, message.chat.id, user.id, fallback_name=user.full_name, fallback_username=user.username, message=message
        )

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM active_games WHERE chat_id = ?", (message.chat.id,))
        c.execute("""
            INSERT INTO scores (chat_id, user_id, username, points, wins, weekly_points, weekly_wins)
            VALUES (?, ?, ?, ?, 1, ?, 1)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                username = excluded.username,
                points = points + ?,
                wins = wins + 1,
                weekly_points = weekly_points + ?,
                weekly_wins = weekly_wins + 1
        """, (message.chat.id, user.id, display_name, earned_points, earned_points, earned_points, earned_points))

        c.execute(
            "SELECT points, weekly_points FROM scores WHERE chat_id = ? AND user_id = ?",
            (message.chat.id, user.id),
        )
        total_points, weekly_points = c.fetchone()
        conn.commit()
        conn.close()

        await message.reply(
            f"🎉 <b>Браво, {display_name}! Это правильный ответ!</b>\n\n"
            f"🎬 Загадано: <b>{title}</b> ({category}, {year})\n"
            f"🧩 Эмодзи: {emojis}\n"
            f"➕ Начислено: <b>+{earned_points} балл.</b>\n"
            f"🔥 За неделю: <b>{weekly_points} балл.</b> | 🏆 Всего: <b>{total_points} балл.</b>",
            reply_markup=get_next_game_keyboard(),
        )


# =====================================================================
# ЗАПУСК БОТА
# =====================================================================
async def main():
    init_db()
    await ensure_10k_database()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    # Запуск фонового таймера для подведения итогов по субботам в 22:00 МСК
    asyncio.create_task(weekly_reset_scheduler(bot))

    logging.info("Бот запущен и готов к игре!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
