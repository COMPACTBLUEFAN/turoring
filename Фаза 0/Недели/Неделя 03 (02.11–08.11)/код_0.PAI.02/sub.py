import sys
import paho.mqtt.client as mqtt

# Топик: можно передать первым аргументом (например, "plant/#"), по умолчанию — "plant/+/temp"
TOPIC = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "plant/+/temp"

def on_connect(client, userdata, connect_flags, reason_code, properties):
    # Строка для объяснения №2: почему подписка внутри on_connect?
    # При обрыве связи и автоматическом переподключении клиент заново подписывается на топики на брокере.
    print(f"Подключено к брокеру (reason_code: {reason_code})", flush=True)
    print(f"Оформлена подписка на топик: {TOPIC}", flush=True)
    client.subscribe(TOPIC, qos=1)

def on_message(client, userdata, msg):
    print(f"[ПОЛУЧЕНО] {msg.topic} -> {msg.payload.decode()}", flush=True)

# Строка для объяснения №1: CallbackAPIVersion.VERSION2
# В paho-mqtt 2.0+ обязательно явно указывать версию API коллбэков (защита от несовместимости сигнатур параметров).
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sub_demo")
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect("127.0.0.1", 1883, keepalive=60)
    print(f"Ожидание сообщений ({TOPIC})... Нажмите Ctrl+C для выхода.\n", flush=True)
    # Строка для объяснения №3: loop_forever()
    # Запускает блокирующий бесконечный цикл обработки сетевых событий (входящие пакеты, keepalive-пинги, автореконнект).
    client.loop_forever()
except KeyboardInterrupt:
    print("\nОстановка подписчика.", flush=True)
finally:
    client.disconnect()
