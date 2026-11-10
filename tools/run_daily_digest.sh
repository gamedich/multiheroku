#!/usr/bin/env bash
set -e
export SYSTEMD_PAGER=cat
export XDG_RUNTIME_DIR="/run/user/$(id -u)"

VENV_PYTHON="/home/botuser/accounts/main/.venv/bin/python3"
SCRIPT_PATH="/home/botuser/accounts/main/tools/twinks_deep_scout_digest.py"

echo "🚀 Запуск глубокой мультиаккаунтной разведки и сборки дайджеста..."
$VENV_PYTHON $SCRIPT_PATH

echo "🔍 Проверка свежих ключей и релизов Antigravity в чате Nova..."
$VENV_PYTHON "/home/botuser/accounts/main/tools/watch_nova_antigravity.py"

echo "✅ Дайджест и проверка обновлений успешно завершены!"
