# Telegram Panel

Источник: https://github.com/ItsOrv/Telegram-Panel
Зафиксирован commit f8a4ea1cd2ab4f57f603463e1127d0fb44fa71e5. Лицензия MIT сохранена в LICENSE.

Локальная проверка: 481 тест прошёл (без test_network.py).

Размещение на сервере: ~/telegram-panel, отдельное Python-окружение .venv.

Для настройки скопируйте env.example в .env, ограничьте доступ командой chmod 600 .env и заполните API_ID, API_HASH, BOT_TOKEN, ADMIN_ID. Не добавляйте .env и файлы сессий в Git.

Запуск: .venv/bin/python main.py. Интерфейс управления — Telegram-бот либо interactive_cli.py; веб-панели у проекта нет.

Без учётных данных бот не запускается в рабочем режиме. Для дальнейшей настройки используйте отдельный тестовый аккаунт и контролируемый чат.
