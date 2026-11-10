import asyncio
import os
import shutil
from herokutl import TelegramClient

API_ID = 14052957
API_HASH = 'ad8d7e59ecd6d4c8c2b6119952b8aec4'
SRC_SESSION = '/home/botuser/accounts/service-1/sessions/heroku-5074793938.session'
TEMP_SESSION = '/tmp/list_dialogs_file.session'

async def main():
    shutil.copyfile(SRC_SESSION, TEMP_SESSION)
    client = TelegramClient(TEMP_SESSION.replace('.session', ''), API_ID, API_HASH, proxy=('http', '127.0.0.1', 8889))
    await client.connect()
    dialogs = await client.get_dialogs(limit=25)
    print(f"Total dialogs: {len(dialogs)}", flush=True)
    for d in dialogs:
        print(f"- [{d.id}] '{d.title or d.name}' (group={d.is_group}, channel={d.is_channel})", flush=True)
    await client.disconnect()
    if os.path.exists(TEMP_SESSION):
        os.remove(TEMP_SESSION)

if __name__ == '__main__':
    asyncio.run(main())
