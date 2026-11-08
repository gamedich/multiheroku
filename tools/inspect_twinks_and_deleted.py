import asyncio
from herokutl import TelegramClient
from herokutl.tl.types import Channel, Chat, User

API_ID = 14052957
API_HASH = 'ad8d7e59ecd6d4c8c2b6119952b8aec4'
SESSION = '/home/botuser/heroku-userbot/sessions/heroku-5074793938'
OWNER_ID = 7657422832

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH, proxy=('http', '127.0.0.1', 8889))
    await client.connect()
    
    print("=== CHECKING SAVED MESSAGES (ME) ===")
    async for msg in client.iter_messages('me', limit=15):
        print(f"[{msg.date}] (id={msg.id}): {repr(msg.text)}")

    print("\n=== CHECKING MESSAGES WITH OWNER ===")
    try:
        async for msg in client.iter_messages(OWNER_ID, limit=15):
            sender = "OWNER" if not msg.out else "ME"
            print(f"[{msg.date}] {sender} (id={msg.id}): {repr(msg.text)}")
    except Exception as e:
        print(f"Error checking owner messages: {e}")

    print("\n=== CHECKING DELETED ACCOUNTS IN DIALOGS ===")
    deleted_accounts = []
    total_dialogs = 0
    async for dialog in client.iter_dialogs(limit=200):
        total_dialogs += 1
        entity = dialog.entity
        if isinstance(entity, User):
            if getattr(entity, 'deleted', False):
                deleted_accounts.append((entity.id, dialog.name, dialog.unread_count))
            elif not entity.first_name and not entity.last_name and not entity.username:
                deleted_accounts.append((entity.id, f"EmptyName ({dialog.name})", dialog.unread_count))
                
    print(f"Total dialogs: {total_dialogs}")
    print(f"Found deleted accounts: {len(deleted_accounts)}")
    for acc in deleted_accounts:
        print(f"  - ID: {acc[0]} | Name: {acc[1]} | Unread: {acc[2]}")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
