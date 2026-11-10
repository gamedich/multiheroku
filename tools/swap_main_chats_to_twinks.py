import asyncio
import json
import logging
import os
import random
from herokutl import TelegramClient, errors
from herokutl.tl.types import Channel, Chat, User
from herokutl.tl.functions.channels import JoinChannelRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("swap_ops")

PROXY = ('http', '127.0.0.1', 8889)
OWNER_ID = 7657422832

# Доступные твинки для подхвата чатов:
TWINKS = [
    {
        "tag": "Twink-3",
        "username": "Darksaltiu",
        "session": "/home/botuser/accounts/twink-3/sessions/account_7999839708",
        "api_id": 4883642,
        "api_hash": "f3975ed9c1f919ee1fe62828e88ace55",
    },
    {
        "tag": "Twink-4",
        "username": "Tralaladark",
        "session": "/home/botuser/accounts/twink-4/sessions/account_8501573051",
        "api_id": 4883642,
        "api_hash": "f3975ed9c1f919ee1fe62828e88ace55",
    },
    {
        "tag": "Twink-2",
        "username": "fast_ilya",
        "session": "/home/botuser/accounts/twink-2-nosim/sessions/account_5189061964",
        "api_id": 6378328,
        "api_hash": "3922dcbe446da84937188b7cb5c1328f",
    }
]

WHITELIST_KEYWORDS = [
    "уэт", "uet", "транспорт", "троллей", "трамва", "чнту",
    "darksold", "депо", "штаб", "guzban", "botuser", "fast_ilya",
    "its_darksold1", "флейм", "flame", "leomatch", "bibinto"
]

def is_whitelisted(name: str, username: str) -> bool:
    name_l = (name or "").lower()
    uname_l = (username or "").lower()
    return any(kw in name_l or kw in uname_l for kw in WHITELIST_KEYWORDS)

async def try_solve_captcha(client, entity, me):
    try:
        await asyncio.sleep(2)
        async for msg in client.iter_messages(entity, limit=5):
            if msg.buttons:
                for row in msg.buttons:
                    for button in row:
                        btn_text = (button.text or "").lower()
                        if any(k in btn_text for k in ["человек", "human", "пройти", "подтверд", "нажми", "click", "verify", "войти", "✅", "👌", "🟢"]):
                            logger.info(f"Найдена капча-кнопка: '{button.text}', нажимаем...")
                            try:
                                await button.click()
                                await asyncio.sleep(1.5)
                                return True
                            except Exception as be:
                                logger.warning(f"Ошибка клика по капче: {be}")
    except Exception as e:
        logger.warning(f"Ошибка проверки капчи: {e}")
    return False

async def main():
    logger.info("Запуск анализа чатов основы для передачи твинкам...")
    main_chats_path = "/home/botuser/dev_modules/main_chats_list.json"
    if not os.path.exists(main_chats_path):
        logger.error(f"Файл {main_chats_path} не найден!")
        return

    with open(main_chats_path, "r", encoding="utf-8") as f:
        main_chats = json.load(f)

    # Отбираем кандидатов:
    # 1. Группы с огромным количеством непрочитанных (не читаются основой)
    # 2. Неактивные каналы (days_inactive >= 20)
    # Строго исключая whitelist!
    candidates = []
    for c in main_chats:
        uname = c.get("username")
        title = c.get("title", "")
        if not uname:
            continue  # Без юзернейма твинк не сможет безопасно войти по ссылке
        if is_whitelisted(title, uname):
            continue

        unread = c.get("unread", 0)
        days = c.get("days_inactive", 0)
        is_grp = c.get("is_group", False)

        # Критерий: группы с непрочитанными > 1000 или каналы с неактивностью > 20 дней
        if (is_grp and unread >= 1000) or (not is_grp and days >= 20):
            candidates.append(c)

    logger.info(f"Найдено кандидатов для передачи твинкам: {len(candidates)}")
    for cand in candidates[:10]:
        logger.info(f"• {cand['title']} ({cand['username']}) | unread={cand.get('unread')} | days={cand.get('days_inactive')}")

    if not candidates:
        logger.info("Кандидатов для передачи не найдено.")
        return

    # Берем топ-5 самых забитых/неактивных чатов для аккуратной передачи
    batch = candidates[:5]
    successful_swaps = []
    failed_swaps = []

    # Распределяем по твинкам
    twink_idx = 0
    for chat in batch:
        twink_cfg = TWINKS[twink_idx % len(TWINKS)]
        twink_idx += 1
        tag = twink_cfg["tag"]
        uname = chat["username"]
        title = chat["title"]

        logger.info(f"\n--- Пробуем пересадить '{title}' ({uname}) на {tag} ---")
        client = TelegramClient(twink_cfg["session"], twink_cfg["api_id"], twink_cfg["api_hash"], proxy=PROXY)
        joined_ok = False
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logger.error(f"[{tag}] Не авторизован!")
                failed_swaps.append({"title": title, "username": uname, "reason": "twink unauthorized"})
                continue

            me = await client.get_me()
            # Плавная задержка
            delay = random.uniform(3.5, 6.0)
            logger.info(f"[{tag}] Антифрод-пауза {delay:.1f}с перед входом...")
            await asyncio.sleep(delay)

            # Пробуем войти
            try:
                entity = await client.get_entity(uname)
                await client(JoinChannelRequest(entity))
                joined_ok = True
                logger.info(f"[{tag}] Успешно вошел в {uname}!")
                # Проверка капчи
                await try_solve_captcha(client, entity, me)
            except errors.UserAlreadyParticipantError:
                joined_ok = True
                logger.info(f"[{tag}] Уже участник {uname}")
            except Exception as je:
                logger.warning(f"[{tag}] Не удалось войти в {uname}: {je}")
                joined_ok = False

            if joined_ok:
                successful_swaps.append({
                    "id": chat["id"],
                    "title": title,
                    "username": uname,
                    "taken_by": tag
                })
            else:
                failed_swaps.append({
                    "title": title,
                    "username": uname,
                    "reason": "вход закрыт или требуется ручное одобрение — ОСНОВА ОСТАЛАСЬ!"
                })

        except Exception as e:
            logger.error(f"Ошибка при работе с {tag}: {e}")
            failed_swaps.append({"title": title, "username": uname, "reason": str(e)})
        finally:
            await client.disconnect()

    logger.info(f"\nИтоги: Успешно подхвачено твинками: {len(successful_swaps)}, Оставлено на основе: {len(failed_swaps)}")

    # Если есть успешные переносы — отправляем их в очередь выхода для основы
    if successful_swaps:
        queue_path = "/home/botuser/dev_modules/leave_queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(successful_swaps, f, ensure_ascii=False, indent=2)
        logger.info(f"Очередь выхода для основы сформирована в {queue_path} ({len(successful_swaps)} чатов).")
        logger.info("DialogSorterMod на основе подхватит её и выйдет без блокировок в течение 10 секунд.")

    # Формируем отчет Создателю
    report_lines = [
        "🔄 <b>ОТЧЕТ ПО ПЕРЕНОСУ ЧАТОВ С ОСНОВЫ НА ТВИНКИ</b>\n",
        f"✅ <b>Успешно подхвачено твинками (основа выходит):</b> <code>{len(successful_swaps)}</code>"
    ]
    for s in successful_swaps:
        report_lines.append(f"• <b>{s['title']}</b> ({s['username']}) $\\rightarrow$ передан на <b>{s['taken_by']}</b>")

    if failed_swaps:
        report_lines.append(f"\n🛡️ <b>Не удалось зайти твинком (ОСНОВА ОСТАЛАСЬ НА МЕСТЕ):</b> <code>{len(failed_swaps)}</code>")
        for f in failed_swaps:
            report_lines.append(f"• <b>{f['title']}</b> ({f['username']}) — <i>{f['reason']}</i>")

    report_text = "\n".join(report_lines)

    # Отправляем Создателю через Twink-3
    report_sender = TWINKS[0]
    sender_cl = TelegramClient(report_sender["session"], report_sender["api_id"], report_sender["api_hash"], proxy=PROXY)
    try:
        await sender_cl.connect()
        if await sender_cl.is_user_authorized():
            await sender_cl.send_message(OWNER_ID, report_text, parse_mode="html")
            logger.info("Отчет успешно отправлен Создателю!")
    except Exception as e:
        logger.error(f"Ошибка отправки отчета: {e}")
    finally:
        await sender_cl.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
