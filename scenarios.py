# scenarios - модуль для работы со сценариями
# Он отвечает за получение публичных и созданных пользователем сценариев, создание сценария и привязку сценария к пользователю
# Используемые библиотеки
from flask import request # Для получения HTTP-запросов
from flask import jsonify # Для преобразования данных в JSON-ответ, который можно отдать клиенту
import datetime # Для создания времени получения данных
from database import query_db, execute_db # Для работы с SQL-запросами


from config import Config
from database import DATABASE


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

        # УДАЛЁН plant_name ИЗ ЗАПРОСА
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

        
def get_all_scenarios(): # Получает все публичные сценарии.
    # Пробуем получить список сценариев
    try:
        scenarios = query_db("""
            SELECT iid, nam, min_temperature, max_temperature,
                   min_soil_moisture, max_soil_moisture,
                   min_humidity, max_humidity,
                   min_light_lux, max_light_lux
            FROM scenarios 
            WHERE created_by IS NULL
        """)
        # Создаём пустой (пока) список сценариев
        result = []
        for us in user_scenarios:
            # УДАЛЁН plant_name, используем только scenario_name
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
        # Выводим список публичных сценариев как JSON-ответ с кодом 200
        return jsonify({
            "success": True,
            "scenarios_of_user": result,
            "count": len(result),
            "user_id": user['id'],
            "username": user['username']
        }), 200
    # Если произошла какая-то неизвестная ошибка, то так и говорим
    except Exception as e:
        print(f"Error in get_all_scenarios: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

    except Exception as e:
        print(f"Error in get_user_scenarios: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Внутренняя ошибка сервера",
            "message": f"Ошибка: {str(e)}"
        }), 500

def create_scenario(): # Создаёт новый сценарий для пользователя и автоматически привязать его.
    # Сначала пробуем получить данные из тела запроса (если там ничего нет, то данных нет)
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400
    # Если есть, то переписываем их в переменные почты и имени растения
    email = data.get('username') or data.get('email')
    plant_name = data.get('nam')  # Имя растения/сценария
    # Если переменная почты пуста, значит, почта не указана
    if not email:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401
    # Если переменная имени растения пуста или там нет букв, значит, имя не указано верно
    if not plant_name or not plant_name.strip():
        return jsonify({"success": False, "message": "Не указано имя растения"}), 400
    # Пробуем создать новый сценарий
    try:
        # Пробуем найти пользователя, для которого создаётся сценарий (если его нет, так и говорим)
        user = query_db(
            "SELECT iid, username FROM users WHERE username = ?",
            [email], one=True
        )
        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401
        # Проверяем обязательные поля (если какого-то поля нет, так и говорим)
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
        # Если есть, то делаем предупреждение
        if existing_plant:
            print(f"Предупреждение: растение '{plant_name}' уже существует у пользователя")
        # Вставляем запись в таблицу
        execute_db(
            """
            INSERT INTO user_scenarios 
            (user_id, scenario_id, device_id, created_at, is_active, plant_name) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user['iid'], scenario_id, device_id, datetime.datetime.now(), 1, plant_name)
        )
        # Выводим успешно созданный сценарий как JSON-ответ с кодом 201
        return jsonify({
            "success": True,
            "message": "Сценарий успешно создан и привязан",
            "scenario_id": scenario_id,
            "user_id": user['iid'],
            "plant_name": plant_name
        }), 201
    # Если произошла какая-то неизвестная ошибка, то так и говорим
    except Exception as e:
        print(f"Ошибка создания сценария: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500


def assign_scenario_to_user(): # Привязывает существующий сценарий к пользователю.
    # Сначала пробуем получить данные из тела запроса (если там ничего нет, то данных нет)
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400
    # Если есть, то переписываем их в переменные имени, id сценария и устройства и имени растения
    username = data.get('username') or data.get('email')
    scenario_id = data.get('scenario_id')
    device_id = data.get('device_id', 'esp32_default')
    plant_name = data.get('plant_name', '')
    # Если переменная имени пуста, значит, имя не указано
    if not username:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401
    # Если переменная id сценария пуста, значит, id сценария не указан
    if not scenario_id:
        return jsonify({"success": False, "message": "Не указан ID сценария"}), 400
    # Пробуем привязать существующий сценарий
    try:
        # Пробуем найти пользователя, для которого создаётся сценарий (если его нет, так и говорим)
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
        # Проверяем, не привязан ли уже этот сценарий с таким же именем растения
        # Используем все три поля для проверки
        existing = query_db(
            "SELECT 1 FROM user_scenarios WHERE user_id = ? AND scenario_id = ? AND device_id = ? AND plant_name = ?",
            [user['iid'], scenario_id, device_id, plant_name], one=True
        )
        # Если привязан, так и говорим
        if existing:
            return jsonify({
                "success": False,
                "message": f"Растение '{plant_name}' уже использует этот сценарий"
            }), 409
        # Привязываем сценарий, если не привязан
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
                # Если привязан, так и говорим
                if existing_with_new:
                    return jsonify({
                        "success": False,
                        "message": "Этот сценарий уже привязан к другому растению"
                    }), 409
                # Если нет, то привязываем к другому устройству и говорим, что привязали туда
                execute_db(
                    """
                    INSERT INTO user_scenarios 
                    (user_id, scenario_id, device_id, created_at, is_active, plant_name) 
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user['iid'], scenario_id, new_device_id, datetime.datetime.now(), 1, plant_name)
                )
                print(f"Использован новый device_id: {new_device_id}")
            # Если это не ошибка уникальности, то говорим, что это
            else:
                raise e
        # Получаем обновленное количество сценариев пользователя
        count = query_db(
            "SELECT COUNT(*) as count FROM user_scenarios WHERE user_id = ?",
            [user['iid']], one=True
        )
        # Выводим успешную привязку сценария к пользователю как JSON-ответ с кодом 201
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
    # Если произошла какая-то неизвестная ошибка, то так и говорим
    except Exception as e:
        print(f"Error in assign_scenario_to_user: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"}), 500


def get_user_scenarios(): # Получает сценарии пользователя.
    # Для начала пробуем получить данные из тела запроса (если нет, то нет)
    username = request.args.get('username') or request.args.get('email')
    if not username:
        return jsonify({"success": False, "message": "Необходимо указать email"}), 401
    # Пробуем получить сценарии пользователя
    try:
        # Пробуем найти пользователя, для которого создаётся сценарий (если его нет, так и говорим)
        user = query_db(
            "SELECT iid, username FROM users WHERE username = ?",
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
            FROM user_scenarios AS us
            INNER JOIN scenarios AS s ON us.scenario_id = s.iid
            LEFT OUTER JOIN scenarios AS orig ON s.original_scenario_id = orig.iid
            WHERE us.user_id = ?
            ORDER BY us.created_at DESC
        """, [user['iid']])
        # Создаём пустой (пока) список сценариев пользователя
        result = []
        # Добавляем туда сценарии
        for us in user_scenarios:
            # Для отображения используем plant_name (имя растения)
            display_name = us['plant_name'] if us['plant_name'] and us['plant_name'].strip() else us['scenario_name']
            # Уникальный идентификатор для каждой привязки
            unique_id = f"{us['user_id']}_{us['scenario_id']}_{us['plant_name']}_{us['created_at']}"
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
        # Выводим список созданных пользователем сценариев как JSON-ответ с кодом 200
        return jsonify({
            "success": True,
            "scenarios_of_user": result,
            "count": len(result),
            "user_id": user['iid'],
            "username": user['username']
        }), 200
    # Если произошла какая-то неизвестная ошибка, то так и говорим
    except Exception as e:
        print(f"Error in get_user_scenarios: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Внутренняя ошибка сервера",
            "message": f"Ошибка: {str(e)}"
        }), 500