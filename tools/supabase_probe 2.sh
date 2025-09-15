#!/usr/bin/env bash
set -euo pipefail

# Простая утилита для диагностики Supabase по задаче Pyrus.
# Использование:
#   bash tools/supabase_probe.sh <TASK_ID>
# Требуются переменные окружения:
#   SUPABASE_URL, SUPABASE_KEY

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <TASK_ID>" >&2
  exit 1
fi

TASK_ID="$1"

if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_KEY:-}" ]]; then
  echo "❌ SUPABASE_URL или SUPABASE_KEY не заданы" >&2
  exit 2
fi

AUTH_HEADERS=(
  -H "apikey: $SUPABASE_KEY"
  -H "Authorization: Bearer $SUPABASE_KEY"
)

echo "--- pending_notifications (task_id=$TASK_ID)";
curl -s "${AUTH_HEADERS[@]}" \
  "$SUPABASE_URL/rest/v1/pending_notifications?select=*&task_id=eq.$TASK_ID" | jq . || true

echo "\n--- logs by task_id (JSON contains)";
curl -s "${AUTH_HEADERS[@]}" \
  "$SUPABASE_URL/rest/v1/logs?select=event,ts,payload&payload=cs.%7B%22task_id%22%3A$TASK_ID%7D" | jq . || true

echo "\n--- error logs only (notify_failed|notify_error|notify_failed_preformatted)";
curl -s "${AUTH_HEADERS[@]}" \
  "$SUPABASE_URL/rest/v1/logs?select=event,ts,payload&event=in.(notify_failed,notify_error,notify_failed_preformatted)&payload=cs.%7B%22task_id%22%3A$TASK_ID%7D" | jq . || true

echo "\nDone."


