# tools/dashboard

Интерактивный дашборд состояния проекта. React + Vite + Tailwind.

## Статус

🚧 **TODO / Скаффолд** — в этом PR (`chore/repo-setup`) положен только описательный README + `scripts/dashboard-fetch.mjs` для сбора данных. Полный React-проект будет добавлен в отдельном PR.

## Планируемые views

- **RoadmapView** — quarterly view, эпики на таймлайне.
- **BacklogView** — список issues с фильтрами по лейблам.
- **BoardView** — kanban по статусам Project v2.
- **EpicsView** — иерархия epic → issue → sub-issue с прогрессом.
- **DependencyView** — граф зависимостей (Mermaid / d3).

## Источник данных

`/scripts/dashboard-fetch.mjs` через GitHub GraphQL собирает:
- Issues + custom labels.
- Project v2 items + кастомные поля.
- Sub-issues hierarchy.
- PR статусы.

Сохраняет в `tools/dashboard/data/snapshot.json`.

## Workflow

`.github/workflows/dashboard-sync.yml` запускает fetch + build + публикует в GitHub Pages по cron'у и на `push` в main.

## Roadmap

- [ ] React + Vite + Tailwind скаффолд
- [ ] RoadmapView
- [ ] BacklogView
- [ ] BoardView
- [ ] EpicsView
- [ ] DependencyView
- [ ] CSV/JSON export
- [ ] Authentication (если перейдём на private)
