from flask import request, jsonify
from database import query_db, execute_db
import datetime

def get_user_scenarios():
    """Получить сценарии пользователя."""
    username = request.args.get('username') or request.args.get('email')

    if not username:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401

    try:
        user = query_db(
            "SELECT iid, username FROM users WHERE username = ?",
            [username], one=True
        )

        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401

        user_scenarios = query_db("""
            SELECT 
                us.user_id,
                us.scenario_id, 
                us.device_id, 
                us.is_active, 
                us.created_at,
                s.nam as scenario_name,
                s.min_temperature,
                s.max_temperature,
                s.min_soil_moisture,
                s.max_soil_moisture,
                s.min_humidity,
                s.max_humidity,
                s.min_light_lux,
                s.max_light_lux,
                s.original_scenario_id,
                orig.nam as original_scenario_name
            FROM user_scenarios us
            INNER JOIN scenarios AS s ON us.scenario_id = s.iid
            LEFT OUTER JOIN scenarios AS orig ON s.original_scenario_id = orig.iid
            WHERE us.user_id = ?
            ORDER BY us.created_at DESC
        """, [user['iid']])

        result = []
        for us in user_scenarios:
            display_name = us['scenario_name']
            result.append({
                "unique_id": f"{us['user_id']}_{us['scenario_id']}_{us['created_at']}",
                "assignment_id": f"{us['user_id']}_{us['scenario_id']}",
                "user_id": us['user_id'],
                "scenario_id": us['scenario_id'],
                "scenario_name": us['scenario_name'],
                "display_name": display_name,
                "device_id": us['device_id'],
                "is_active": bool(us['is_active']),
                "created_at": us['created_at'],
                "min_temperature": us['min_temperature'],
                "max_temperature": us['max_temperature'],
                "min_soil_moisture": us['min_soil_moisture'],
                "max_soil_moisture": us['max_soil_moisture'],
                "min_humidity": us['min_humidity'],
                "max_humidity": us['max_humidity'],
                "min_light_lux": us['min_light_lux'],
                "max_light_lux": us['max_light_lux'],
                "original_scenario_id": us['original_scenario_id'],
                "original_scenario_name": us['original_scenario_name'],
                "is_copy": us['original_scenario_id'] is not None
            })

        return jsonify({
            "success": True,
            "scenarios_of_user": result,
            "count": len(result),
            "user_id": user['iid'],
            "username": user['username']
        }), 200

    except Exception as e:
        print(f"Error in get_user_scenarios: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Внутренняя ошибка сервера",
            "message": f"Ошибка: {str(e)}"
        }), 500

def create_scenario():
    """Создать новый сценарий для пользователя."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400

    email = data.get('username') or data.get('email')
    plant_name = data.get('nam')

    if not email:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401

    if not plant_name or not plant_name.strip():
        return jsonify({"success": False, "message": "Не указано имя сценария"}), 400

    try:
        user = query_db(
            "SELECT iid, username FROM users WHERE username = ?",
            [email], one=True
        )

        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401

        scenario_id = execute_db(
            """
            INSERT INTO scenarios 
            (nam, min_temperature, max_temperature, min_soil_moisture, max_soil_moisture, 
             min_humidity, max_humidity, min_light_lux, max_light_lux, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plant_name,
                data.get('min_temperature', 1000.0),
                data.get('max_temperature', 1000.0),
                data.get('min_soil_moisture', 1000.0),
                data.get('max_soil_moisture', 1000.0),
                data.get('min_humidity', 1000.0),
                data.get('max_humidity', 1000.0),
                data.get('min_light_lux', 1000.0),
                data.get('max_light_lux', 1000.0),
                user['iid']
            )
        )

        device_id = data.get('device_id', 'esp32_default')

        execute_db(
            """
            INSERT INTO user_scenarios 
            (user_id, scenario_id, device_id, created_at, is_active) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (user['iid'], scenario_id, device_id, datetime.datetime.now(), 1)
        )

        return jsonify({
            "success": True,
            "message": "Сценарий успешно создан",
            "scenario_id": scenario_id,
            "user_id": user['iid']
        }), 201

    except Exception as e:
        print(f"Ошибка создания сценария: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

def assign_scenario_to_user():
    """Привязать существующий сценарий к пользователю."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400

    username = data.get('username') or data.get('email')
    scenario_id = data.get('scenario_id')
    device_id = data.get('device_id', 'esp32_default')

    if not username:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401

    if not scenario_id:
        return jsonify({"success": False, "message": "Не указан ID сценария"}), 400

    try:
        user = query_db(
            "SELECT iid, username FROM users WHERE username = ?",
            [username], one=True
        )

        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401

        scenario = query_db("SELECT * FROM scenarios WHERE iid = ?", [scenario_id], one=True)
        if not scenario:
            return jsonify({"success": False, "message": "Сценарий не найден"}), 404

        existing = query_db(
            "SELECT 1 FROM user_scenarios WHERE user_id = ? AND scenario_id = ? AND device_id = ?",
            [user['iid'], scenario_id, device_id], one=True
        )

        if existing:
            return jsonify({
                "success": False,
                "message": "Этот сценарий уже привязан к устройству"
            }), 409

        execute_db(
            """
            INSERT INTO user_scenarios 
            (user_id, scenario_id, device_id, created_at, is_active) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (user['iid'], scenario_id, device_id, datetime.datetime.now(), 1)
        )

        return jsonify({
            "success": True,
            "message": "Сценарий успешно привязан"
        }), 201

    except Exception as e:
        print(f"Error in assign_scenario_to_user: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"}), 500