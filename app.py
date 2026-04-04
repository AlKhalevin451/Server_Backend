from flask import Flask, jsonify, request
from database import init_db, close_db
from asgiref.wsgi import WsgiToAsgi
import os
import auth
import scenarios
import devices
from mqtt_service import init_mqtt


app = Flask(__name__)
mqtt = init_mqtt(app)

if mqtt:
    devices.set_mqtt_service(mqtt)
    print("MQTT сервис инициализирован")
else:
    print("MQTT сервис не инициализирован")


with app.app_context():
    init_db()
    from config import Config
    config = Config()
    config.make_base_scenarios('plantcare.db')

asgi_app = WsgiToAsgi(app)


@app.teardown_appcontext
def shutdown_session(exception=None):
    close_db()


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
                "pump_on": "POST /api/device/<device_id>/pump/on",
                "pump_off": "POST /api/device/<device_id>/pump/off",
                "pump_status": "GET /api/device/<device_id>/pump/status",
                "notifications": "GET /api/device/<device_id>/notifications"
            },
            "Система": {
                "health": "GET /api/health",
                "info": "GET /api/info"
            }
        }
    }), 200


# Добавьте в app.py временный эндпоинт
@app.route('/fixdb', methods=['GET'])
def fix_database_route():
    import sqlite3
    DATABASE = 'plantcare.db'
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE user_scenarios ADD COLUMN plant_name TEXT DEFAULT NULL")
        result = "✅ Колонка plant_name добавлена"
    except Exception as e:
        result = f"⚠ Ошибка: {e}"
    conn.commit()
    conn.close()
    return jsonify({"result": result})


@app.route('/auth/register', methods=['POST'])
def register():
    return auth.register_user()


@app.route('/api/login', methods=['POST'])
def login():
    return auth.login_user()


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


@app.route('/api/device/data', methods=['POST'])
def device_data():
    return devices.process_sensor_data()


@app.route('/api/device/<device_id>/scenario', methods=['GET'])
def device_scenario(device_id):
    return devices.get_device_scenario(device_id)


@app.route('/api/device/<device_id>/data', methods=['GET'])
def get_device_data(device_id):
    return devices.get_device_data(device_id)


@app.route('/api/device/<device_id>/pump/toggle', methods=['POST'])
def toggle_pump(device_id):
    return devices.toggle_pump(device_id)


@app.route('/api/device/<device_id>/pump/on', methods=['POST'])
def pump_on(device_id):
    return devices.pump_on(device_id)


@app.route('/api/device/<device_id>/pump/off', methods=['POST'])
def pump_off(device_id):
    return devices.pump_off(device_id)


@app.route('/api/device/<device_id>/pump/status', methods=['GET'])
def pump_status(device_id):
    return devices.get_pump_status(device_id)


@app.route('/api/device/<device_id>/notifications', methods=['GET'])
def get_notifications(device_id):
    return devices.get_notifications(device_id)


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "database": "connected", "mqtt": mqtt is not None}), 200


@app.route('/api/info', methods=['GET'])
def server_info():
    return jsonify({
        "server_name": "Plant Care Server",
        "version": "1.0.0",
        "api_version": "v1"
    }), 200


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


@app.route('/api/user/scenarios/delete', methods=['POST'])
def delete_user_scenario():
    """Удалить привязку сценария к пользователю"""
    data = request.get_json()
    username = data.get('username')
    scenario_name = data.get('scenario_name')

    if not username or not scenario_name:
        return jsonify({"success": False, "message": "Не указаны username или scenario_name"}), 400

    try:
        # Находим пользователя
        user = query_db("SELECT id FROM users WHERE username = ?", [username], one=True)
        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 404

        # Находим сценарий
        scenario = query_db("SELECT id FROM scenarios WHERE name = ?", [scenario_name], one=True)
        if not scenario:
            return jsonify({"success": False, "message": "Сценарий не найден"}), 404

        # Удаляем привязку
        execute_db("""
            DELETE FROM user_scenarios 
            WHERE user_id = ? AND scenario_id = ?
        """, (user['id'], scenario['id']))

        return jsonify({"success": True, "message": "Сценарий удален"}), 200

    except Exception as e:
        print(f"Error deleting scenario: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)