#!/usr/bin/env bash
# Идемпотентный скрипт создания лейблов GitHub.
# Запуск: bash scripts/setup-labels.sh
#
# Требует gh CLI с авторизацией: gh auth login

set -e

if ! command -v gh &> /dev/null; then
  echo "❌ gh CLI не установлен. Установите: https://cli.github.com/"
  exit 1
fi

create_label() {
  local name="$1"
  local color="$2"
  local description="$3"
  if gh label create "$name" --color "$color" --description "$description" 2>/dev/null; then
    echo "✅ создан: $name"
  else
    gh label edit "$name" --color "$color" --description "$description" 2>/dev/null && echo "🔄 обновлён: $name" || echo "⚠️  пропущен: $name"
  fi
}

echo "📌 Создаю лейблы по типу..."
create_label "тип: баг" "d73a4a" "Что-то работает не так"
create_label "тип: фича" "0e8a16" "Новая функциональность"
create_label "тип: рефакторинг" "1d76db" "Улучшение кода без смены поведения"
create_label "тип: документация" "0075ca" "Изменения в документации"
create_label "тип: тех-долг" "5319e7" "Технический долг"
create_label "тип: инфра" "bfd4f2" "Инфраструктура и DevOps"
create_label "тип: вопрос" "d876e3" "Нужно прояснение"
create_label "тип: эпик" "000000" "Большой блок работы"
create_label "тип: безопасность" "ee0701" "Безопасность"

echo "🔥 Создаю лейблы по приоритету..."
create_label "приоритет: P0" "b60205" "Критический, блокирует релиз"
create_label "приоритет: P1" "d93f0b" "Высокий"
create_label "приоритет: P2" "fbca04" "Средний"
create_label "приоритет: P3" "c5def5" "Низкий"

echo "🚦 Создаю лейблы по статусу..."
create_label "статус: бэклог" "ededed" "В очереди"
create_label "статус: discovery" "c2e0c6" "Требует проработки"
create_label "статус: готово к работе" "0e8a16" "Можно брать"
create_label "статус: в работе" "1d76db" "В разработке"
create_label "статус: на ревью" "fbca04" "На код-ревью"
create_label "статус: готово" "00ff00" "Завершено"
create_label "статус: заблокировано" "d73a4a" "Заблокировано"
create_label "статус: нужна инфа" "ff9f1c" "Не хватает данных"
create_label "статус: stale" "cccccc" "Без активности >60д"

echo "👥 Создаю лейблы для исполнителей..."
create_label "для: claude-code" "8a2be2" "Для Claude Code"
create_label "для: claude-design" "ff69b4" "Для Claude Design"
create_label "для: вики" "00ced1" "Для DevOps-агента Вики"
create_label "для: human" "ffffff" "Только для человека"
create_label "good first issue" "7057ff" "Хорошая первая задача"

echo "📏 Создаю лейблы для размеров PR..."
create_label "size: XS" "00ff00" "Менее 10 строк"
create_label "size: S" "7fff00" "10-100 строк"
create_label "size: M" "ffff00" "100-500 строк"
create_label "size: L" "ff7f00" "500-1000 строк"
create_label "size: XL" "ff0000" "Более 1000 строк"

echo "🏷  Создаю спецлейблы..."
create_label "breaking-change" "ff0000" "Ломает обратную совместимость"
create_label "requires-migration" "fbca04" "Требует миграции данных"
create_label "requires-docs" "0075ca" "Требует обновления документации"

echo ""
echo "✨ Готово. Всего лейблов:"
gh label list --limit 100 | wc -l
