import asyncio
import os
import shutil
import sys
import json
from herokutl import TelegramClient
from herokutl.sessions import StringSession

API_ID = 14052957
API_HASH = 'ad8d7e59ecd6d4c8c2b6119952b8aec4'
SESSIONS_DIR = '/home/botuser/heroku-userbot/sessions'
BACKUP_DIR = '/home/botuser/backups/sessions'
REGISTRY_PATH = '/home/botuser/heroku-userbot/tools/accounts_registry.json'

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

async def verify_and_register(session_target, tag="main_account", has_sim=True, note="Основной аккаунт"):
    print(f"[*] Проверка сессии для тега '{tag}'...")
    client = TelegramClient(session_target, API_ID, API_HASH, proxy=('http', '127.0.0.1', 8889))
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("[!] ОШИБКА: Сессия не авторизована!")
            return False

        me = await client.get_me()
        user_id = me.id
        first_name = me.first_name or ""
        last_name = me.last_name or ""
        username = me.username or "без юзернейма"
        phone = me.phone or "скрыт/нет"

        print(f"[+] УСПЕШНО! Авторизован аккаунт:")
        print(f"    - ID: {user_id}")
        print(f"    - Имя: {first_name} {last_name}")
        print(f"    - Юзернейм: @{username}")
        print(f"    - Телефон: {phone}")

        # Целевой файл сессии
        target_session_name = f"account_{user_id}.session"
        target_session_path = os.path.join(SESSIONS_DIR, target_session_name)

        if isinstance(session_target, str) and os.path.isfile(session_target):
            if os.path.abspath(session_target) != os.path.abspath(target_session_path):
                shutil.copy2(session_target, target_session_path)
        else:
            # Если это StringSession или объект, сохраняем в файл
            # herokutl сохраняет файл автоматически если передать путь
            pass

        # Резервная копия
        backup_path = os.path.join(BACKUP_DIR, f"{user_id}_{tag}.session")
        if os.path.isfile(target_session_path):
            shutil.copy2(target_session_path, backup_path)
            print(f"[+] Резервная копия создана: {backup_path}")

        # Обновляем реестр
        registry = {"accounts": []}
        if os.path.isfile(REGISTRY_PATH):
            try:
                with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
            except Exception:
                pass

        accounts = registry.get("accounts", [])
        # Обновляем или добавляем
        existing = [acc for acc in accounts if acc.get("id") == user_id]
        if not existing:
            accounts.append({
                "id": user_id,
                "tag": tag,
                "first_name": first_name,
                "username": username,
                "session_file": f"sessions/{target_session_name}",
                "has_sim": has_sim,
                "status": "ready",
                "note": note
            })
        else:
            existing[0]["tag"] = tag
            existing[0]["first_name"] = first_name
            existing[0]["username"] = username
            existing[0]["has_sim"] = has_sim
            existing[0]["status"] = "ready"
            existing[0]["note"] = note

        registry["accounts"] = accounts
        with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

        print(f"[+] Запись в реестре обновлена: {REGISTRY_PATH}")
        return True
    finally:
        await client.disconnect()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python3 import_session.py <путь_к_session_файлу_или_StringSession> [тег] [has_sim: true/false] [заметка]")
        sys.exit(1)

    sess_arg = sys.argv[1]
    acc_tag = sys.argv[2] if len(sys.argv) > 2 else "main_account"
    sim_flag = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else True
    acc_note = sys.argv[4] if len(sys.argv) > 4 else "Основной аккаунт"

    asyncio.run(verify_and_register(sess_arg, acc_tag, sim_flag, acc_note))
