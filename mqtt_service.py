"""
mqtt_service.py - MQTT клиент для сервера
"""
import paho.mqtt.client as mqtt
import json
import threading
import time
from flask import jsonify


class MQTTService:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.device_states = {}
        self.pending_commands = {}

        # Настройки из переменных окружения
        self.mqtt_host = "4fc91b0cfc8d474b9e791bae55b873f6.s1.eu.hivemq.cloud"
        self.mqtt_port = 8883
        self.mqtt_username = "Kirrius"  # Замените на ваши данные
        self.mqtt_password = "Yandex2019"  # Замените на ваши данные

        # Настройка SSL
        self.client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                            cert_reqs=mqtt.ssl.CERT_REQUIRED,
                            tls_version=mqtt.ssl.PROTOCOL_TLS)

        # Устанавливаем имя пользователя и пароль
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("MQTT подключен к HiveMQ Cloud")
            # Подписываемся на данные и статусы
            client.subscribe("plantcare/device/+/data")
            client.subscribe("plantcare/device/+/status")
            print("Подписан на топики: plantcare/device/+/data и plantcare/device/+/status")
        else:
            print(f"Ошибка подключения MQTT, код: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            print(f"MQTT получено: {topic} -> {payload}")

            # Разбираем топик: plantcare/device/{device_id}/data
            parts = topic.split('/')
            if len(parts) >= 3:
                device_id = parts[2]
                msg_type = parts[3] if len(parts) > 3 else "unknown"

                if msg_type == "data":
                    # Обработка данных от датчиков
                    self.process_sensor_data(device_id, payload)
                elif msg_type == "status":
                    # Обработка статуса устройства
                    self.process_device_status(device_id, payload)

        except Exception as e:
            print(f"Ошибка обработки MQTT сообщения: {e}")

    def process_sensor_data(self, device_id, data):
        """Обработка данных от датчиков"""
        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            from Sensor_service import SensorService
            sensor_service = SensorService()

            # Преобразуем данные в формат, ожидаемый SensorService
            flat_data = {
                "device_id": device_id,
                "temp": data.get("sensors", {}).get("temp"),
                "soil_moisture": data.get("sensors", {}).get("soil"),
                "light": data.get("sensors", {}).get("light"),
                "humidity": data.get("sensors", {}).get("humidity"),
                "pump_state": data.get("sensors", {}).get("pump", False)
            }

            # Обрабатываем данные
            result = sensor_service.process_sensor_data(flat_data)
            print(f"Данные обработаны: {result}")

            # Если нужно отправить команду обратно
            for cmd in result.get('commands', []):
                if cmd['command'] in ['pump_on', 'pump_off', 'toggle_pump']:
                    self.send_command(device_id, cmd['command'])

        except Exception as e:
            print(f"Ошибка обработки данных датчиков: {e}")

    def process_device_status(self, device_id, data):
        """Обработка статуса устройства"""
        # Сохраняем состояние насоса
        if 'pump_state' in data:
            # Обновляем глобальный словарь с данными
            from devices import latest_sensor_data
            if device_id not in latest_sensor_data:
                latest_sensor_data[device_id] = {}
            latest_sensor_data[device_id]['pump'] = data['pump_state']
            print(f"Статус насоса для {device_id}: {data['pump_state']}")

    def send_command(self, device_id, command, command_id=None):
        """Отправить команду на устройство"""
        topic = f"plantcare/device/{device_id}/command"

        if command_id is None:
            command_id = str(int(time.time()))

        command_msg = {
            "command": command,
            "command_id": command_id,
            "timestamp": time.time()
        }

        # Сохраняем для ожидания ответа
        self.pending_commands[command_id] = {
            "device_id": device_id,
            "command": command,
            "timestamp": time.time(),
            "status": "pending"
        }

        # Публикуем команду
        result = self.client.publish(topic, json.dumps(command_msg))

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Команда {command} отправлена на {device_id}")
            return {"success": True, "command_id": command_id}
        else:
            print(f"Ошибка отправки команды: {result.rc}")
            return {"success": False, "error": f"MQTT error: {result.rc}"}

    def get_device_status(self, device_id):
        """Получить статус устройства"""
        from devices import latest_sensor_data
        return latest_sensor_data.get(device_id, {})

    def start(self):
        """Запуск MQTT клиента в отдельном потоке"""

        def run():
            try:
                self.client.connect(self.mqtt_host, self.mqtt_port, 60)
                self.client.loop_forever()
            except Exception as e:
                print(f"Ошибка подключения MQTT: {e}")
                # Пытаемся переподключиться через 5 секунд
                time.sleep(5)
                self.start()

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def stop(self):
        """Остановка MQTT клиента"""
        self.client.loop_stop()
        self.client.disconnect()


# Создаем глобальный экземпляр
mqtt_service = None


def init_mqtt():
    """Инициализация MQTT сервиса"""
    global mqtt_service
    mqtt_service = MQTTService()
    mqtt_service.start()
    return mqtt_service