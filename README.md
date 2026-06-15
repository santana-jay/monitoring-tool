# monitoring-tool

A Django + Celery system-monitoring and support-ticketing platform. It collects
host metrics (CPU, memory, etc.), tracks support tickets with categories,
priorities and assignees, and exposes analytics, notifications, an admin
interface, and a REST API.

## Apps

- `apps.core` — tickets, categories, monitoring systems/metrics models, REST API
- `apps.collectors` — host metric collection (`psutil`, Celery tasks)
- `apps.analytics` — analytics over collected metrics
- `apps.notifications` — notifications

## Requirements

- Python 3.11+
- The dependencies in [`requirements.txt`](requirements.txt) (Django, DRF,
  Channels, Celery, Redis, etc.)

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Related project: Meeting Co-pilot

The **Background Meeting Co-pilot** previously lived in this repository under
`meeting-copilot/`. It is a separate, standalone application and now has its own
repository: **https://github.com/santana-jay/meeting-copilot**.

If you are performing the split, see [`MIGRATION.md`](MIGRATION.md) for the exact
steps to move that directory (with history) into the new repo.