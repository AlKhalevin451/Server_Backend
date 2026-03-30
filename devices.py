"""
devices.py - Модуль для работы с ESP32 устройствами
"""
from flask import request, jsonify
from datetime import datetime
import requests  # для отправки команд на ESP

# Константы
ESP32_API_KEY = "esp32_secret_key_123"

# Инициализация сервисов (ваши существующие)
from Sensor_service import SensorService
from Scenario_service import ScenarioService

sensor_service = SensorService()
scenario_service = ScenarioService()

# ------------------- Хранилище данных от ESP32 -------------------
# В реальном проекте используйте базу данных, здесь для простоты - словари
latest_sensor_data = {}      # key: device_id, value: последние показания + pump
device_ip_map = {}           # key: device_id, value: последний известный IP ESP32

# -----------------------------------------------------------------

def verify_esp32_key():
    """Проверка API ключа ESP32 (для эндпоинтов, вызываемых ESP)"""
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return False, "Отсутствует API ключ"
    if api_key != ESP32_API_KEY:
        return False, "Неверный API ключ"
    return True, ""


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
        # 🔧 Преобразование во flat_data
        flat_data = {
            "device_id": device_id,
            "temp": sensors.get('temp'),
            "soil_moisture": sensors.get('soil'),
            "light": sensors.get('light'),
            "humidity": sensors.get('humidity'),
            "pump_state": sensors.get('pump', False)
        }
        result = sensor_service.process_sensor_data(flat_data)

        # Отладка: выводим результат сервиса
        print("Результат сервиса:", result)

        # ------------------- ОБРАБОТКА КОМАНД -------------------
        # Если сервис вернул команды, выполняем их
        for cmd in result.get('commands', []):
            if cmd['command'] == 'pump_on':
                esp_ip = device_ip_map.get(device_id)
                if esp_ip:
                    try:
                        # Отправляем команду переключения насоса
                        resp = requests.post(f"http://{esp_ip}/togglePump", json={}, timeout=2)
                        if resp.status_code == 200:
                            new_state = resp.json().get('pump')
                            # Обновляем сохранённое состояние
                            if device_id in latest_sensor_data:
                                latest_sensor_data[device_id]['pump'] = new_state
                            print(f"Автоматическое включение насоса на {esp_ip}, новое состояние: {new_state}")
                        else:
                            print(f"Ошибка при отправке pump_on: {resp.status_code}")
                    except Exception as e:
                        print(f"Исключение при отправке pump_on: {e}")
                else:
                    print(f"IP для устройства {device_id} не найден в device_ip_map")
            # Здесь можно добавить обработку других команд (например, alert)
        # ---------------------------------------------------------

        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        print(f"Ошибка обработки данных: {e}")
        return jsonify({"success": False, "error": "Внутренняя ошибка сервера"}), 500


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
    Отправляет команду переключения насоса на ESP32.
    """
    try:
        # Проверяем, есть ли IP для этого устройства
        esp_ip = device_ip_map.get(device_id)
        if not esp_ip:
            print(f"[ERROR] IP для устройства {device_id} не найден в device_ip_map")
            return jsonify({"error": "IP устройства неизвестен"}), 404

        print(f"[DEBUG] Отправка команды togglePump на {esp_ip} для устройства {device_id}")

        # Отправляем POST-запрос на ESP с таймаутом
        url = f"http://{esp_ip}/togglePump"

        try:
            resp = requests.post(url, json={}, timeout=3)
            print(f"[DEBUG] ESP ответил с кодом: {resp.status_code}")

            if resp.status_code == 200:
                try:
                    response_data = resp.json()
                    new_state = response_data.get('pump')
                    print(f"[DEBUG] Новое состояние насоса: {new_state}")

                    # Обновляем сохранённое состояние
                    if device_id in latest_sensor_data:
                        latest_sensor_data[device_id]['pump'] = new_state
                        print(
                            f"[DEBUG] Обновлено состояние в latest_sensor_data: {latest_sensor_data[device_id]['pump']}")
                    else:
                        print(f"[WARNING] Устройство {device_id} не найдено в latest_sensor_data")
                        # Создаем запись если её нет
                        latest_sensor_data[device_id] = {
                            'pump': new_state,
                            'timestamp': datetime.utcnow().isoformat()
                        }

                    return jsonify({"success": True, "pump": new_state}), 200
                except ValueError as json_err:
                    print(f"[ERROR] Ошибка парсинга JSON от ESP: {json_err}, ответ: {resp.text}")
                    return jsonify({"error": "Неверный формат ответа от ESP"}), 502
            else:
                print(f"[ERROR] ESP вернул ошибку: {resp.status_code}, тело: {resp.text}")
                return jsonify({"error": f"ESP вернул код {resp.status_code}"}), 502

        except requests.exceptions.Timeout:
            print(f"[ERROR] Таймаут при подключении к ESP {esp_ip}")
            return jsonify({"error": "Таймаут соединения с ESP"}), 504
        except requests.exceptions.ConnectionError as conn_err:
            print(f"[ERROR] Ошибка подключения к ESP {esp_ip}: {conn_err}")
            return jsonify({"error": f"ESP недоступен: {str(conn_err)}"}), 503

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


def get_pump_status(device_id):
    """
    GET /api/device/<device_id>/pump/status
    Возвращает текущее состояние насоса (из последних данных).
    """
    data = latest_sensor_data.get(device_id)
    if not data or 'pump' not in data:
        return jsonify({"error": "Состояние насоса неизвестно"}), 404
    return jsonify({"pump": data['pump']}), 200