# Welcome Moscow — компоненты платформы

Репозиторий содержит исходники программ для будущего стенда в виде Git-подмодулей:

| Программа | Каталог | Назначение |
| --- | --- | --- |
| [EspoCRM](https://github.com/espocrm/espocrm) | programs/espocrm | CRM, гости, квартиры, собственники и брони |
| [Chatwoot](https://github.com/chatwoot/chatwoot) | programs/chatwoot | Переписка гостей и операторов |
| [LangGraph](https://github.com/langchain-ai/langgraph) | programs/langgraph | Библиотека для разработки ИИ-консьержа |
| [Apache Superset](https://github.com/apache/superset) | programs/superset | Аналитика и отчёты |
| [pgvector](https://github.com/pgvector/pgvector) | programs/pgvector | Поиск по смыслу в PostgreSQL |
| [Celery](https://github.com/celery/celery) | programs/celery | Очереди фоновых задач |
| [Keycloak](https://github.com/keycloak/keycloak) | programs/keycloak | Вход пользователей и роли |
| [LiveKit Agents](https://github.com/livekit/agents) | programs/livekit-agents | Основа голосового помощника |
| [Dify](https://github.com/langgenius/dify) | programs/dify | Альтернативная визуальная платформа ИИ |
| [n8n](https://github.com/n8n-io/n8n) | programs/n8n | Вспомогательная автоматизация |
| [QloApps](https://github.com/Qloapps/QloApps) | programs/qloapps | Альтернативная система управления размещением |
| [ERPNext](https://github.com/frappe/erpnext) | programs/erpnext | Возможная основа корпоративного учёта |

Каждый подмодуль закреплён на конкретном коммите. Лицензии находятся в исходниках соответствующего проекта. Наличие исходников не означает, что приложения установлены или запущены.

Dify и n8n имеют специальные условия лицензирования; изучите лицензии перед использованием. Альтернативы сохранены для сравнения: установка всех компонентов одновременно не требуется. Скачанные коммиты не являются утверждённым набором производственных релизов; перед развёртыванием необходимо выбрать совместимые стабильные версии.

Для получения репозитория вместе с программами:

```sh
git clone --recurse-submodules <адрес-репозитория-welcome>
```

Если репозиторий уже скачан:

```sh
git submodule update --init --recursive
```

## Установка

- EspoCRM: https://docs.espocrm.com/administration/docker/installation/
- Chatwoot: https://developers.chatwoot.com/self-hosted/deployment/docker
- LangGraph: Python-библиотека, устанавливаемая в сервис консьержа; исходники находятся в programs/langgraph.
- Superset: https://superset.apache.org/admin-docs/installation/docker-compose/

Для пилота предполагается Linux-сервер с Docker. Потребуются настройка, базы данных, секреты и адреса приложений. Сервер и модель ИИ оплачиваются отдельно.

## Наш коннектор

Коннектор RealtyCalendar → EspoCRM и консьерж с Chatwoot требуют отдельной разработки. Готовой программы коннектора в этом репозитории пока нет. RealtyCalendar — внешний сервис; его исходники не предоставлены.

План интеграции находится в docs/INTEGRATION.md.

Подробная последовательность разработки и тестирования: [руководство для новичка](docs/IMPLEMENTATION_GUIDE_RU.md).

## Особенности скачивания на Windows

Для Keycloak и n8n локально включена поддержка длинных путей Git. QloApps содержит путь с точкой в конце имени каталога, несовместимый с обычной распаковкой Windows. Каталог themes/hotel-reservation-theme исключён из локальной рабочей копии QloApps; все его файлы сохранены в Git и в полном архиве qloapps-complete-source.tar рядом с README. Архив не добавлен в Git, поскольку дублирует исходники подмодуля. Полную рабочую копию QloApps следует получать на Linux. Файлы исходного проекта не изменялись.
