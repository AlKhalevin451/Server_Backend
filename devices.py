"""
devices.py - Модуль для работы с ESP32 устройствами
<<<<<<< HEAD
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
=======
Содержит эндпоинты Flask для приёма данных от ESP32, управления насосом,
а также для взаимодействия с Android-клиентом.
"""

from flask import request, jsonify
from datetime import datetime
import requests  # для отправки команд на ESP
# Инициализация сервисов
from Sensor_service import SensorService
from Scenario_service import ScenarioService

# Константа: секретный ключ, который ESP32 должна передавать в заголовке X-API-Key.
# Используется для аутентификации запросов от устройств.
ESP32_API_KEY = "esp32_secret_key_123"
# Создаём экземпляры сервисов для обработки данных и сценариев.
sensor_service = SensorService()
scenario_service = ScenarioService()
# Глобальные хранилища состояния (в памяти, не сохраняются между перезапусками).
# latest_sensor_data: key = device_id, value = словарь с последними показаниями датчиков и состоянием насоса.
latest_sensor_data = {}
# device_ip_map: key = device_id, value = последний известный IP-адрес ESP32 (для отправки команд).
device_ip_map = {}


def verify_esp32_key():
    """
    Проверка API ключа ESP32 (для эндпоинтов, вызываемых ESP).
    Читает заголовок X-API-Key из запроса и сравнивает с ESP32_API_KEY.
    Returns:
        (bool, str): (True, "") если ключ верный, иначе (False, сообщение об ошибке).
    """
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return False, "Отсутствует API ключ"
    if api_key != ESP32_API_KEY:
        return False, "Неверный API ключ"
    return True, ""


<<<<<<< HEAD
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
=======
def process_sensor_data():
    """
    Эндпоинт для приёма данных от ESP32 (POST /api/sensor_data).
    Ожидает JSON с данными датчиков, сохраняет их, обрабатывает через SensorService,
    и при необходимости отправляет команды на устройство (например, включение насоса).

    Returns:
        JSON-ответ с результатом обработки.
    """
    # Проверка аутентификации
    is_valid, error = verify_esp32_key()
    if not is_valid:
        return jsonify({"success": False, "error": error}), 401
    # Получение и валидация входных данных
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Отсутствуют данные"}), 400
    # Извлекаем device_id (может быть в поле 'device_id' или 'device' для обратной совместимости)
    device_id = data.get('device_id') or data.get('device')
    if not device_id:
        return jsonify({"success": False, "error": "Отсутствует device_id"}), 400
    # Сохраняем IP-адрес, с которого пришёл запрос (для последующей отправки команд).
    client_ip = request.remote_addr
    device_ip_map[device_id] = client_ip
    # Извлекаем показания датчиков из вложенного объекта 'sensors'.
    sensors = data.get('sensors', {})
    # Формируем запись с последними данными и временем получения.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    latest_sensor_data[device_id] = {
        'timestamp': datetime.utcnow().isoformat(),
        'light': sensors.get('light'),
        'soil': sensors.get('soil'),
        'temp': sensors.get('temp'),
        'humidity': sensors.get('humidity'),
<<<<<<< HEAD
        'pump': sensors.get('pump', False)
    }

    print(f"[{datetime.now()}] Данные от {device_id} с IP {client_ip}: {latest_sensor_data[device_id]}")

    try:
        # 🔧 Преобразование во flat_data
=======
        'pump': sensors.get('pump', False)   # текущее состояние насоса (если передано)
    }
    # Отладочный вывод в консоль сервера.
    print(f"[{datetime.now()}] Данные от {device_id} с IP {client_ip}: {latest_sensor_data[device_id]}")
    try:
        # Преобразование входных данных в формат, ожидаемый SensorService.
        # SensorService.process_sensor_data ожидает плоский словарь с ключами:
        # device_id, temp, soil_moisture, light, humidity, pump_state.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        flat_data = {
            "device_id": device_id,
            "temp": sensors.get('temp'),
            "soil_moisture": sensors.get('soil'),
            "light": sensors.get('light'),
            "humidity": sensors.get('humidity'),
            "pump_state": sensors.get('pump', False)
        }
<<<<<<< HEAD
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
=======
        # Вызов бизнес-логики обработки данных.
        result = sensor_service.process_sensor_data(flat_data)
        # Отладка: выводим результат сервиса.
        print("Результат сервиса:", result)
        # Обработка команд
        # Если сервис вернул команды, выполняем их.
        # В данном примере поддерживается только команда 'pump_on' (включение насоса).
        for cmd in result.get('commands', []):
            if cmd['command'] == 'pump_on':
                # Получаем сохранённый IP устройства.
                esp_ip = device_ip_map.get(device_id)
                if esp_ip:
                    try:
                        # Отправляем POST-запрос на ESP32 для переключения насоса.
                        # ESP ожидает пустое тело (json={}).
                        resp = requests.post(f"http://{esp_ip}/togglePump", json={}, timeout=2)
                        if resp.status_code == 200:
                            # ESP возвращает JSON с новым состоянием насоса (поле 'pump').
                            new_state = resp.json().get('pump')
                            # Обновляем сохранённое состояние в latest_sensor_data.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
                            if device_id in latest_sensor_data:
                                latest_sensor_data[device_id]['pump'] = new_state
                            print(f"Автоматическое включение насоса на {esp_ip}, новое состояние: {new_state}")
                        else:
                            print(f"Ошибка при отправке pump_on: {resp.status_code}")
                    except Exception as e:
                        print(f"Исключение при отправке pump_on: {e}")
                else:
                    print(f"IP для устройства {device_id} не найден в device_ip_map")
<<<<<<< HEAD
            # Здесь можно добавить обработку других команд (например, alert)
        # ---------------------------------------------------------

        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
=======
        # Возвращаем результат клиенту (ESP32).
        return jsonify(result), 200

    except ValueError as e:
        # Ошибка валидации данных (например, сценарий не найден).
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        # Непредвиденная ошибка.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        print(f"Ошибка обработки данных: {e}")
        return jsonify({"success": False, "error": "Внутренняя ошибка сервера"}), 500


def get_device_scenario(device_id):
<<<<<<< HEAD
    """Возвращает сценарий для устройства (вызывается ESP32)."""
=======
    """
    Эндпоинт для получения активного сценария устройства (GET /api/device/<device_id>/scenario).
    Вызывается ESP32 для получения параметров сценария.
    """
    # Проверка ключа ESP32.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    is_valid, error = verify_esp32_key()
    if not is_valid:
        return jsonify({"success": False, "error": error}), 401

    try:
<<<<<<< HEAD
        result = scenario_service.get_device_scenario(device_id)
=======
        # Запрашиваем сценарий через ScenarioService.
        result = scenario_service.get_device_scenario(device_id)
        # Возвращаем результат (может быть None, если сценарий не назначен).
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


<<<<<<< HEAD
# ========== НОВЫЕ ЭНДПОИНТЫ ДЛЯ ANDROID ==========
=======
# Эндпоинты для ANDROID
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f

def get_device_data(device_id):
    """
    GET /api/device/<device_id>/data
    Возвращает последние данные датчиков для указанного устройства.
<<<<<<< HEAD
=======
    Используется Android-клиентом для отображения текущих показаний.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    """
    data = latest_sensor_data.get(device_id)
    if not data:
        return jsonify({"error": "Нет данных для данного устройства"}), 404
    return jsonify(data), 200


def toggle_pump(device_id):
    """
    POST /api/device/<device_id>/pump/toggle
<<<<<<< HEAD
    Отправляет команду переключения насоса на ESP32.
    """
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
=======
    Отправляет команду переключения насоса на ESP32 (ручное управление из Android).
    """
    # Проверяем, есть ли IP для этого устройства.
    esp_ip = device_ip_map.get(device_id)
    if not esp_ip:
        return jsonify({"error": "IP устройства неизвестен"}), 404
    # Отправляем POST-запрос на ESP.
    try:
        url = f"http://{esp_ip}/togglePump"
        # ESP ожидает POST с пустым телом (можно {}).
        resp = requests.post(url, json={}, timeout=5)
        if resp.status_code == 200:
            new_state = resp.json().get('pump')
            # Обновляем сохранённое состояние.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
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
<<<<<<< HEAD
    Возвращает текущее состояние насоса (из последних данных).
=======
    Возвращает текущее состояние насоса (из последних данных, хранящихся в памяти).
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    """
    data = latest_sensor_data.get(device_id)
    if not data or 'pump' not in data:
        return jsonify({"error": "Состояние насоса неизвестно"}), 404
    return jsonify({"pump": data['pump']}), 200