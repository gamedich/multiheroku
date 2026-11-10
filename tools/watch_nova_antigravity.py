import asyncio
import json
import logging
import os
import re
from herokutl import TelegramClient
from herokutl.tl.types import InputMessagesFilterPinned

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nova_watcher")

PROXY = ('http', '127.0.0.1', 8889)
SESSION = '/home/botuser/accounts/twink-3/sessions/account_7999839708'
API_ID = 4883642
API_HASH = 'f3975ed9c1f919ee1fe62828e88ace55'
OWNER_ID = 7657422832
STATE_FILE = '/home/botuser/dev_modules/antigravity_key_state.json'

async def main():
    logger.info("Проверка обновлений Antigravity Unlocker и ключей в Nova...")
    client = TelegramClient(SESSION, API_ID, API_HASH, proxy=PROXY)
    await client.connect()
    if not await client.is_user_authorized():
        logger.error("Твинк-3 не авторизован")
        return

    try:
        nova = await client.get_entity('@nova_txt')
        last_state = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    last_state = json.load(f)
            except Exception:
                pass

        current_key = None
        current_version = None
        key_msg_id = None

        # Проверяем закрепленные сообщения на наличие ключа
        async for m in client.iter_messages(nova, filter=InputMessagesFilterPinned, limit=10):
            text = m.message or ""
            match = re.search(r'Ключ для\s+(v[0-9\.\+]+)\s*\n+([A-Z0-9]{20,30})', text, re.IGNORECASE)
            if match:
                current_version = match.group(1)
                current_key = match.group(2)
                key_msg_id = m.id
                break

        if not current_key:
            logger.info("Ключ в закрепе не изменился.")
            return

        last_key = last_state.get("key")
        last_version = last_state.get("version")

        if current_key != last_key or current_version != last_version:
            logger.info(f"ОБНАРУЖЕН НОВЫЙ КЛЮЧ: {current_version} -> {current_key}")
            alert = (
                f"🚨 <b>НОВЫЙ КЛЮЧ ANTIGRAVITY В ЧАТЕ NOVA!</b> 🚨\n\n"
                f"Версия: <code>{current_version}</code>\n"
                f"Ключ:\n<code>{current_key}</code>\n\n"
                f"🔗 <a href='https://t.me/nova_txt/{key_msg_id}'>Ссылка на закрепленное сообщение</a>"
            )
            await client.send_message(OWNER_ID, alert, parse_mode="html")
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"version": current_version, "key": current_key, "msg_id": key_msg_id}, f, indent=2)
            logger.info("Уведомление о новом ключе отправлено Создателю!")
        else:
            logger.info(f"Ключ актуален: {current_version} ({current_key})")

    except Exception as e:
        logger.error(f"Ошибка проверки Nova: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
