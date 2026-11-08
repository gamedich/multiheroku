import asyncio
import logging
import random
import sys
from herokutl import TelegramClient, errors
from herokutl.tl.types import Channel, Chat, User
from herokutl.tl.functions.contacts import BlockRequest

API_ID = 14052957
API_HASH = 'ad8d7e59ecd6d4c8c2b6119952b8aec4'
SESSION = '/home/botuser/heroku-userbot/sessions/heroku-5074793938'

# Белый список (НЕ УДАЛЯТЬ НИ ПРИ КАКИХ ОБСТОЯТЕЛЬСТВАХ)
WHITELIST_IDS = {
    7657422832,   # Владелец (@its_darksold1)
    777000,       # Официальный аккаунт Telegram
    93372553,     # @BotFather
    178220800,    # @SpamBot
    9162697030,   # Инлайн-бот юзербота (@Gratia_ppynhm_bot)
    1900098976,   # Канал @uet73
    4406172606,   # Служебный чат heroku-userbot (Assets/Backups)
    1679998924,   # @hikka_ub (Модули)
    1582589190,   # @ftgmod3 (Модули)
    1208954059,   # @TheUltroid (Модули)
    5519484330,   # @hikkamods_bot (Модули)
}

WHITELIST_USERNAMES = {
    'its_darksold1',
    'uet73',
    'botfather',
    'spambot',
    'hikka_ub',
    'ftgmod3',
    'theultroid',
    'hikkamods_bot',
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/botuser/heroku-userbot/cleanup.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('cleaner')

async def main():
    logger.info("Запуск безопасной очистки аккаунта...")
    client = TelegramClient(SESSION, API_ID, API_HASH, proxy=('http', '127.0.0.1', 8889))
    await client.connect()
    
    dialogs_to_remove = []
    
    async for dialog in client.iter_dialogs(limit=250):
        entity = dialog.entity
        entity_id = entity.id
        username = (getattr(entity, 'username', '') or '').lower()
        title = dialog.name or str(entity_id)
        
        # Проверка вайтлиста
        if entity_id in WHITELIST_IDS or username in WHITELIST_USERNAMES:
            logger.info(f"KEEP (Белый список): {title} (ID: {entity_id}, @{username})")
            continue
            
        dialogs_to_remove.append((dialog, entity, title, entity_id, username))
        
    total = len(dialogs_to_remove)
    logger.info(f"Найдено к удалению/выходу: {total} диалогов. Начинаем плавную очистку...")
    
    success_count = 0
    err_count = 0
    
    for idx, (dialog, entity, title, entity_id, username) in enumerate(dialogs_to_remove, start=1):
        while True:
            try:
                # Если бот - сначала блокируем
                if isinstance(entity, User) and getattr(entity, 'bot', False):
                    try:
                        await client(BlockRequest(id=entity))
                    except Exception:
                        pass
                
                # Удаляем диалог / выходим из канала/группы
                await client.delete_dialog(dialog)
                success_count += 1
                logger.info(f"[{idx}/{total}] Успешно удалено/покинуто: {title} (ID: {entity_id})")
                break
            except errors.FloodWaitError as e:
                wait_sec = e.seconds + 5
                logger.warning(f"FloodWait от Telegram: пауза на {wait_sec} сек...")
                await asyncio.sleep(wait_sec)
            except Exception as e:
                err_count += 1
                logger.error(f"[{idx}/{total}] Ошибка при удалении {title} ({entity_id}): {e}")
                break
                
        # Плавная задержка между запросами 2.0 - 3.5 секунды для защиты от блокировок
        delay = random.uniform(2.0, 3.5)
        await asyncio.sleep(delay)
        
    logger.info(f"Очистка завершена! Успешно: {success_count}, Ошибок: {err_count}")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
