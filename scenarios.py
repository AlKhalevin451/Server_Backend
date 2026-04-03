from flask import request, jsonify
from database import query_db, execute_db
import datetime


from config import Config
from database import DATABASE


def get_all_scenarios():

    """Получаем все публичные сценарии."""
    try:
        scenarios = query_db("""
            SELECT iid, nam, min_temperature, max_temperature,
                   min_soil_moisture, max_soil_moisture,
                   min_humidity, max_humidity,
                   min_light_lux, max_light_lux
            FROM scenarios 
            WHERE created_by IS NULL
        """)

        result = []
        for s in scenarios:
            result.append({
                "iid": s['iid'],
                "name": s['nam'],
                "min_temperature": s['min_temperature'],
                "max_temperature": s['max_temperature'],
                "min_soil_moisture": s['min_soil_moisture'],
                "max_soil_moisture": s['max_soil_moisture'],
                "min_humidity": s['min_humidity'],
                "max_humidity": s['max_humidity'],
                "min_light_lux": s['min_light_lux'],
                "max_light_lux": s['max_light_lux']
            })

        return jsonify({
            "success": True,
            "scenarios": result,
            "count": len(result)
        }), 200
    except Exception as e:
        print(f"Error in get_all_scenarios: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500


def create_scenario():
    """
    Создать новый сценарий для пользователя и автоматически привязать его.
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400

    email = data.get('username') or data.get('email')
    plant_name = data.get('nam')  # Имя растения/сценария

    if not email:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401

    if not plant_name or not plant_name.strip():
        return jsonify({"success": False, "message": "Не указано имя растения"}), 400

    try:
        user = query_db(
            "SELECT iid, username FROM users WHERE username = ?",
            [email], one=True
        )

        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401

        # Проверяем обязательные поля
        required_fields = ['nam', 'min_soil_moisture', 'max_soil_moisture']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Отсутствует поле: {field}"}), 400

        # Вставляем сценарий
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

        # Привязываем сценарий к пользователю
        device_id = data.get('device_id', 'esp32_default')

        # Проверяем, нет ли уже растения с таким именем
        existing_plant = query_db(
            "SELECT 1 FROM user_scenarios WHERE user_id = ? AND plant_name = ?",
            [user['iid'], plant_name], one=True
        )

        if existing_plant:
            # Можно либо запретить, либо разрешить (сделаем предупреждение)
            print(f"Предупреждение: растение '{plant_name}' уже существует у пользователя")

        execute_db(
            """
            INSERT INTO user_scenarios 
            (user_id, scenario_id, device_id, created_at, is_active, plant_name) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user['iid'], scenario_id, device_id, datetime.datetime.now(), 1, plant_name)
        )

        return jsonify({
            "success": True,
            "message": "Сценарий успешно создан и привязан",
            "scenario_id": scenario_id,
            "user_id": user['iid'],
            "plant_name": plant_name
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
    plant_name = data.get('plant_name', '')

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

        # Получаем данные сценария
        scenario = query_db("SELECT * FROM scenarios WHERE iid = ?", [scenario_id], one=True)
        if not scenario:
            return jsonify({"success": False, "message": "Сценарий не найден"}), 404

        # Проверяем, не привязан ли уже этот сценарий с ТАКИМ ЖЕ ИМЕНЕМ РАСТЕНИЯ
        # Используем все три поля для проверки
        existing = query_db(
            "SELECT 1 FROM user_scenarios WHERE user_id = ? AND scenario_id = ? AND device_id = ? AND plant_name = ?",
            [user['iid'], scenario_id, device_id, plant_name], one=True
        )

        if existing:
            return jsonify({
                "success": False,
                "message": f"Растение '{plant_name}' уже использует этот сценарий"
            }), 409

        # Привязываем сценарий
        try:
            execute_db(
                """
                INSERT INTO user_scenarios 
                (user_id, scenario_id, device_id, created_at, is_active, plant_name) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user['iid'], scenario_id, device_id, datetime.datetime.now(), 1, plant_name)
            )
        except Exception as e:
            # Если ошибка уникальности, пробуем с другим device_id
            if "UNIQUE constraint failed" in str(e):
                # Генерируем уникальный device_id на основе имени растения
                new_device_id = f"esp32_{plant_name.replace(' ', '_')}_{scenario_id}"

                # Проверяем еще раз
                existing_with_new = query_db(
                    "SELECT 1 FROM user_scenarios WHERE user_id = ? AND scenario_id = ? AND device_id = ?",
                    [user['iid'], scenario_id, new_device_id], one=True
                )

                if existing_with_new:
                    return jsonify({
                        "success": False,
                        "message": "Этот сценарий уже привязан к другому растению"
                    }), 409

                execute_db(
                    """
                    INSERT INTO user_scenarios 
                    (user_id, scenario_id, device_id, created_at, is_active, plant_name) 
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user['iid'], scenario_id, new_device_id, datetime.datetime.now(), 1, plant_name)
                )
                print(f"Использован новый device_id: {new_device_id}")
            else:
                raise e

        # Получаем обновленное количество
        count = query_db(
            "SELECT COUNT(*) as count FROM user_scenarios WHERE user_id = ?",
            [user['iid']], one=True
        )

        return jsonify({
            "success": True,
            "message": "Сценарий успешно привязан к пользователю",
            "user_id": user['iid'],
            "scenario_id": scenario_id,
            "scenario_name": scenario['nam'],
            "plant_name": plant_name,
            "device_id": device_id,
            "total_user_scenarios": count['count'] if count else 0
        }), 201

    except Exception as e:
        print(f"Error in assign_scenario_to_user: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"}), 500

def get_user_scenarios():
    """Получить сценарии пользователя."""
    username = request.args.get('username') or request.args.get('email')

    if not username:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401

    try:
        user = query_db(
            "SELECT id, username FROM users WHERE username = ?",
            [username], one=True
        )

        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401

        # Получаем все сценарии пользователя
        user_scenarios = query_db("""
            SELECT 
                us.user_id,
                us.scenario_id, 
                us.device_id, 
                us.is_active, 
                us.created_at,
                s.name as scenario_name,
                s.min_temperature,
                s.max_temperature,
                s.min_soil_moisture,
                s.max_soil_moisture,
                s.min_humidity,
                s.max_humidity,
                s.min_light_lux,
                s.max_light_lux,
                s.original_scenario_id,
                orig.name as original_scenario_name
            FROM user_scenarios us
            INNER JOIN scenarios AS s ON us.scenario_id = s.id
            LEFT OUTER JOIN scenarios AS orig ON s.original_scenario_id = orig.id
            WHERE us.user_id = ?
            ORDER BY us.created_at DESC
        """, [user['id']])

        result = []
        for us in user_scenarios:
            # Для отображения используем scenario_name (имя сценария)
            display_name = us['scenario_name']

            # Уникальный идентификатор для каждой привязки
            unique_id = f"{us['user_id']}_{us['scenario_id']}_{us['created_at']}"

            result.append({
                "unique_id": unique_id,
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
            "user_id": user['id'],
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