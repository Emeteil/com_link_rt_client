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
