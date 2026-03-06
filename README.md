# com_link_rt

Библиотека Python - клиент для связи с робототехническим оборудованием по протоколу COM-LINK-RT через последовательный порт.

## Использование

### Простой пример с командами
```python
from com_link_rt import ComLinkConnection, PingCommand, MillisCommand

with ComLinkConnection('COM7') as conn:
    # Проверка соединения
    ping = PingCommand(conn)
    ping_time = ping.execute()
    if ping_time is not None:
        print(f"Соединение установлено! Задержка: {ping_time:.1f} мс")
    else:
        print("Ошибка соединения!")

    # Получение времени работы микроконтроллера
    millis = MillisCommand(conn)
    time_ms = millis.execute()
    print(f"Время работы: {time_ms} мс")
```

### Пример с подпиской на данные
```python
from com_link_rt import ComLinkConnection, MillisCommand

def on_millis_data(time_ms):
    print(f"Текущее время микроконтроллера: {time_ms} мс")

with ComLinkConnection('COM7') as conn:
    millis = MillisCommand(conn)

    # Подписка на обновления времени
    millis.subscribe(on_millis_data)

    # Поддержание соединения
    import time
    time.sleep(10)
```
