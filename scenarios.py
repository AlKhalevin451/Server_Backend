from flask import request, jsonify
from database import query_db, execute_db
import datetime
<<<<<<< HEAD


=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
from config import Config
from database import DATABASE


def get_all_scenarios():
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
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
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
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
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
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
<<<<<<< HEAD
    # 🔍 ОТЛАДКА: выводим полученные данные
    print("=== DEBUG: create_scenario received data ===")
    print(data)
    print("============================================")
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400

    email = data.get('username') or data.get('email')
    plant_name = data.get('nam')  # Имя растения/сценария

    if not email:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401

    if not plant_name or not plant_name.strip():
        return jsonify({"success": False, "message": "Не указано имя растения"}), 400

=======
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400
    email = data.get('username') or data.get('email')
    plant_name = data.get('nam')  # Имя растения/сценария
    if not email:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401
    if not plant_name or not plant_name.strip():
        return jsonify({"success": False, "message": "Не указано имя растения"}), 400
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    try:
        user = query_db(
            "SELECT iid, username FROM users WHERE username = ?",
            [email], one=True
        )
<<<<<<< HEAD

        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401

=======
        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        # Проверяем обязательные поля
        required_fields = ['nam', 'min_soil_moisture', 'max_soil_moisture']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Отсутствует поле: {field}"}), 400
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
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
<<<<<<< HEAD

        # Привязываем сценарий к пользователю
        device_id = data.get('device_id', 'esp32_default')

=======
        # Привязываем сценарий к пользователю
        device_id = data.get('device_id', 'esp32_default')
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        # Проверяем, нет ли уже растения с таким именем
        existing_plant = query_db(
            "SELECT 1 FROM user_scenarios WHERE user_id = ? AND plant_name = ?",
            [user['iid'], plant_name], one=True
        )
<<<<<<< HEAD

        if existing_plant:
            # Можно либо запретить, либо разрешить (сделаем предупреждение)
            print(f"Предупреждение: растение '{plant_name}' уже существует у пользователя")

=======
        if existing_plant:
            # Сделаем предупреждение
            print(f"Предупреждение: растение '{plant_name}' уже существует у пользователя")
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        execute_db(
            """
            INSERT INTO user_scenarios 
            (user_id, scenario_id, device_id, created_at, is_active, plant_name) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user['iid'], scenario_id, device_id, datetime.datetime.now(), 1, plant_name)
        )
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        return jsonify({
            "success": True,
            "message": "Сценарий успешно создан и привязан",
            "scenario_id": scenario_id,
            "user_id": user['iid'],
            "plant_name": plant_name
        }), 201
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
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
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    username = data.get('username') or data.get('email')
    scenario_id = data.get('scenario_id')
    device_id = data.get('device_id', 'esp32_default')
    plant_name = data.get('plant_name', '')
<<<<<<< HEAD

    if not username:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401

    if not scenario_id:
        return jsonify({"success": False, "message": "Не указан ID сценария"}), 400

=======
    if not username:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401
    if not scenario_id:
        return jsonify({"success": False, "message": "Не указан ID сценария"}), 400
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    try:
        user = query_db(
            "SELECT iid, username FROM users WHERE username = ?",
            [username], one=True
        )
<<<<<<< HEAD

        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401

=======
        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        # Получаем данные сценария
        scenario = query_db("SELECT * FROM scenarios WHERE iid = ?", [scenario_id], one=True)
        if not scenario:
            return jsonify({"success": False, "message": "Сценарий не найден"}), 404
<<<<<<< HEAD

        # Проверяем, не привязан ли уже этот сценарий с ТАКИМ ЖЕ ИМЕНЕМ РАСТЕНИЯ
=======
        # Проверяем, не привязан ли уже этот сценарий с таким же именем растения
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        # Используем все три поля для проверки
        existing = query_db(
            "SELECT 1 FROM user_scenarios WHERE user_id = ? AND scenario_id = ? AND device_id = ? AND plant_name = ?",
            [user['iid'], scenario_id, device_id, plant_name], one=True
        )
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        if existing:
            return jsonify({
                "success": False,
                "message": f"Растение '{plant_name}' уже использует этот сценарий"
            }), 409
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
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
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
                # Проверяем еще раз
                existing_with_new = query_db(
                    "SELECT 1 FROM user_scenarios WHERE user_id = ? AND scenario_id = ? AND device_id = ?",
                    [user['iid'], scenario_id, new_device_id], one=True
                )
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
                if existing_with_new:
                    return jsonify({
                        "success": False,
                        "message": "Этот сценарий уже привязан к другому растению"
                    }), 409
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
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
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        # Получаем обновленное количество
        count = query_db(
            "SELECT COUNT(*) as count FROM user_scenarios WHERE user_id = ?",
            [user['iid']], one=True
        )
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
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
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    except Exception as e:
        print(f"Error in assign_scenario_to_user: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"}), 500

<<<<<<< HEAD
def get_user_scenarios():
    """Получить сценарии пользователя."""
    username = request.args.get('username') or request.args.get('email')

    if not username:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401

=======

def get_user_scenarios():
    """Получить сценарии пользователя."""
    username = request.args.get('username') or request.args.get('email')
    if not username:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    try:
        user = query_db(
            "SELECT iid, username FROM users WHERE username = ?",
            [username], one=True
        )
<<<<<<< HEAD

        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401

=======
        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        # Получаем все сценарии пользователя
        user_scenarios = query_db("""
            SELECT 
                us.user_id,
                us.scenario_id, 
                us.device_id, 
                us.is_active, 
                us.created_at,
                us.plant_name,
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
<<<<<<< HEAD
            FROM user_scenarios us
            JOIN scenarios s ON us.scenario_id = s.iid
            LEFT JOIN scenarios orig ON s.original_scenario_id = orig.iid
            WHERE us.user_id = ?
            ORDER BY us.created_at DESC
        """, [user['iid']])

=======
            FROM user_scenarios AS us
            INNER JOIN scenarios AS s ON us.scenario_id = s.iid
            LEFT OUTER JOIN scenarios orig ON s.original_scenario_id = orig.iid
            WHERE us.user_id = ?
            ORDER BY us.created_at DESC
        """, [user['iid']])
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        result = []
        for us in user_scenarios:
            # Для отображения используем plant_name (имя растения)
            display_name = us['plant_name'] if us['plant_name'] and us['plant_name'].strip() else us['scenario_name']
<<<<<<< HEAD

            # Уникальный идентификатор для каждой привязки
            unique_id = f"{us['user_id']}_{us['scenario_id']}_{us['plant_name']}_{us['created_at']}"

=======
            # Уникальный идентификатор для каждой привязки
            unique_id = f"{us['user_id']}_{us['scenario_id']}_{us['plant_name']}_{us['created_at']}"
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
            result.append({
                "unique_id": unique_id,  # Уникальный ID для каждой записи
                "assignment_id": f"{us['user_id']}_{us['scenario_id']}",
                "user_id": us['user_id'],
                "scenario_id": us['scenario_id'],
                "scenario_name": us['scenario_name'],
                "plant_name": us['plant_name'],
                "display_name": display_name,  # Имя для отображения (имя растения)
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
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        return jsonify({
            "success": True,
            "scenarios_of_user": result,
            "count": len(result),
            "user_id": user['iid'],
            "username": user['username']
        }), 200
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    except Exception as e:
        print(f"Error in get_user_scenarios: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Внутренняя ошибка сервера",
            "message": f"Ошибка: {str(e)}"
        }), 500