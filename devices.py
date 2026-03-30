"""
devices.py - Модуль для работы с ESP32 устройствами
"""
from flask import request, jsonify
from datetime import datetime
import requests
from collections import defaultdict
import threading
import time

# Константы
ESP32_API_KEY = "esp32_secret_key_123"

# Инициализация сервисов
from Sensor_service import SensorService
from Scenario_service import ScenarioService

sensor_service = SensorService()
scenario_service = ScenarioService()

# ------------------- Хранилище данных от ESP32 -------------------
latest_sensor_data = {}      # key: device_id, value: последние показания + pump
device_ip_map = {}           # key: device_id, value: последний известный IP ESP32

# ------------------- ОЧЕРЕДЬ КОМАНД -------------------
command_queue = defaultdict(list)  # device_id -> list of commands
command_results = defaultdict(dict)  # device_id -> command results

# -----------------------------------------------------------------

def verify_esp32_key():
    """Проверка API ключа ESP32 (для эндпоинтов, вызываемых ESP)"""
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return False, "Отсутствует API ключ"
    if api_key != ESP32_API_KEY:
        return False, "Неверный API ключ"
    return True, ""

def queue_command(device_id, command, params=None):
    """Добавить команду в очередь для устройства"""
    cmd = {
        "command": command,
        "params": params or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    command_queue[device_id].append(cmd)
    print(f"[QUEUE] Добавлена команда {command} для {device_id}")
    return True

# ========== ЭНДПОИНТЫ ДЛЯ ESP32 ==========

def process_sensor_data():
    is_valid, error = verify_esp32_key()
    if not is_valid:
        return jsonify({"success": False, "error": error}), 401

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Отсутствуют данные"}), 400

    device_id = data.get('device_id') or data.get('device')
    if not device_id:
        return jsonify({"success": False, "error": "Отсутствует device_id"}), 400

    client_ip = request.remote_addr
    device_ip_map[device_id] = client_ip

    sensors = data.get('sensors', {})
    latest_sensor_data[device_id] = {
        'timestamp': datetime.utcnow().isoformat(),
        'light': sensors.get('light'),
        'soil': sensors.get('soil'),
        'temp': sensors.get('temp'),
        'humidity': sensors.get('humidity'),
        'pump': sensors.get('pump', False)
    }

    print(f"[{datetime.now()}] Данные от {device_id} с IP {client_ip}: {latest_sensor_data[device_id]}")

    try:
        # Преобразование во flat_data
        flat_data = {
            "device_id": device_id,
            "temp": sensors.get('temp'),
            "soil_moisture": sensors.get('soil'),
            "light": sensors.get('light'),
            "humidity": sensors.get('humidity'),
            "pump_state": sensors.get('pump', False)
        }
        result = sensor_service.process_sensor_data(flat_data)

        print("Результат сервиса:", result)

        # Обработка команд от сервиса (автоматическое управление)
        for cmd in result.get('commands', []):
            if cmd['command'] == 'pump_on':
                # Добавляем команду в очередь вместо прямого вызова
                queue_command(device_id, "pump_on")
                print(f"[AUTO] Добавлена команда pump_on для {device_id}")
            elif cmd['command'] == 'pump_off':
                queue_command(device_id, "pump_off")
                print(f"[AUTO] Добавлена команда pump_off для {device_id}")
            # Здесь можно добавить обработку других команд

        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        print(f"Ошибка обработки данных: {e}")
        return jsonify({"success": False, "error": "Внутренняя ошибка сервера"}), 500

def get_device_command(device_id):
    """
    GET /api/device/<device_id>/command
    ESP32 запрашивает команды (polling)
    """
    is_valid, error = verify_esp32_key()
    if not is_valid:
        return jsonify({"success": False, "error": error}), 401

    # Получаем следующую команду из очереди
    if command_queue[device_id]:
        cmd = command_queue[device_id].pop(0)
        print(f"[CMD] Отдаю команду {cmd['command']} устройству {device_id}")
        return jsonify({
            "has_command": True,
            "command": cmd['command'],
            "params": cmd['params']
        }), 200
    else:
        return jsonify({
            "has_command": False,
            "command": None
        }), 200

def update_pump_state(device_id):
    """
    POST /api/device/<device_id>/pump/state
    ESP32 обновляет состояние насоса после выполнения команды
    """
    is_valid, error = verify_esp32_key()
    if not is_valid:
        return jsonify({"success": False, "error": error}), 401

    data = request.get_json()
    pump_state = data.get('pump')
    command = data.get('command')  # какая команда была выполнена
    success = data.get('success', True)

    if device_id in latest_sensor_data:
        latest_sensor_data[device_id]['pump'] = pump_state
        latest_sensor_data[device_id]['last_command'] = command
        latest_sensor_data[device_id]['command_success'] = success
        latest_sensor_data[device_id]['command_time'] = datetime.utcnow().isoformat()

    print(f"[STATE] Устройство {device_id} обновило состояние насоса: {pump_state}, команда: {command}")

    # Сохраняем результат выполнения команды
    command_results[device_id][command] = {
        "success": success,
        "pump_state": pump_state,
        "timestamp": datetime.utcnow().isoformat()
    }

    return jsonify({"success": True}), 200

def get_device_scenario(device_id):
    """Возвращает сценарий для устройства (вызывается ESP32)."""
    is_valid, error = verify_esp32_key()
    if not is_valid:
        return jsonify({"success": False, "error": error}), 401

    try:
        result = scenario_service.get_device_scenario(device_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def get_device_data(device_id):
    """
    GET /api/device/<device_id>/data
    Возвращает последние данные датчиков для указанного устройства.
    """
    data = latest_sensor_data.get(device_id)
    if not data:
        return jsonify({"error": "Нет данных для данного устройства"}), 404
    return jsonify(data), 200

def toggle_pump(device_id):
    """
    POST /api/device/<device_id>/pump/toggle
    Добавляет команду переключения насоса в очередь для ESP32.
    """
    try:
        # Проверяем, есть ли устройство в базе
        if device_id not in latest_sensor_data and device_id not in device_ip_map:
            print(f"[ERROR] Устройство {device_id} не найдено")
            return jsonify({"error": "Устройство не найдено"}), 404

        # Добавляем команду в очередь вместо прямого вызова
        queue_command(device_id, "toggle_pump")

        # Возвращаем текущее состояние (оно может измениться после выполнения команды)
        current_state = latest_sensor_data.get(device_id, {}).get('pump', False)

        return jsonify({
            "success": True,
            "message": "Команда добавлена в очередь",
            "pump": current_state,
            "pending": len(command_queue[device_id])
        }), 200

    except Exception as e:
        print(f"[ERROR] Непредвиденная ошибка в toggle_pump: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500
    # Проверяем, есть ли IP для этого устройства
    esp_ip = device_ip_map.get(device_id)
    if not esp_ip:
        return jsonify({"error": "IP устройства неизвестен"}), 404

    # Отправляем POST-запрос на ESP
    try:
        url = f"http://{esp_ip}/togglePump"
        # ESP ожидает POST с пустым телом (можно {} )
        resp = requests.post(url, json={}, timeout=5)
        if resp.status_code == 200:
            new_state = resp.json().get('pump')
            # Обновляем сохранённое состояние
            if device_id in latest_sensor_data:
                latest_sensor_data[device_id]['pump'] = new_state
            return jsonify({"success": True, "pump": new_state}), 200
        else:
            return jsonify({"error": f"ESP вернул код {resp.status_code}"}), 502
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Ошибка соединения с ESP: {str(e)}"}), 500

def pump_on(device_id):
    """
    POST /api/device/<device_id>/pump/on
    Добавляет команду включения насоса в очередь
    """
    try:
        if device_id not in latest_sensor_data and device_id not in device_ip_map:
            return jsonify({"error": "Устройство не найдено"}), 404

        queue_command(device_id, "pump_on")

        return jsonify({
            "success": True,
            "message": "Команда включения насоса добавлена в очередь",
            "pump": latest_sensor_data.get(device_id, {}).get('pump', False)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def pump_off(device_id):
    """
    POST /api/device/<device_id>/pump/off
    Добавляет команду выключения насоса в очередь
    """
    try:
        if device_id not in latest_sensor_data and device_id not in device_ip_map:
            return jsonify({"error": "Устройство не найдено"}), 404

        queue_command(device_id, "pump_off")

        return jsonify({
            "success": True,
            "message": "Команда выключения насоса добавлена в очередь",
            "pump": latest_sensor_data.get(device_id, {}).get('pump', False)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_pump_status(device_id):
    """
    GET /api/device/<device_id>/pump/status
    Возвращает текущее состояние насоса (из последних данных).
    """
    data = latest_sensor_data.get(device_id)
    if not data or 'pump' not in data:
        return jsonify({"error": "Состояние насоса неизвестно"}), 404

    pending_commands = len(command_queue[device_id])

    return jsonify({
        "pump": data['pump'],
        "pending_commands": pending_commands,
        "last_update": data.get('timestamp'),
        "last_command": data.get('last_command')
    }), 200

def get_command_queue_status(device_id):
    """
    GET /api/device/<device_id>/queue
    Отладочный эндпоинт для просмотра очереди команд
    """
    is_valid, error = verify_esp32_key()
    if not is_valid:
        return jsonify({"success": False, "error": error}), 401

    return jsonify({
        "device_id": device_id,
        "pending_commands": len(command_queue[device_id]),
        "commands": command_queue[device_id],
        "last_results": command_results.get(device_id, {})
    }), 200