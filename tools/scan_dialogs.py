import asyncio
from herokutl import TelegramClient
from herokutl.tl.types import Channel, Chat, User

API_ID = 14052957
API_HASH = 'ad8d7e59ecd6d4c8c2b6119952b8aec4'
SESSION = '/home/botuser/heroku-userbot/sessions/heroku-5074793938'

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH, proxy=('http', '127.0.0.1', 8889))
    await client.connect()
    
    channels = []
    groups = []
    bots = []
    users = []
    
    async for dialog in client.iter_dialogs(limit=150):
        entity = dialog.entity
        name = dialog.name or 'Без названия'
        unread = dialog.unread_count
        
        if isinstance(entity, Channel):
            if entity.broadcast:
                channels.append((name, entity.id, unread, getattr(entity, 'username', None)))
            else:
                groups.append((name, entity.id, unread, getattr(entity, 'username', None)))
        elif isinstance(entity, Chat):
            groups.append((name, entity.id, unread, None))
        elif isinstance(entity, User):
            if getattr(entity, 'bot', False):
                bots.append((name, entity.id, unread, getattr(entity, 'username', None)))
            elif not getattr(entity, 'is_self', False):
                users.append((name, entity.id, unread, getattr(entity, 'username', None)))
                
    print(f'TOTAL_DIALOGS: {len(channels) + len(groups) + len(bots) + len(users)}')
    print(f'=== CHANNELS ({len(channels)}) ===')
    for c in channels:
        print(f'[CHANNEL] {c[0]} | @{c[3]} | ID:{c[1]}')
        
    print(f'=== GROUPS ({len(groups)}) ===')
    for g in groups:
        print(f'[GROUP] {g[0]} | @{g[3]} | ID:{g[1]}')
        
    print(f'=== BOTS ({len(bots)}) ===')
    for b in bots:
        print(f'[BOT] {b[0]} | @{b[3]} | ID:{b[1]}')
        
    print(f'=== USERS ({len(users)}) ===')
    for u in users:
        print(f'[USER] {u[0]} | @{u[3]} | ID:{u[1]}')
        
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
