import asyncio
import os
import sys
import json
import shutil
from herokutl import TelegramClient
from herokutl.errors import SessionPasswordNeededError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
BACKUP_DIR = "/home/botuser/backups/sessions"
AUTH_STATE_FILE = os.path.join(BASE_DIR, "tools", ".auth_state.json")
REGISTRY_PATH = os.path.join(BASE_DIR, "tools", "accounts_registry.json")
TEMP_SESSION = os.path.join(SESSIONS_DIR, "temp_auth_session")

DEFAULT_API_ID = 14052957
DEFAULT_API_HASH = 'ad8d7e59ecd6d4c8c2b6119952b8aec4'

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

async def send_code(phone: str, api_id: int = None, api_hash: str = None):
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone

    api_id = int(api_id) if api_id else DEFAULT_API_ID
    api_hash = str(api_hash) if api_hash else DEFAULT_API_HASH

    for ext in ["", ".session", ".session-journal"]:
        p = f"{TEMP_SESSION}{ext}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    print(f"[*] Отправка кода авторизации на номер {phone[:4]}***{phone[-2:]} через прокси (api_id={api_id})...", flush=True)
    client = TelegramClient(TEMP_SESSION, api_id, api_hash, proxy=('http', '127.0.0.1', 8889))
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        state = {
            "phone": phone,
            "api_id": api_id,
            "api_hash": api_hash,
            "phone_code_hash": sent.phone_code_hash
        }
        with open(AUTH_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        print(f"[+] Код успешно отправлен! Проверь приложение Telegram (или СМС).", flush=True)
        print(f"[*] phone_code_hash получен.", flush=True)
    except Exception as e:
        print(f"[!] Ошибка отправки кода: {e}", flush=True)
    finally:
        await client.disconnect()

async def sign_in(code: str, password: str = None, tag: str = "main_account", note: str = "Основной аккаунт"):
    if not os.path.exists(AUTH_STATE_FILE):
        print("[!] Ошибка: Нет активного запроса авторизации. Сначала вызови send_code.", flush=True)
        return

    with open(AUTH_STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    phone = state["phone"]
    api_id = state.get("api_id", DEFAULT_API_ID)
    api_hash = state.get("api_hash", DEFAULT_API_HASH)
    phone_code_hash = state["phone_code_hash"]
    code = str(code).strip()

    print(f"[*] Подключение к Telegram для входа {phone[:4]}***{phone[-2:]}...", flush=True)
    client = TelegramClient(TEMP_SESSION, api_id, api_hash, proxy=('http', '127.0.0.1', 8889))
    await client.connect()
    try:
        try:
            print(f"[*] Проверка кода подтверждения...", flush=True)
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            if not password:
                print("[!] ТРЕБУЕТСЯ 2FA ПАРОЛЬ (Облачный пароль)!", flush=True)
                return
            print(f"[*] Ввод 2FA пароля...", flush=True)
            await client.sign_in(password=password)

        me = await client.get_me()
        user_id = me.id
        first_name = me.first_name or ""
        last_name = me.last_name or ""
        username = me.username or "без юзернейма"

        print(f"[+] ВХОД УСПЕШЕН!", flush=True)
        print(f"    - ID: {user_id}", flush=True)
        print(f"    - Имя: {first_name} {last_name}", flush=True)
        print(f"    - Юзернейм: @{username}", flush=True)

        final_session_name = f"account_{user_id}.session"
        final_session_path = os.path.join(SESSIONS_DIR, final_session_name)
        temp_file = f"{TEMP_SESSION}.session"

        if os.path.exists(temp_file):
            shutil.copy2(temp_file, final_session_path)
            backup_file = os.path.join(BACKUP_DIR, f"{user_id}_{tag}.session")
            shutil.copy2(temp_file, backup_file)
            print(f"[+] Сессия сохранена: {final_session_path}", flush=True)
            print(f"[+] Резервная копия создана: {backup_file}", flush=True)
            try:
                os.remove(temp_file)
            except Exception:
                pass

        if os.path.exists(AUTH_STATE_FILE):
            os.remove(AUTH_STATE_FILE)

        registry = {"accounts": []}
        if os.path.exists(REGISTRY_PATH):
            try:
                with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
            except Exception:
                pass

        accounts = registry.get("accounts", [])
        existing = [acc for acc in accounts if acc.get("id") == user_id]
        if not existing:
            accounts.append({
                "id": user_id,
                "tag": tag,
                "first_name": first_name,
                "username": username,
                "session_file": f"sessions/{final_session_name}",
                "api_id": api_id,
                "api_hash": api_hash,
                "has_sim": True,
                "status": "ready",
                "note": note
            })
        else:
            existing[0]["tag"] = tag
            existing[0]["first_name"] = first_name
            existing[0]["username"] = username
            existing[0]["api_id"] = api_id
            existing[0]["api_hash"] = api_hash
            existing[0]["status"] = "ready"
            existing[0]["note"] = note

        registry["accounts"] = accounts
        with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

        print(f"[+] Аккаунт добавлен в реестр: {REGISTRY_PATH}", flush=True)

    except Exception as e:
        print(f"[!] Ошибка авторизации: {e}", flush=True)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python3 auth_flow.py send_code <PHONE> [API_ID] [API_HASH]")
        print("  python3 auth_flow.py sign_in <CODE> [2FA_PASSWORD] [tag] [note]")
        sys.exit(1)

    action = sys.argv[1].lower()
    if action == "send_code":
        if len(sys.argv) < 3:
            print("Укажи номер телефона: python3 auth_flow.py send_code +79991234567 [API_ID] [API_HASH]")
            sys.exit(1)
        p = sys.argv[2]
        aid = sys.argv[3] if len(sys.argv) > 3 else None
        ahash = sys.argv[4] if len(sys.argv) > 4 else None
        asyncio.run(send_code(p, aid, ahash))
    elif action == "sign_in":
        if len(sys.argv) < 3:
            print("Укажи код: python3 auth_flow.py sign_in 12345 [PASSWORD]")
            sys.exit(1)
        code_arg = sys.argv[2]
        pwd_arg = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "none" else None
        tag_arg = sys.argv[4] if len(sys.argv) > 4 else "main_account"
        note_arg = sys.argv[5] if len(sys.argv) > 5 else "Основной аккаунт"
        asyncio.run(sign_in(code_arg, pwd_arg, tag_arg, note_arg))
