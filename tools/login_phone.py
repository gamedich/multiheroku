import asyncio
import os
import sys
from herokutl import TelegramClient

API_ID = 14052957
API_HASH = 'ad8d7e59ecd6d4c8c2b6119952b8aec4'
SESSIONS_DIR = '/home/botuser/heroku-userbot/sessions'

async def main():
    if len(sys.argv) < 2:
        print("Использование: python3 login_phone.py <номер_телефона_или_имя_сессии>")
        sys.exit(1)
        
    phone_or_name = sys.argv[1]
    session_file = os.path.join(SESSIONS_DIR, f"{phone_or_name}.session")
    client = TelegramClient(session_file, API_ID, API_HASH, proxy=('http', '127.0.0.1', 8889))
    
    await client.start(phone=phone_or_name)
    me = await client.get_me()
    print(f"\n[+] Вход успешен: {me.first_name} (@{me.username}) ID: {me.id}")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
