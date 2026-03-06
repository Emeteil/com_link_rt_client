# com_link_rt

Библиотека Python - клиент для связи с робототехническим оборудованием по протоколу COM-LINK-RT через последовательный порт.

## Использование

### Простой пример с командами
```python
from com_link_rt import ComLinkConnection, PingCommand, DistanceCommand

with ComLinkConnection('COM7') as conn:
    # Проверка соединения
    ping = PingCommand(conn)
    if ping.execute():
        print("Соединение установлено!")

    # Получение данных с датчика расстояния
    distance = DistanceCommand(conn)
    dist_cm = distance.execute()
    print(f"Расстояние: {dist_cm} см")
```

### Пример с подпиской на данные
```python
from com_link_rt import ComLinkConnection, GyroCommand

def on_gyro_data(data):
    accel = gyro.get_acceleration(data)
    rotation = gyro.get_rotation(data)
    temp = gyro.get_temperature(data)
    print(f"Ускорение: {accel}, Вращение: {rotation}, Температура: {temp:.1f}°C")

with ComLinkConnection('COM7') as conn:
    gyro = GyroCommand(conn)

    # Подписка на данные гироскопа
    gyro.subscribe(on_gyro_data, mode=GyroCommand.GYRO_CALIBRATED_FILTERED)

    # Поддержание соединения
    import time
    time.sleep(10)
```
