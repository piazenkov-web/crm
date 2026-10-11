# IA Welcome to Moscow v4.0 — комплект разработчика

Начните с TECHNICAL_SPEC_v4.0.md. MASTER_PROMPT_v4.0.md — текст для системного слоя. TOOL_CATALOG.md — обзор 82 tools; contracts/tools/ — отдельные полные JSON Schema каждого инструмента. db/001_schema.sql — справочная начальная схема PostgreSQL, применять через проверенные миграции. contracts/openapi.json — контракт внутреннего сервиса, не API RealtyCalendar.

## Что готово

- Согласованная проектная архитектура и ограничения интеграций.
- 82 спецификации input/output, общие модели данных, trusted context, внутренние события и минимальный RC webhook boundary contract.
- Промпт и 39 справочных таблиц с tenant isolation.
- Контрактный FastAPI каркас и тесты форматов/границ данных.

## Что требуется реализовать

Policy Engine, identity linking, object authorization, DB repositories, transactional confirmations/operations, Celery workers/scheduler, provider adapters, durable inbox/outbox, live booking/payment workflows, кабинет, UI и production infrastructure. Реальные интеграции в каркасе выключены. Все вызовы валидного tool возвращают CAPABILITY_DISABLED, не имитируя бизнес-операцию. Контрактный каркас не обращается к PostgreSQL/Redis и не исполняет DDL.

## Запуск каркаса

Python 3.12, из корня комплекта:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
export HARNESS_SERVICE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Токен хранить локально, не добавлять в репозиторий. HTTP endpoint внутреннего каркаса требует Bearer token. Не публикуйте этот каркас как гостевой backend. Static service token не заменяет production identity/permissions; значения tenant/actor никогда не брать из гостевого HTTP body.

Контейнер собирается из корня: `docker build -f app/Dockerfile -t ia-v4-contracts .`. PostgreSQL с pgvector и Redis для полной системы разворачиваются отдельно после реализации сервисов; полный production compose здесь не симулируется.

## Передача сотрудникам

Модули: gateway/identity; ai-orchestrator; catalog/booking; payments; operations/support; concierge; retention/CRM; corporate; platform/analytics. Владельцы модулей реализуют общий contracts, не меняя семантику статусов локально. Любое несовместимое изменение оформлять как schema migration + contract version + ADR + integration tests. Раздельный доступ сотрудников задаётся инфраструктурой репозиториев/CI, не промптом.

Заказчику полезно читать MASTER_PROMPT и TECHNICAL_SPEC. Разработчикам дополнительно нужны JSON/SQL/каркас. Обязательные приёмочные сценарии перечислены в спецификации; контрактные тесты в архиве не доказывают работу vendor adapters.
