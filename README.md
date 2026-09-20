# com_link_rt_client

Библиотека Python - клиент для связи с робототехническим оборудованием по протоколу COM-LINK-RT через последовательный порт.

## Использование

### Простой пример с командами
```python
from com_link_rt import ComLinkConnection, PingCommand, VersionCommand

with ComLinkConnection('COM7') as conn:
    # Проверка соединения
    ping = PingCommand(conn)
    if ping.execute():
        print("Соединение установлено!")

    # Получение версии прошивки
    version = VersionCommand(conn)
    info = version.execute()
    print(f"Прошивка собрана: {info['build_date']} {info['build_time']}")
```

### Пример с подпиской на данные
```python
from com_link_rt import ComLinkConnection, MillisCommand

def on_millis_data(data):
    print(f"Аптайм устройства: {data} мс")

with ComLinkConnection('COM7') as conn:
    millis = MillisCommand(conn)

    # Подписка на данные аптайма
    millis.subscribe(on_millis_data)

    # Поддержание соединения
    import time
    time.sleep(10)
```

## Тесты

```bash
pip install -r requirements-dev.txt
pytest
```

Тесты не требуют подключённого устройства. Протокол лежит в `tests/test_core/`, команды в `tests/test_commands/` (по файлу на команду), общие вспомогательные классы в `tests/common/`.

Новый тест команды: создайте `tests/test_commands/test_<name>.py`, возьмите `FakeConnection` из `common.fake_connection` и передайте ему ответ `(тип_пакета, payload)`:

```python
from common.fake_connection import FakeConnection
from core.commands.ping import PingCommand

def test_ping_returns_latency():
    conn = FakeConnection(response=(0x02, b""))
    assert PingCommand(conn).execute() >= 0
```

Имена тестовых файлов должны быть уникальными во всём `tests/`.
