import asyncio
import json
import logging
import os
import random
import re
from datetime import datetime, timezone
from herokutl import TelegramClient, errors
from herokutl.tl.types import Channel, Chat, User
from herokutl.tl.functions.channels import JoinChannelRequest
from herokutl.tl.functions.messages import ReadHistoryRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scout_digest")

PROXY = ('http', '127.0.0.1', 8889)
OWNER_ID = 7657422832

# План распределения целей по твинкам:
ASSIGNMENTS = [
    {
        "tag": "Twink-1",
        "username": "its_ilyakr111",
        "session": "/home/botuser/accounts/twink-1/sessions/account_5333160510",
        "api_id": 4883642,
        "api_hash": "f3975ed9c1f919ee1fe62828e88ace55",
        "role": "Python & Aiogram Core",
        "targets": ["@pythontgbotcourse", "@Aiogram_Devs"]
    },
    {
        "tag": "Twink-2",
        "username": "fast_ilya",
        "session": "/home/botuser/accounts/twink-2-nosim/sessions/account_5189061964",
        "api_id": 6378328,
        "api_hash": "3922dcbe446da84937188b7cb5c1328f",
        "role": "Hikka & Telethon Modules",
        "targets": ["@PyModule", "@shizu_talks"]
    },
    {
        "tag": "Twink-3",
        "username": "Darksaltiu",
        "session": "/home/botuser/accounts/twink-3/sessions/account_7999839708",
        "api_id": 4883642,
        "api_hash": "f3975ed9c1f919ee1fe62828e88ace55",
        "role": "Tools & Open-Source Community",
        "targets": ["@openlibrecommunitychat", "@ezmod_dev"]
    },
    {
        "tag": "Twink-4",
        "username": "Tralaladark",
        "session": "/home/botuser/accounts/twink-4/sessions/account_8501573051",
        "api_id": 4883642,
        "api_hash": "f3975ed9c1f919ee1fe62828e88ace55",
        "role": "GIS, Networks & Transports",
        "targets": ["@meshcore_rulang", "@dev_svyatoslav"]
    }
]

# Ключевые паттерны для фильтрации контента в дайджест:
TOPIC_PATTERNS = {
    "python_bots": [
        r"python", r"aiogram", r"telethon", r"asyncio", r"aiohttp",
        r"fastapi", r"bot\b", r"хэндлер", r"роутер", r"middleware"
    ],
    "modules_tools": [
        r"\.py\b", r"модул", r"custommod", r"hikka", r"ftg", r"сниппет",
        r"github\.com", r"репозитор", r"скрипт"
    ],
    "gis_transport": [
        r"карт", r"map", r"gis", r"leaflet", r"geojson", r"глонасс",
        r"gps", r"трекинг", r"транспорт", r"маршрут", r"депо", r"geofence"
    ],
    "backend_arch": [
        r"sqlite", r"wal", r"c#", r"\.net", r"database", r"баз[аы]",
        r"бэкенд", r"docker", r"nginx", r"systemd", r"compose"
    ]
}

def classify_message(text: str) -> list:
    categories = []
    text_l = text.lower()
    for cat, patterns in TOPIC_PATTERNS.items():
        if any(re.search(pat, text_l) for pat in patterns):
            categories.append(cat)
    return categories

async def try_solve_captcha(client, entity, me):
    """Поиск и автоматическое прохождение базовой кнопки-капчи"""
    try:
        await asyncio.sleep(2)
        async for msg in client.iter_messages(entity, limit=5):
            # Проверяем, адресовано ли нам или бот просит подтверждение
            is_for_us = False
            if msg.mentioned:
                is_for_us = True
            if me.username and f"@{me.username}" in (msg.message or ""):
                is_for_us = True
            if me.first_name and me.first_name in (msg.message or ""):
                is_for_us = True

            # Если есть кнопки (inline buttons)
            if msg.buttons:
                for row in msg.buttons:
                    for button in row:
                        btn_text = (button.text or "").lower()
                        # Ищем кнопки подтверждения человека
                        if any(k in btn_text for k in ["человек", "human", "пройти", "подтверд", "нажми", "click", "verify", "войти", "✅", "👌", "🟢"]):
                            logger.info(f"Найдена капча-кнопка: '{button.text}', нажимаем...")
                            try:
                                await button.click()
                                await asyncio.sleep(1.5)
                                return True
                            except Exception as be:
                                logger.warning(f"Ошибка клика по капче: {be}")
    except Exception as e:
        logger.warning(f"Ошибка при проверке капчи: {e}")
    return False

async def scout_target(client, entity_uname: str, me):
    """Плавный вход в чат/канал и сбор актуальной информации"""
    logger.info(f"Вход в целевой ресурс: {entity_uname}...")
    try:
        entity = await client.get_entity(entity_uname)
    except Exception as e:
        logger.warning(f"Не удалось получить {entity_uname}: {e}")
        return None

    # Плавное вступление с защитой
    joined = False
    try:
        await client(JoinChannelRequest(entity))
        joined = True
        logger.info(f"Успешный вход в {entity_uname}")
        # Проверяем капчу
        captcha_solved = await try_solve_captcha(client, entity, me)
        if captcha_solved:
            logger.info(f"Капча в {entity_uname} успешно пройдена!")
    except errors.UserAlreadyParticipantError:
        joined = True
        logger.info(f"Уже являемся участником {entity_uname}")
    except Exception as e:
        logger.info(f"Вход в {entity_uname} (или открытый просмотр без входа): {e}")

    # Сбор последних постов/сообщений
    harvested = []
    try:
        async for msg in client.iter_messages(entity, limit=40):
            text = msg.message or ""
            if not text and not msg.document:
                continue

            cats = classify_message(text)
            links = re.findall(r'https?://[^\s]+', text)
            
            # Извлечение прикрепленных файлов (.py модули)
            doc_name = ""
            if msg.document:
                for attr in getattr(msg.document, 'attributes', []):
                    fn = getattr(attr, 'file_name', None)
                    if fn:
                        doc_name = fn
                        if fn.endswith('.py') and 'modules_tools' not in cats:
                            cats.append('modules_tools')

            if cats or links or doc_name.endswith('.py'):
                snippet = text.replace('\n', ' ')[:140]
                harvested.append({
                    "date": msg.date.strftime("%d.%m %H:%M"),
                    "link": f"https://t.me/{entity_uname.lstrip('@')}/{msg.id}",
                    "categories": cats,
                    "snippet": snippet,
                    "urls": links,
                    "doc": doc_name
                })
    except Exception as e:
        logger.warning(f"Ошибка сбора сообщений из {entity_uname}: {e}")

    return {
        "target": entity_uname,
        "title": getattr(entity, 'title', entity_uname),
        "joined": joined,
        "count": len(harvested),
        "items": harvested[:8]  # Топ-8 самых ценных
    }

async def process_twink(twink_cfg, collected_digest):
    tag = twink_cfg["tag"]
    logger.info(f"\n==========================================")
    logger.info(f"ЗАПУСК ТВИНКА: {tag} ({twink_cfg['role']})")
    logger.info(f"==========================================")

    client = TelegramClient(twink_cfg["session"], twink_cfg["api_id"], twink_cfg["api_hash"], proxy=PROXY)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error(f"[{tag}] Не авторизован!")
            return

        me = await client.get_me()
        logger.info(f"[{tag}] В сети: {me.first_name} (@{me.username})")

        twink_results = []
        for target in twink_cfg["targets"]:
            # Антифрод-пауза перед каждым действием (4-7 сек)
            delay = random.uniform(4.0, 7.0)
            logger.info(f"[{tag}] Задержка {delay:.1f}с перед переходом в {target}...")
            await asyncio.sleep(delay)

            res = await scout_target(client, target, me)
            if res:
                twink_results.append(res)

        collected_digest.append({
            "tag": tag,
            "username": me.username,
            "role": twink_cfg["role"],
            "targets": twink_results
        })

    except Exception as e:
        logger.error(f"[{tag}] Ошибка воркера: {e}")
    finally:
        await client.disconnect()

async def main():
    logger.info("Старт глубокой мультиаккаунтной разведки...")
    collected_digest = []

    for twink_cfg in ASSIGNMENTS:
        await process_twink(twink_cfg, collected_digest)
        await asyncio.sleep(3)

    # Формируем сводный красивый дайджест
    lines = [
        "🔥 <b>МУЛЬТИАККАУНТНЫЙ ДАЙДЖЕСТ РАЗВЕДКИ</b> 🔥",
        f"<i>Сводка собрана пулом твинков на {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}</i>\n",
        "👥 <b>Статус твинков на дежурстве:</b>"
    ]

    all_harvested_items = []
    for t in collected_digest:
        joined_str = ", ".join([f"{tgt['title']}" for tgt in t["targets"]])
        lines.append(f"• <b>{t['tag']}</b> (@{t['username']}) — <i>{t['role']}</i>: мониторит {joined_str}")
        for tgt in t["targets"]:
            for item in tgt["items"]:
                item["source_title"] = tgt["title"]
                item["source_target"] = tgt["target"]
                all_harvested_items.append(item)

    lines.append("\n" + "—" * 25 + "\n")

    # Группировка по рубрикам
    categories_dict = {
        "python_bots": "🐍 <b>Python, aiogram 3.x & Telegram-боты:</b>",
        "modules_tools": "🧩 <b>Модули, юзерботы и код:</b>",
        "gis_transport": "🗺️ <b>GIS, Leaflet, сети & транспорт:</b>",
        "backend_arch": "⚙️ <b>Бэкенд, SQLite & архитектура:</b>"
    }

    categorized_seen = {cat: set() for cat in categories_dict}

    for cat_key, cat_header in categories_dict.items():
        cat_lines = []
        for item in all_harvested_items:
            if cat_key in item["categories"]:
                unique_key = item["snippet"][:40]
                if unique_key in categorized_seen[cat_key]:
                    continue
                categorized_seen[cat_key].add(unique_key)

                urls_str = " ".join([f"<a href='{u}'>[Ссылка]</a>" for u in item["urls"][:2]])
                doc_str = f" 📄 <code>{item['doc']}</code>" if item["doc"] else ""
                cat_lines.append(
                    f"• <b>{item['source_title']}</b> ({item['date']}){doc_str}\n"
                    f"  <i>{item['snippet']}...</i>\n"
                    f"  🔗 <a href='{item['link']}'>Перейти к сообщению</a> {urls_str}"
                )
                if len(cat_lines) >= 4:
                    break

        if cat_lines:
            lines.append(cat_header)
            lines.extend(cat_lines)
            lines.append("")

    lines.append("⚡ <i>Твинки продолжают фоновое дежурство в чатах! Следующий срез — по расписанию.</i>")
    final_digest_text = "\n".join(lines)

    # Сохраняем дайджест в файл
    digest_path = "/home/botuser/deep_scout_digest.md"
    with open(digest_path, "w", encoding="utf-8") as f:
        f.write(final_digest_text)
    logger.info(f"Дайджест сохранен в {digest_path}")

    # Отправляем дайджест Создателю через сессию Twink-1
    logger.info("Отправка финального дайджеста Создателю...")
    sender_cfg = ASSIGNMENTS[0]
    sender_cl = TelegramClient(sender_cfg["session"], sender_cfg["api_id"], sender_cfg["api_hash"], proxy=PROXY)
    try:
        await sender_cl.connect()
        if await sender_cl.is_user_authorized():
            # Если текст длинный - делим на 2 части
            if len(final_digest_text) > 4000:
                parts = [final_digest_text[:3900], final_digest_text[3900:]]
                for p in parts:
                    await sender_cl.send_message(OWNER_ID, p, parse_mode="html", link_preview=False)
            else:
                await sender_cl.send_message(OWNER_ID, final_digest_text, parse_mode="html", link_preview=False)
            logger.info("Дайджест успешно доставлен Создателю в Telegram!")
    except Exception as e:
        logger.error(f"Ошибка отправки дайджеста: {e}")
    finally:
        await sender_cl.disconnect()

    print(f"\n Операция успешно завершена! Собрано находок: {len(all_harvested_items)}")

if __name__ == "__main__":
    asyncio.run(main())
