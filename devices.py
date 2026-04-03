# devices - Модуль для работы с ESP32 устройствами
# Поддерживает MQTT и HTTP (обратная совместимость)
from flask import request # Для работы с HTTP-данными
from flask import jsonify # Для создания JSON-ответов
from datetime import datetime # Для создания времени получения данных
import requests # Для отправки запросов к контроллеру

# Глобальная переменная для MQTT сервиса
mqtt_service = None


def set_mqtt_service(mqtt): # Установка глобального MQTT сервиса
    global mqtt_service
    mqtt_service = mqtt


# Ключ для получения запросов от микроконтроллера
ESP32_API_KEY = "esp32_secret_key_123"
# Инициализация сервисов
from Sensor_service import SensorService
from Scenario_service import ScenarioService
sensor_service = SensorService()
scenario_service = ScenarioService()
# Хранилище данных
latest_sensor_data = {}      # key: device_id, value: последние показания + pump
device_ip_map = {}           # key: device_id, value: последний известный IP ESP32


def verify_esp32_key(): # Проверка API ключа ESP32
    # Береём API-ключ из запроса
    api_key = request.headers.get('X-API-Key')
    # Если ничего нет, значит, ключ не указан
    if not api_key:
        return False, "Отсутствует API ключ"
    # Если он не совпадает с ESP32_API_KEY, значит, это не тот ключ
    if api_key != ESP32_API_KEY:
        return False, "Неверный API ключ"
    # Если он совпадает, значит, что всё хорошо
    return True, ""


def send_mqtt_command(device_id, command): # Отправка команды через MQTT
    # Если ничего нет, значит, сервис не работает
    if not mqtt_service:
        print("MQTT сервис не инициализирован")
        return False, "MQTT сервис недоступен"
    # Пробуем отправить команду через MQTT-сервис (если всё хорошо, значит, всё хорошо, если нет, то это ошибка)
    try:
        result = mqtt_service.send_command(device_id, command)
        if result.get("success"):
            return True, result.get("command_id")
        else:
            return False, result.get("error", "Ошибка отправки")
    # Если произошла какая-то неизвестная ошибка, то так и говорим
    except Exception as e:
        print(f"Ошибка отправки MQTT команды: {e}")
        return False, str(e)


def process_sensor_data(): # ESP32 отправляет данные датчиков через HTTP.
    # Используется как запасной случай, если MQTT недоступен.
    # Проверяем API-ключ, и если он неверный, то возвращается ошибка.
    is_valid, error = verify_esp32_key()
    if not is_valid:
        return jsonify({"success": False, "error": error}), 401
    # Берём JSON и ID устройства (если чего-то нет - так и говорим)
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Отсутствуют данные"}), 400
    device_id = data.get('device_id') or data.get('device')
    if not device_id:
        return jsonify({"success": False, "error": "Отсутствует device_id"}), 400
    # Сохраняем IP адрес используемого контроллера в словарь
    client_ip = request.remote_addr
    device_ip_map[device_id] = client_ip
    # Сохраняем все датчики как есть
    sensors = data.get('sensors', {})
    latest_sensor_data[device_id] = {
        'timestamp': datetime.utcnow().isoformat(),
        'sensors': sensors,
        'pump': sensors.get('pump', False)
    }
    print(f"[{datetime.now()}] HTTP данные от {device_id} с IP {client_ip}: {latest_sensor_data[device_id]}")
    try:
        # Преобразование во flat_data для SensorService (только для совместимости)
        flat_data = {
            "device_id": device_id,
            "temp": sensors.get('temp'),
            "soil_moisture": sensors.get('soil'),
            "light": sensors.get('light'),
            "humidity": sensors.get('humidity'),
            "pump_state": sensors.get('pump', False)
        }
        # Добавляем все остальные датчики в flat_data
        for key, value in sensors.items():
            if key not in ['temp', 'soil', 'light', 'humidity', 'pump']:
                flat_data[key] = value
        result = sensor_service.process_sensor_data(flat_data)
        print("Результат обработки:", result)
        # Отправляем команды через MQTT (если они, конечно, захотят отправиться туда)
        for cmd in result.get('commands', []):
            if cmd['command'] in ['pump_on', 'pump_off', 'toggle_pump']:
                success, msg = send_mqtt_command(device_id, cmd['command'])
                if not success:
                    print(f"Не удалось отправить команду {cmd['command']}: {msg}")
                else:
                    print(f"Команда {cmd['command']} отправлена через MQTT")
        return jsonify(result), 200
    # Если произошла какая-то неизвестная ошибка, то так и говорим
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        print(f"Ошибка обработки данных: {e}")
        return jsonify({"success": False, "error": "Внутренняя ошибка сервера"}), 500


def get_device_scenario(device_id): # Запрос сценария контроллером
    # Проверяем API-ключ, и если он неверный, то возвращается ошибка.
    is_valid, error = verify_esp32_key()
    if not is_valid:
        return jsonify({"success": False, "error": error}), 401
    # Пробуем получить сценарий у сервиса для сценариев
    try:
        result = scenario_service.get_device_scenario(device_id)
        return jsonify(result), 200
    # Если произошла какая-то неизвестная ошибка, то так и говорим
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def get_device_data(device_id): # Получение последних данных датчиков в приложении
    # Возвращает все датчики динамически.
    # Пробуем получить данные из запроса (нет данных - нет данных)
    data = latest_sensor_data.get(device_id)
    if not data:
        return jsonify({"error": "Нет данных для данного устройства"}), 404
    # Возвращаем полные данные, включая все датчики
    response_data = {
        'timestamp': data.get('timestamp'),
        'sensors': data.get('sensors', {}),
        'pump': data.get('pump', False)
    }
    return jsonify(response_data), 200


def toggle_pump(device_id): # Переключение насоса в приложении
    # Пытаемся отправить через MQTT
    if mqtt_service:
        success, result = send_mqtt_command(device_id, "toggle_pump")
        if success:
            # Обновляем локальное состояние
            if device_id in latest_sensor_data:
                current_state = latest_sensor_data[device_id].get('pump', False)
                latest_sensor_data[device_id]['pump'] = not current_state
                # Также обновляем в sensors
                if 'sensors' in latest_sensor_data[device_id]:
                    latest_sensor_data[device_id]['sensors']['pump'] = not current_state
            return jsonify({"success": True, "pump": latest_sensor_data[device_id]['pump']}), 200
    # Если MQTT не работает, пытаемся через HTTP (старый способ)
    esp_ip = device_ip_map.get(device_id)
    # Если и так не работает, значит, что-то не так с сервисом и IP устройства
    if not esp_ip:
        return jsonify({"error": "MQTT недоступен и IP устройства неизвестен"}), 404
    # Пробуем отправить команды контроллеру
    try:
        url = f"http://{esp_ip}/togglePump"
        resp = requests.post(url, json={}, timeout=5)
        if resp.status_code == 200:
            new_state = resp.json().get('pump')
            if device_id in latest_sensor_data:
                latest_sensor_data[device_id]['pump'] = new_state
                if 'sensors' in latest_sensor_data[device_id]:
                    latest_sensor_data[device_id]['sensors']['pump'] = new_state
            return jsonify({"success": True, "pump": new_state}), 200
        else:
            return jsonify({"error": f"ESP вернул код {resp.status_code}"}), 502
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Ошибка соединения с ESP: {str(e)}"}), 500


def pump_on(device_id): # Включение насоса в приложении
    # То же самое, что и переключением насоса, только ссылка другая
    if mqtt_service:
        success, result = send_mqtt_command(device_id, "pump_on")
        if success:
            if device_id in latest_sensor_data:
                latest_sensor_data[device_id]['pump'] = True
                if 'sensors' in latest_sensor_data[device_id]:
                    latest_sensor_data[device_id]['sensors']['pump'] = True
            return jsonify({"success": True, "pump": True}), 200

    esp_ip = device_ip_map.get(device_id)
    if not esp_ip:
        return jsonify({"error": "MQTT недоступен и IP устройства неизвестен"}), 404

    try:
        url = f"http://{esp_ip}/pumpOn"
        resp = requests.post(url, json={}, timeout=5)
        if resp.status_code == 200:
            if device_id in latest_sensor_data:
                latest_sensor_data[device_id]['pump'] = True
                if 'sensors' in latest_sensor_data[device_id]:
                    latest_sensor_data[device_id]['sensors']['pump'] = True
            return jsonify({"success": True, "pump": True}), 200
        else:
            return jsonify({"error": f"ESP вернул код {resp.status_code}"}), 502
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Ошибка соединения с ESP: {str(e)}"}), 500


def pump_off(device_id): # Выключение насоса в приложении
    # То же самое, что и переключением насоса, только ссылка другая
    if mqtt_service:
        success, result = send_mqtt_command(device_id, "pump_off")
        if success:
            if device_id in latest_sensor_data:
                latest_sensor_data[device_id]['pump'] = False
                if 'sensors' in latest_sensor_data[device_id]:
                    latest_sensor_data[device_id]['sensors']['pump'] = False
            return jsonify({"success": True, "pump": False}), 200
    esp_ip = device_ip_map.get(device_id)
    if not esp_ip:
        return jsonify({"error": "MQTT недоступен и IP устройства неизвестен"}), 404
    try:
        url = f"http://{esp_ip}/pumpOff"
        resp = requests.post(url, json={}, timeout=5)
        if resp.status_code == 200:
            if device_id in latest_sensor_data:
                latest_sensor_data[device_id]['pump'] = False
                if 'sensors' in latest_sensor_data[device_id]:
                    latest_sensor_data[device_id]['sensors']['pump'] = False
            return jsonify({"success": True, "pump": False}), 200
        else:
            return jsonify({"error": f"ESP вернул код {resp.status_code}"}), 502
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Ошибка соединения с ESP: {str(e)}"}), 500


def get_pump_status(device_id): # Запрашивание состояния насоса пользователем
    # Берем информацию с запроса (если там нет наноса, так и говорим)
    data = latest_sensor_data.get(device_id)
    if not data or 'pump' not in data:
        return jsonify({"error": "Состояние насоса неизвестно"}), 404
    return jsonify({"pump": data['pump']}), 200


def get_device_info(device_id): # Получает информацию об устройстве
    data = latest_sensor_data.get(device_id)
    if not data:
        return jsonify({"error": "Устройство не найдено"}), 404
    sensors_info = data.get('sensors', {})
    sensor_keys = list(sensors_info.keys())
    return jsonify({
        "device_id": device_id,
        "last_seen": data.get('timestamp'),
        "ip": device_ip_map.get(device_id),
        "pump_state": data.get('pump', False),
        "sensors_count": len(sensor_keys),
        "sensors_list": sensor_keys,
        "has_data": True
    }), 200


def get_notifications(device_id): # Возвращает все данные датчиков для Android.
    data = latest_sensor_data.get(device_id)
    if not data:
        return jsonify({"notifications": [], "sensor_data": None}), 200
    # Возвращаем текущие данные датчиков со всеми ключами
    return jsonify({
        "notifications": [],  # Пустой массив, так как уведомления генерируются на Android
        "sensor_data": data.get('sensors', {}),
        "pump": data.get('pump', False),
        "timestamp": data.get('timestamp')
    }), 200


def get_all_sensors(device_id): # Возвращает список всех активных датчиков для устройства.
    data = latest_sensor_data.get(device_id)
    if not data:
        return jsonify({"error": "Устройство не найдено"}), 404
    sensors = data.get('sensors', {})
    sensor_list = []
    for key, value in sensors.items():
        sensor_list.append({
            "name": key,
            "value": value,
            "unit": _get_unit_for_sensor(key)
        })
    return jsonify({
        "device_id": device_id,
        "sensors": sensor_list,
        "count": len(sensor_list)
    }), 200


def _get_unit_for_sensor(sensor_key): # Определяет единицу измерения по ключу датчика
    sensor_key_lower = sensor_key.lower()
    if 'temp' in sensor_key_lower:
        return "°C"
    elif 'hum' in sensor_key_lower:
        return "%"
    elif 'light' in sensor_key_lower:
        return "лк"
    elif 'soil' in sensor_key_lower:
        return "%"
    else:
        return ""


def process_mqtt_sensor_data(device_id, data): # Обработка данных от датчиков, полученных через MQTT.
    try:
        # Сохраняем все датчики как есть
        sensors = data.get('sensors', {})
        # Если sensors пустой, но есть прямые поля, собираем их
        if not sensors:
            sensors = {}
            for key in ['light', 'soil', 'temp', 'humidity', 'pump']:
                if key in data:
                    sensors[key] = data[key]
        latest_sensor_data[device_id] = {
            'timestamp': datetime.utcnow().isoformat(),
            'sensors': sensors,
            'pump': sensors.get('pump', False)
        }
        print(f"[{datetime.now()}] MQTT данные от {device_id}: {latest_sensor_data[device_id]}")
        # Преобразование для SensorService
        flat_data = {
            "device_id": device_id,
            "temp": sensors.get('temp'),
            "soil_moisture": sensors.get('soil'),
            "light": sensors.get('light'),
            "humidity": sensors.get('humidity'),
            "pump_state": sensors.get('pump', False)
        }
        # Добавляем все остальные датчики в flat_data
        for key, value in sensors.items():
            if key not in ['temp', 'soil', 'light', 'humidity', 'pump']:
                flat_data[key] = value
        result = sensor_service.process_sensor_data(flat_data)
        print(f"Результат обработки MQTT данных: {result}")
        # Отправляем команды обратно
        for cmd in result.get('commands', []):
            if cmd['command'] in ['pump_on', 'pump_off', 'toggle_pump']:
                success, msg = send_mqtt_command(device_id, cmd['command'])
                if not success:
                    print(f"Не удалось отправить команду {cmd['command']}: {msg}")
        return result
    except Exception as e:
        print(f"Ошибка обработки MQTT данных: {e}")
        return {"success": False, "error": str(e)}


def process_mqtt_device_status(device_id, data): # Обработка статуса устройства, полученного через MQTT.
    try:
        if 'pump_state' in data:
            if device_id not in latest_sensor_data:
                latest_sensor_data[device_id] = {}
            latest_sensor_data[device_id]['pump'] = data['pump_state']
            if 'sensors' not in latest_sensor_data[device_id]:
                latest_sensor_data[device_id]['sensors'] = {}
            latest_sensor_data[device_id]['sensors']['pump'] = data['pump_state']
            print(f"[{datetime.now()}] Статус насоса {device_id}: {data['pump_state']}")
        if 'status' in data:
            print(f"[{datetime.now()}] Устройство {device_id}: {data['status']}")
    except Exception as e:
        print(f"Ошибка обработки статуса устройства: {e}")