import asyncio
import json
import logging
import os
import random
from datetime import datetime, timezone
from herokutl import TelegramClient, errors
from herokutl.tl.types import Channel, Chat, User
from herokutl.tl.functions.contacts import SearchRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("twinks_ops")

PROXY = ('http', '127.0.0.1', 8889)
OWNER_ID = 7657422832

WHITELIST_IDS = {
    4461506603,  # HQ Hub
    1900098976,  # uet73
    2037930399,  # uet73_chat
    4402944926,  # helpuet73
    2305753413,  # Seechat
    1627183816,  # Колледж прога
    675952118,   # Игры
    1546112685,  # lavhostchat
    1980610166,  # lavhostofftop
    1755474280,  # hikka-commands-logs
    1819795615,  # Группа грамматика общения
    4406172606,  # heroku-userbot (Assets/Backups)
    1621617710,  # hikka-assets
    7657422832,  # Owner
    777000,      # Telegram
}

WHITELIST_KEYWORDS = [
    "уэт", "uet", "транспорт", "троллей", "трамва", "чнту",
    "darksold", "депо", "штаб", "guzban", "botuser", "fast_ilya",
    "its_darksold1", "флейм", "flame", "leomatch", "bibinto"
]

TWINKS = [
    {
        "tag": "Twink-3",
        "username": "Darksaltiu",
        "session": "/home/botuser/accounts/twink-3/sessions/account_7999839708",
        "api_id": 4883642,
        "api_hash": "f3975ed9c1f919ee1fe62828e88ace55",
        "search_term": "telethon python"
    },
    {
        "tag": "Twink-4",
        "username": "Tralaladark",
        "session": "/home/botuser/accounts/twink-4/sessions/account_8501573051",
        "api_id": 4883642,
        "api_hash": "f3975ed9c1f919ee1fe62828e88ace55",
        "search_term": "разработка telegram ботов"
    }
]

def is_whitelisted(entity, name: str) -> bool:
    if entity.id in WHITELIST_IDS:
        return True
    uname = (getattr(entity, 'username', '') or '').lower()
    name_l = (name or '').lower()
    return any(kw in uname or kw in name_l for kw in WHITELIST_KEYWORDS)

async def clean_and_task_twink(twink_info, all_found_channels):
    tag = twink_info["tag"]
    session_path = twink_info["session"]
    logger.info(f"=== Подключение к {tag} (@{twink_info['username']}) ===")

    client = TelegramClient(session_path, twink_info["api_id"], twink_info["api_hash"], proxy=PROXY)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error(f"[{tag}] Не авторизован!")
            return {"tag": tag, "status": "unauthorized"}

        me = await client.get_me()
        logger.info(f"[{tag}] Успешно авторизован: {me.first_name} (@{me.username})")

        # 1. Очистка диалогов (удаленные аккаунты + мусорные каналы/боты)
        to_remove = []
        keep_count = 0
        deleted_users_count = 0

        async for dialog in client.iter_dialogs(limit=150):
            entity = dialog.entity
            name = dialog.name or str(entity.id)

            if isinstance(entity, User):
                if getattr(entity, 'deleted', False):
                    to_remove.append((dialog, "Deleted Account", name))
                    deleted_users_count += 1
                else:
                    # Обычных людей не трогаем
                    keep_count += 1
                continue

            # Каналы и группы
            if is_whitelisted(entity, name):
                keep_count += 1
                continue

            # Если канал/группа не в белом списке - помечаем на выход
            to_remove.append((dialog, "Group/Channel", name))

        logger.info(f"[{tag}] Найдено на удаление: {len(to_remove)} (из них Deleted: {deleted_users_count}), сохранено: {keep_count}")

        removed_count = 0
        for dlg, kind, name in to_remove:
            try:
                await client.delete_dialog(dlg)
                removed_count += 1
                await asyncio.sleep(0.8)
            except errors.FloodWaitError as fwe:
                logger.warning(f"[{tag}] FloodWait: {fwe.seconds}s, пропускаем дальше")
                break
            except Exception as e:
                logger.warning(f"[{tag}] Ошибка удаления {name}: {e}")

        # 2. Поиск каналов и чатов по теме проекта
        search_query = twink_info["search_term"]
        logger.info(f"[{tag}] Разведка по теме: '{search_query}'...")
        scout_items = []
        try:
            res = await client(SearchRequest(q=search_query, limit=15))
            for chat in getattr(res, 'chats', []):
                uname = getattr(chat, 'username', None)
                if uname:
                    full_username = f"@{uname}"
                    title = chat.title
                    participants = getattr(chat, 'participants_count', 'N/A')
                    if full_username not in all_found_channels:
                        all_found_channels[full_username] = {
                            "title": title,
                            "username": full_username,
                            "scout": tag,
                            "query": search_query,
                            "participants": participants
                        }
                    scout_items.append(f"• <b>{title}</b> ({full_username})")
        except Exception as e:
            logger.warning(f"[{tag}] Ошибка поиска: {e}")

        # 3. Отправка отчета Создателю (@its_darksold1 / OWNER_ID)
        top_scout_preview = "\n".join(scout_items[:5]) if scout_items else "<i>(поиск выполнен, данные агрегированы)</i>"
        report_msg = (
            f"🫡 <b>Рапорт от {tag} (@{me.username or 'твинк'}):</b>\n\n"
            f"🧹 <b>Очистка:</b> удалено <code>{removed_count}</code> мусорных диалогов (Deleted: {deleted_users_count}). Важные чаты и ЛС сохранены.\n"
            f"🎯 <b>Задача:</b> «Разведка открытых каналов и чатов по Python, aiogram 3.x, Telethon и архитектуре ботов» принята в работу!\n\n"
            f"🔍 <b>Мои находки по запросу <code>{search_query}</code>:</b>\n"
            f"{top_scout_preview}\n\n"
            f"⚡ <i>Остаюсь на связи и продолжаю мониторинг!</i>"
        )

        try:
            await client.send_message(OWNER_ID, report_msg)
            logger.info(f"[{tag}] Рапорт успешно отправлен Создателю (ID {OWNER_ID})")
        except Exception as e:
            logger.error(f"[{tag}] Не удалось отправить сообщение Создателю: {e}")

        return {
            "tag": tag,
            "username": me.username,
            "name": me.first_name,
            "cleaned": removed_count,
            "kept": keep_count,
            "status": "ready"
        }

    except Exception as e:
        logger.error(f"[{tag}] Сбой: {e}")
        return {"tag": tag, "status": f"error: {e}"}
    finally:
        await client.disconnect()

async def main():
    logger.info("Запуск операции: Очистка твинков + Рапорт Создателю + Разведка каналов...")
    all_found_channels = {}
    results = []

    for twink in TWINKS:
        res = await clean_and_task_twink(twink, all_found_channels)
        results.append(res)
        await asyncio.sleep(2)  # Безопасная пауза между сессиями

    # Сохраняем сводный каталог находок
    catalog_path = "/home/botuser/dev_modules/python_scout_channels.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(all_found_channels, f, ensure_ascii=False, indent=2)
    logger.info(f"Каталог находок сохранен в {catalog_path} (всего найдено: {len(all_found_channels)})")

    # Сводный отчет в текстовый файл
    report_file = "/home/botuser/twinks_ops_report.txt"
    lines = [
        f"📋 СВОДНЫЙ ОТЧЕТ ПО ОПЕРАЦИИ ТВИНКОВ ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')})",
        "=" * 60,
        "ТВИНКИ:"
    ]
    for r in results:
        lines.append(f"• {r.get('tag')}: @{r.get('username')} | Почищено: {r.get('cleaned', 0)} | Статус: {r.get('status')}")

    lines.append("\nСОБРАННЫЕ КАНАЛЫ И ЧАТЫ ПО PYTHON & БОТАМ:")
    for uname, data in all_found_channels.items():
        lines.append(f"• {data['title']} ({uname}) [найден {data['scout']} по '{data['query']}'] — участников: {data['participants']}")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nОперация успешно завершена! Найдено уникальных ресурсов: {len(all_found_channels)}")

if __name__ == "__main__":
    asyncio.run(main())
