import asyncio
import logging
import sys
from herokutl import TelegramClient
from herokutl.tl.types import User
from herokutl.errors import FloodWaitError

API_ID = 14052957
API_HASH = 'ad8d7e59ecd6d4c8c2b6119952b8aec4'
SESSION = '/home/botuser/heroku-userbot/sessions/heroku-5074793938'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/botuser/heroku-userbot/cleanup_deleted.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('deleted_cleaner')

async def main():
    logger.info("Запуск поиска и удаления диалогов с удаленными аккаунтами...")
    client = TelegramClient(SESSION, API_ID, API_HASH, proxy=('http', '127.0.0.1', 8889))
    await client.connect()
    
    deleted_dialogs = []
    logger.info("Сканируем список диалогов...")
    async for dialog in client.iter_dialogs(limit=None):
        entity = dialog.entity
        if isinstance(entity, User):
            is_deleted = getattr(entity, 'deleted', False)
            no_name = not entity.first_name and not entity.last_name and not entity.username
            if is_deleted or no_name:
                deleted_dialogs.append((entity, dialog.name, entity.id))

    logger.info(f"Найдено диалогов с удаленными аккаунтами: {len(deleted_dialogs)}")

    deleted_count = 0
    for entity, name, uid in deleted_dialogs:
        try:
            logger.info(f"Удаляем диалог с ID: {uid} (имя: '{name}')...")
            await client.delete_dialog(entity)
            deleted_count += 1
            await asyncio.sleep(1.0)
        except FloodWaitError as e:
            logger.warning(f"FloodWait: ожидание {e.seconds} сек...")
            await asyncio.sleep(e.seconds + 2)
            await client.delete_dialog(entity)
            deleted_count += 1
        except Exception as ex:
            logger.error(f"Ошибка при удалении {uid}: {ex}")

    logger.info(f"Успешно удалено диалогов с удаленными аккаунтами: {deleted_count} из {len(deleted_dialogs)}")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
