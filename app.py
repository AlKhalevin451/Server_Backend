from flask import Flask, jsonify, request
from database import init_db, close_db
from asgiref.wsgi import WsgiToAsgi

# Подключаем другие файлы
import auth
import scenarios
import devices   # наш обновлённый модуль

# Создаем Flask приложение
app = Flask(__name__)

# Инициализация БД при старте приложения
with app.app_context():
    init_db()
    # Создаем базовые сценарии если их нет
    from config import Config
    config = Config()
    config.make_base_scenarios('plantcare.db')

asgi_app = WsgiToAsgi(app)

# Закрытие соединения после запроса
@app.teardown_appcontext
def shutdown_session(exception=None):
    close_db()

# Существующие маршруты d cthdtht
@app.route('/test/assign', methods=['POST'])
def test_assign():
    data = request.get_json()
    return jsonify({
        "success": True,
        "message": "Тестовый эндпоинт работает",
        "received_data": data,
        "requires_password": False
    }), 200

@app.route('/')
def home():
    return jsonify({
        "message": "Сервер запущен",
        "version": "1.0.0",
        "endpoints": {
            "Аутентификация": {
                "register": "POST /auth/register",
                "login": "POST /api/login"
            },
            "Сценарии": {
                "get_all_public": "GET /api/scenarios",
                "create_scenario": "POST /api/scenarios",
                "assign_scenario": "POST /api/user/scenarios",
                "get_user_scenarios": "GET /api/user/scenarios"
            },
            "Устройства (ESP32)": {
                "send_data": "POST /api/device/data",
                "get_scenario": "GET /api/device/<device_id>/scenario",
                "get_device_data": "GET /api/device/<device_id>/data",
                "toggle_pump": "POST /api/device/<device_id>/pump/toggle",
                "pump_status": "GET /api/device/<device_id>/pump/status"
            },
            "Система": {
                "health": "GET /api/health",
                "info": "GET /api/info"
            }
        }
    }), 200

# Аутентификация
@app.route('/auth/register', methods=['POST'])
def register():
    return auth.register_user()

@app.route('/api/login', methods=['POST'])
def login():
    return auth.login_user()

# Сценарии
@app.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    return scenarios.get_all_scenarios()

@app.route('/api/scenarios', methods=['POST'])
def create_scenario():
    return scenarios.create_scenario()

@app.route('/api/user/scenarios', methods=['POST'])
def assign_scenario():
    return scenarios.assign_scenario_to_user()

@app.route('/api/user/scenarios', methods=['GET'])
def get_user_scenarios():
    return scenarios.get_user_scenarios()

@app.route('/debug/all-scenarios')
def debug_all_scenarios():
    from database import query_db
    all_scenarios = query_db("SELECT * FROM scenarios")
    all_assignments = query_db("SELECT * FROM user_scenarios")
    return jsonify({
        "scenarios": [dict(row) for row in all_scenarios],
        "assignments": [dict(row) for row in all_assignments]
    })

# Устройства (ESP32)
@app.route('/api/device/data', methods=['POST'])
def device_data():
    """ESP32 отправляет данные датчиков."""
    return devices.process_sensor_data()

@app.route('/api/device/<device_id>/scenario', methods=['GET'])
def device_scenario(device_id):
    """ESP32 запрашивает сценарий."""
    return devices.get_device_scenario(device_id)

# Маршруты для ANDROID
@app.route('/api/device/<device_id>/data', methods=['GET'])
def get_device_data(device_id):
    """Android получает последние данные датчиков."""
    return devices.get_device_data(device_id)

@app.route('/api/device/<device_id>/pump/toggle', methods=['POST'])
def toggle_pump(device_id):
    """Android переключает насос."""
    return devices.toggle_pump(device_id)

@app.route('/api/device/<device_id>/pump/status', methods=['GET'])
def pump_status(device_id):
    """Android запрашивает состояние насоса."""
    return devices.get_pump_status(device_id)

# Системные маршруты
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "database": "connected"}), 200

@app.route('/api/info', methods=['GET'])
def server_info():
    return jsonify({
        "server_name": "Plant Care Server",
        "version": "1.0.0",
        "api_version": "v1"
    }), 200

# Обработчики ошибок
@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Ресурс не найден"}), 404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"success": False, "error": "Некорректный запрос"}), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({"success": False, "error": "Неавторизован"}), 401

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Внутренняя ошибка сервера"}), 500

'''@app.route('/api/device/<device_id>/notifications', methods=['GET'])
def device_notifications(device_id):
    return devices.get_notifications(device_id)
    '''

# Запуск
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)