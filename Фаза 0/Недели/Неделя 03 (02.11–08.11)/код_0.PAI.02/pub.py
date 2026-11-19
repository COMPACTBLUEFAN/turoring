import sys
import time
import paho.mqtt.client as mqtt

# Поддержка флага --retain для проверки запоминания сообщений брокером
use_retain = "--retain" in sys.argv

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pub_demo")
client.connect("127.0.0.1", 1883, keepalive=60)

# Три тестовых сообщения из условий эксперимента (Задание 3):
messages = [
    ("plant/line1/temp", "45"),
    ("plant/line1/motor/temp", "78"),
    ("plant/line1/cmd", "stop"),
]

print(f"Отправка сообщений в брокер 127.0.0.1:1883 (retain={use_retain})...", flush=True)
for topic, payload in messages:
    print(f"  [ОТПРАВЛЕНО] {topic} -> {payload}", flush=True)
    client.publish(topic, payload, qos=1, retain=use_retain)
    time.sleep(0.2)

# Пауза перед отключением, чтобы клиент успел передать пакеты в сокет
time.sleep(0.5)
client.disconnect()
print("Готово. Все сообщения отправлены.", flush=True)
