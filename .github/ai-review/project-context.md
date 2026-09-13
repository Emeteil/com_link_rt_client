# Project context
`com_link_rt_client` — клиентская Python-библиотека протокола COM-LINK-RT: собирает/разбирает бинарные пакеты и общается по Serial со прошивкой STM32. Подключается как сабмодуль в `izbushka-web-core` (путь `com_link_rt`, ветка `robot`).

## What to review and what to ignore
Ревьюить: `core/` (логика протокола, сборка/разбор пакетов), `exceptions.py`, `setup.py`, `requirements.txt`.
Игнорировать: `.github/`, CI-конфиги.
Если в диффе нет ревьюабельного кода — так и напиши в summary, не выдумывай замечания.

## Always read the PR description and comments
Перед ревью прочитай PR DESCRIPTION из PR / GIT CONTEXT и комментарии в pr-comments/others/. Не поднимай повторно то, что там уже решено или объяснено; объяснение снимает придирку, но не отменяет реальный баг.

## Stack
Python, `pyserial` для UART-связи, упаковка через `setup.py`/`requirements.txt` как устанавливаемый пакет.

## Code style
Библиотечный код: чёткие исключения (`exceptions.py`) вместо тихих ошибок парсинга, явная валидация длины/CRC пакета перед использованием payload. Придерживайся общего для проекта стиля PEP8 (в родственном `izbushka-web-core` CI использует flake8 `--max-line-length=120`).

## Architecture and patterns
- Реализация протокола COM-LINK-RT v2 на стороне клиента (SBC): формирование заголовка 11 байт (`0xAA 0x55 version packetType serviceBits packetId dataLength crc`), вычисление/проверка CRC-16 CCITT-FALSE, работа с `serviceBits` (subscribe/unsubscribe/keep-alive).
- Отправка команд `PING`, `MILLIS`, `DISTANCE`, `GYRO`, `SERVO`, `MOTORS` и разбор ответов от STM32.

## Dependencies on other parts of the system
- Является клиентом для прошивки [COM-LINK-RT](https://github.com/Emeteil/COM-LINK-RT) (STM32) по USB-Serial 115200 бод — формат пакета и `packetType` должны совпадать побайтово.
- Используется как сабмодуль в [izbushka-web-core](https://github.com/Emeteil/izbushka-web-core) (`ComLinkSubscriber` в `transport/bus.py`), приоритет 10 в `TransportBus`.

## Review checklist
- Изменение формата пакета, порядка полей, расчёта CRC или значений `packetType`/`serviceBits` — должно быть согласовано с прошивкой [COM-LINK-RT](https://github.com/Emeteil/COM-LINK-RT); явно указать на необходимость синхронизации.
- Новая зависимость в коде без добавления в `requirements.txt`/`setup.py`, либо наоборот — неиспользуемая зависимость осталась в манифесте.
- Отсутствие проверки CRC/длины перед использованием входящих данных — риск чтения мусора при повреждённом пакете.
- Изменение публичного API библиотеки (сигнатуры методов) без учёта, что вызывающий код находится в отдельном репозитории `izbushka-web-core` — ломающие изменения нужно явно отметить.
- Блокирующие таймауты Serial-чтения, которые могут подвесить вызывающий асинхронный код web-core.
