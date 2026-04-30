#!/usr/bin/env bash
# Создаёт GitHub Project v2 "Roadmap" с 12 кастомными полями.
# Запуск: bash scripts/setup-project.sh <OWNER> <REPO>
#
# OWNER может быть organization или user.
# Требует gh CLI с правами: project, repo, read:org

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: bash scripts/setup-project.sh <OWNER> <REPO>"
  exit 1
fi

OWNER="$1"
REPO="$2"
PROJECT_TITLE="Roadmap"

echo "🎯 Создаю Project '$PROJECT_TITLE' для $OWNER/$REPO..."

EXISTING=$(gh project list --owner "$OWNER" --format json --limit 50 2>/dev/null | jq -r ".projects[]? | select(.title==\"$PROJECT_TITLE\") | .number" || echo "")

if [ -n "$EXISTING" ]; then
  PROJECT_NUMBER="$EXISTING"
  echo "🔄 Project уже существует: #$PROJECT_NUMBER"
else
  PROJECT_NUMBER=$(gh project create --owner "$OWNER" --title "$PROJECT_TITLE" --format json | jq -r '.number')
  echo "✅ Создан Project #$PROJECT_NUMBER"
fi

PROJECT_ID=$(gh project view "$PROJECT_NUMBER" --owner "$OWNER" --format json | jq -r '.id')

echo "🔗 Привязываю репо $OWNER/$REPO к проекту..."
gh project link "$PROJECT_NUMBER" --owner "$OWNER" --repo "$OWNER/$REPO" 2>/dev/null || echo "  (уже привязан)"

create_single_select() {
  local name="$1"
  local options="$2"
  if gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json | jq -e ".fields[] | select(.name==\"$name\")" > /dev/null 2>&1; then
    echo "🔄 поле уже есть: $name"
    return
  fi
  gh project field-create "$PROJECT_NUMBER" --owner "$OWNER" \
    --name "$name" \
    --data-type SINGLE_SELECT \
    --single-select-options "$options" > /dev/null
  echo "✅ создано single-select: $name"
}

create_field() {
  local name="$1"
  local type="$2"
  if gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json | jq -e ".fields[] | select(.name==\"$name\")" > /dev/null 2>&1; then
    echo "🔄 поле уже есть: $name"
    return
  fi
  gh project field-create "$PROJECT_NUMBER" --owner "$OWNER" \
    --name "$name" \
    --data-type "$type" > /dev/null
  echo "✅ создано $type: $name"
}

echo ""
echo "📋 Создаю кастомные поля..."

create_single_select "Priority" "P0,P1,P2,P3"
create_single_select "Size" "XS,S,M,L,XL"
create_single_select "Batch" "v0.1.0,v0.2.0,v0.3.0,v1.0.0,без батча"
create_single_select "Epic" "EPIC-1,EPIC-2,EPIC-3,EPIC-4,EPIC-5,не относится"
create_single_select "Stream" "Платформа,Продукт,Инфра,AI,Команда"
create_single_select "Component" "web,mobile,api,db,devops,ui-kit,ai,integrations,другое"

create_field "Start date" "DATE"
create_field "Target date" "DATE"
create_field "Progress" "NUMBER"
create_field "Blocked by" "TEXT"

echo ""
echo "📅 Создаю Sprint iteration field (только через GraphQL)..."
echo "  ⚠️  ВНИМАНИЕ: gh CLI пока не поддерживает создание ITERATION полей."
echo "  Создайте поле Sprint вручную через UI Project'а:"
echo "  https://github.com/orgs/$OWNER/projects/$PROJECT_NUMBER"
echo ""
echo "  Или через GraphQL:"
cat <<EOF
  curl -X POST https://api.github.com/graphql \\
    -H "Authorization: Bearer \$GH_TOKEN" \\
    -d '{"query":"mutation { createProjectV2Field(input: { projectId: \"$PROJECT_ID\", dataType: ITERATION, name: \"Sprint\" }) { projectV2Field { ... on ProjectV2IterationField { id } } } }"}'
EOF

echo ""
echo "✨ Готово!"
echo ""
echo "📌 Следующие шаги (через UI Project'а):"
echo "1. Откройте проект: https://github.com/users/$OWNER/projects/$PROJECT_NUMBER"
echo "2. Settings → Workflows → включите:"
echo "   - Auto-add to project (для всех issues и PR этого репо)"
echo "   - Item closed → Status: Готово"
echo "   - Pull request merged → linked Issue: Готово"
echo "   - Auto-archive items (Status: Готово, >14 дней)"
echo ""
echo "📌 Запишите в GitHub Secrets:"
echo "   PROJECT_NUMBER=$PROJECT_NUMBER"
echo "   PROJECT_OWNER=$OWNER"
echo ""
echo "📌 Создайте PAT с правами repo + project + read:org и сохраните как PROJECT_TOKEN."
