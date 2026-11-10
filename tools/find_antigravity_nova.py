import asyncio
import json
import logging
import re
from herokutl import TelegramClient
from herokutl.tl.types import Channel, Chat, Message

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nova_search")

PROXY = ('http', '127.0.0.1', 8889)
SESSION = "/home/botuser/accounts/twink-3/sessions/account_7999839708"
API_ID = 4883642
API_HASH = "f3975ed9c1f919ee1fe62828e88ace55"
OWNER_ID = 7657422832

async def main():
    logger.info("Подключение к Twink-3 для поиска в чате Nova (@nova_txt)...")
    client = TelegramClient(SESSION, API_ID, API_HASH, proxy=PROXY)
    await client.connect()
    
    if not await client.is_user_authorized():
        logger.error("Twink-3 не авторизован!")
        return

    try:
        nova = await client.get_entity("@nova_txt")
        logger.info(f"Сущность получена: {nova.title} (ID: {nova.id})")
        
        # 1. Поиск закрепленных сообщений
        pinned_messages = []
        try:
            async for msg in client.iter_messages(nova, limit=10):
                if getattr(msg, 'pinned', False):
                    pinned_messages.append(msg)
        except Exception as pe:
            logger.warning(f"Ошибка чтения закрепленных: {pe}")

        # 2. Поиск по ключевым словам: antigravity, антигравити, ключ, key, версия, update
        keywords = ["antigravity", "антигравити", "agy", "ключ", "key", "обновлен", "update", "верси", "скачать", "load"]
        found_messages = []
        seen_ids = set()

        for kw in ["antigravity", "антигравити", "ключ", "версия", "обновление"]:
            logger.info(f"Поиск сообщений по запросу '{kw}'...")
            try:
                async for msg in client.iter_messages(nova, search=kw, limit=20):
                    if msg.id not in seen_ids:
                        seen_ids.add(msg.id)
                        text = msg.message or ""
                        found_messages.append({
                            "id": msg.id,
                            "date": msg.date.strftime("%d.%m.%Y %H:%M"),
                            "text": text,
                            "link": f"https://t.me/nova_txt/{msg.id}",
                            "buttons": [[b.text for b in row] for row in (msg.buttons or [])],
                            "file": getattr(msg.file, 'name', None) if msg.file else None
                        })
            except Exception as se:
                logger.warning(f"Ошибка поиска по '{kw}': {se}")

        # 3. Также проверим описание чата (about) и последние 15 сообщений
        full_chat = await client.get_entity("@nova_txt")
        logger.info(f"Всего найдено релевантных сообщений: {len(found_messages)}")

        # Сохраняем все находки в файл
        out_file = "/home/botuser/dev_modules/nova_antigravity_findings.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(found_messages, f, ensure_ascii=False, indent=2)
        logger.info(f"Находки сохранены в {out_file}")

        # Выводим в лог самые интересные
        for idx, m in enumerate(found_messages[:10], 1):
            snip = m['text'].replace('\n', ' ')[:100]
            print(f"[{idx}] {m['date']} | {m['link']} | File: {m['file']} | Text: {snip}")

    except Exception as e:
        logger.error(f"Сбой: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
