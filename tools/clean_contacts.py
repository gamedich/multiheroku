import asyncio
import logging
import sys
from herokutl import TelegramClient, errors
from herokutl.tl.functions.contacts import GetContactsRequest, DeleteContactsRequest

API_ID = 14052957
API_HASH = 'ad8d7e59ecd6d4c8c2b6119952b8aec4'
SESSION = '/home/botuser/heroku-userbot/sessions/heroku-5074793938'

WHITELIST_IDS = {
    7657422832,   # Основа (@its_darksold1)
    777000,
    93372553,
    178220800,
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/botuser/heroku-userbot/cleanup.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('contacts_cleaner')

async def main():
    logger.info("Проверка и очистка контактов Telegram...")
    client = TelegramClient(SESSION, API_ID, API_HASH, proxy=('http', '127.0.0.1', 8889))
    await client.connect()
    
    result = await client(GetContactsRequest(hash=0))
    users = getattr(result, 'users', [])
    logger.info(f"Всего контактов в адресной книге Telegram: {len(users)}")
    
    to_delete = []
    for user in users:
        uid = user.id
        username = (getattr(user, 'username', '') or '').lower()
        first_name = user.first_name or ''
        last_name = user.last_name or ''
        phone = user.phone or ''
        
        if uid in WHITELIST_IDS or username == 'its_darksold1':
            logger.info(f"KEEP CONTACT (Основа): {first_name} {last_name} (ID: {uid})")
            continue
            
        logger.info(f"К удалению контакт: {first_name} {last_name} (ID: {uid}, {phone})")
        to_delete.append(user)
        
    if to_delete:
        logger.info(f"Удаляем {len(to_delete)} контактов...")
        # Удаляем пачками по 10 контактов с паузами
        batch_size = 10
        for i in range(0, len(to_delete), batch_size):
            batch = to_delete[i:i + batch_size]
            try:
                await client(DeleteContactsRequest(id=batch))
                logger.info(f"Удалена пачка контактов {i + 1} - {min(i + batch_size, len(to_delete))}")
                await asyncio.sleep(2.0)
            except errors.FloodWaitError as e:
                logger.warning(f"FloodWait: пауза {e.seconds + 2}с")
                await asyncio.sleep(e.seconds + 2)
                await client(DeleteContactsRequest(id=batch))
            except Exception as e:
                logger.error(f"Ошибка при удалении контактов: {e}")
    else:
        logger.info("Лишних контактов не обнаружено.")
        
    await client.disconnect()
    logger.info("Очистка контактов завершена!")

if __name__ == '__main__':
    asyncio.run(main())
