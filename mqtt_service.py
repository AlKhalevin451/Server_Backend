import paho.mqtt.client as mqtt
import json
import threading
import time
import traceback
from datetime import datetime

class MQTTService:
    def __init__(self, app=None):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.app = app

        self.mqtt_host = "broker.hivemq.com"
        self.mqtt_port = 1883

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ MQTT подключен")
            client.subscribe("plantcare/device/+/data")
            client.subscribe("plantcare/device/+/status")
            print("📡 Подписан на топики: plantcare/device/+/data и plantcare/device/+/status")
        else:
            print(f"❌ Ошибка подключения MQTT, код: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            print(f"📨 MQTT получено: {topic} -> {payload}")

            parts = topic.split('/')
            if len(parts) >= 3:
                device_id = parts[2]
                msg_type = parts[3] if len(parts) > 3 else "unknown"

                if msg_type == "data":
                    self.process_sensor_data(device_id, payload)
                elif msg_type == "status":
                    self.process_device_status(device_id, payload)

        except Exception as e:
            print(f"❌ Ошибка обработки MQTT: {e}")
            traceback.print_exc()

    def process_sensor_data(self, device_id, data):
        if self.app:
            with self.app.app_context():
                self._process_sensor_data_in_context(device_id, data)
        else:
            print("⚠️ Нет контекста приложения Flask")

    def _process_sensor_data_in_context(self, device_id, data):
        try:
            from devices import latest_sensor_data

            latest_sensor_data[device_id] = {
                'timestamp': datetime.utcnow().isoformat(),
                'light': data.get('sensors', {}).get('light'),
                'soil': data.get('sensors', {}).get('soil'),
                'temp': data.get('sensors', {}).get('temp'),
                'humidity': data.get('sensors', {}).get('humidity'),
                'pump': data.get('sensors', {}).get('pump', False)
            }

            print(f"💾 Данные сохранены для {device_id}: {latest_sensor_data[device_id]}")

            # Опционально: вызвать SensorService
            try:
                from Sensor_service import SensorService
                sensor_service = SensorService()
                flat_data = {
                    "device_id": device_id,
                    "temp": data.get('sensors', {}).get('temp'),
                    "soil_moisture": data.get('sensors', {}).get('soil'),
                    "light": data.get('sensors', {}).get('light'),
                    "humidity": data.get('sensors', {}).get('humidity'),
                    "pump_state": data.get('sensors', {}).get('pump', False)
                }
                result = sensor_service.process_sensor_data(flat_data)
                print(f"🤖 Результат обработки: {result}")
                for cmd in result.get('commands', []):
                    if cmd['command'] in ['pump_on', 'pump_off', 'toggle_pump']:
                        self.send_command(device_id, cmd['command'])
            except Exception as e:
                print(f"⚠️ Ошибка SensorService: {e}")

        except Exception as e:
            print(f"❌ Ошибка сохранения данных: {e}")
            traceback.print_exc()

    def process_device_status(self, device_id, data):
        try:
            from devices import latest_sensor_data
            if 'pump_state' in data:
                if device_id not in latest_sensor_data:
                    latest_sensor_data[device_id] = {}
                latest_sensor_data[device_id]['pump'] = data['pump_state']
                print(f"🔄 Статус насоса {device_id}: {data['pump_state']}")
            if 'status' in data:
                print(f"📊 Устройство {device_id}: {data['status']}")
        except Exception as e:
            print(f"❌ Ошибка статуса: {e}")

    def send_command(self, device_id, command, command_id=None):
        topic = f"plantcare/device/{device_id}/command"
        if command_id is None:
            command_id = str(int(time.time()))
        command_msg = {"command": command, "command_id": command_id, "timestamp": time.time()}
        result = self.client.publish(topic, json.dumps(command_msg))
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"📤 Команда {command} отправлена на {device_id}")
            return {"success": True, "command_id": command_id}
        else:
            print(f"❌ Ошибка отправки команды: {result.rc}")
            return {"success": False, "error": f"MQTT error: {result.rc}"}

    def start(self, app):
        self.app = app
        def run():
            try:
                print(f"🔌 Подключение к MQTT брокеру {self.mqtt_host}:{self.mqtt_port}")
                self.client.connect(self.mqtt_host, self.mqtt_port, 60)
                self.client.loop_forever()
            except Exception as e:
                print(f"❌ Ошибка подключения: {e}")
                time.sleep(5)
                self.start(app)
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

mqtt_service = None

def init_mqtt(app):
    global mqtt_service
    mqtt_service = MQTTService(app)
    mqtt_service.start(app)
    return mqtt_service