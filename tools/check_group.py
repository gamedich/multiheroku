import asyncio
import os
import shutil
from herokutl import TelegramClient

API_ID = 14052957
API_HASH = 'ad8d7e59ecd6d4c8c2b6119952b8aec4'
SRC_SESSION = '/home/botuser/accounts/service-1/sessions/heroku-5074793938.session'
TEMP_SESSION = '/tmp/check_group.session'

async def main():
    shutil.copyfile(SRC_SESSION, TEMP_SESSION)
    client = TelegramClient(TEMP_SESSION.replace('.session', ''), API_ID, API_HASH, proxy=('http', '127.0.0.1', 8889))
    await client.connect()
    print("Connected.", flush=True)
    async for m in client.iter_messages(-5203243364, limit=10):
        print(f"[{m.date}] sender_id={m.sender_id}: {m.text}", flush=True)
    await client.disconnect()
    if os.path.exists(TEMP_SESSION):
        os.remove(TEMP_SESSION)

if __name__ == '__main__':
    asyncio.run(main())
