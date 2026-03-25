# services/scenario_service.py
"""
ScenarioService - сервис для работы со сценариями ухода за растениями.
Использует модели для типобезопасности и структурирования данных.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from models_for_scenario import Scenario, DeviceScenario
from database import query_db, execute_db


class ScenarioService:
    """
    Сервис для управления сценариями ухода за растениями.
    Отвечает за CRUD-операции со сценариями и их назначение устройствам.
    """
<<<<<<< HEAD

=======
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    def __init__(self):
        """
        Инициализация ScenarioService.
        Создает кэш для хранения сценариев устройств в памяти.
        """
<<<<<<< HEAD
        self._scenario_cache = {}  # Кэш: {device_id: {"data": DeviceScenario, "cached_at": datetime}}
=======
        # Кэш хранит объекты DeviceScenario для каждого device_id с меткой времени.
        # Структура: {device_id: {"data": DeviceScenario, "cached_at": datetime}}
        self._scenario_cache = {}

>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f

    def get_device_scenario(self, device_id: str) -> Optional[DeviceScenario]:
        """
        Получает активный сценарий для устройства.
        Args:
            device_id: Идентификатор устройства (например, "ESP32_001")
        Returns:
            DeviceScenario: Объект с данными сценария или None
        """
        # Проверка кэша
<<<<<<< HEAD
        if device_id in self._scenario_cache:
            cached_data = self._scenario_cache[device_id]
            cache_age = (datetime.now() - cached_data["cached_at"]).seconds
            if cache_age < 300:  # 300 секунд = 5 минут
                return cached_data["data"]
            else:
                del self._scenario_cache[device_id]

        # SQL-запрос для получения активного сценария устройства
        # Используем алиас s.nam AS plant_name для совместимости с моделью
=======
        # Если для данного device_id есть запись в кэше, проверяем её возраст.
        if device_id in self._scenario_cache:
            cached_data = self._scenario_cache[device_id]
            # Вычисляем возраст кэша в секундах.
            cache_age = (datetime.now() - cached_data["cached_at"]).seconds
            # Если кэш не старше 5 минут (300 секунд), возвращаем сохранённые данные.
            if cache_age < 300:
                return cached_data["data"]
            else:
                # Если кэш устарел, удаляем его и идём в базу данных.
                del self._scenario_cache[device_id]

        # Запрос к базе данных
        # Ищем активный сценарий для данного устройства.
        # Используем INNER JOIN с таблицей user_scenarios, где хранятся назначения.
        # Поле s.nam (название растения) переименовываем в plant_name для совместимости с моделью.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        row = query_db("""
            SELECT 
                s.iid,
                s.nam AS plant_name,
                s.min_temperature, s.max_temperature,
                s.min_soil_moisture, s.max_soil_moisture,
                s.min_humidity, s.max_humidity,
                s.min_light_lux, s.max_light_lux,
                s.created_by, s.created_at,
                us.created_at as assigned_at
<<<<<<< HEAD
            FROM scenarios s
=======
            FROM scenarios AS s
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
            INNER JOIN user_scenarios us ON s.iid = us.scenario_id
            WHERE us.device_id = ? AND us.is_active = 1
            ORDER BY us.created_at DESC
            LIMIT 1
        """, [device_id], one=True)
<<<<<<< HEAD

        if not row:
            return None

        row_dict = dict(row)
=======
        # Если ничего не найдено, возвращаем None.
        if not row:
            return None
        # Преобразуем полученную строку в словарь для удобного доступа по именам.
        row_dict = dict(row)
        # Создаём объект Scenario, приводя типы к нужным (int, float).
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        scenario = Scenario(
            iid=int(row_dict['iid']),
            plant_name=row_dict['plant_name'],
            min_temperature=float(row_dict['min_temperature']),
            max_temperature=float(row_dict['max_temperature']),
            min_soil_moisture=int(row_dict['min_soil_moisture']),
            max_soil_moisture=int(row_dict['max_soil_moisture']),
            min_humidity=int(row_dict['min_humidity']),
            max_humidity=int(row_dict['max_humidity']),
            min_light_lux=int(row_dict['min_light_lux']),
            max_light_lux=int(row_dict['max_light_lux']),
            created_by=int(row_dict['created_by'])
        )
<<<<<<< HEAD

=======
        # Оборачиваем сценарий в объект DeviceScenario, добавляя device_id.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        device_scenario = DeviceScenario(
            device_id=device_id,
            scenario=scenario
        )
<<<<<<< HEAD

=======
        # Сохраняем результат в кэш с текущей временной меткой.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        self._scenario_cache[device_id] = {
            "data": device_scenario,
            "cached_at": datetime.now()
        }
<<<<<<< HEAD
        return device_scenario

=======
        # Возвращаем объект DeviceScenario.
        return device_scenario


>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    def assign_scenario_to_device(self, user_id: int, scenario_id: int,
                                  device_id: str) -> bool:
        """
        Назначает сценарий устройству пользователя.
        Args:
            user_id: ID пользователя, который делает назначение
            scenario_id: ID сценария для назначения
            device_id: ID устройства, которому назначается сценарий
        Returns:
            bool: True если назначение успешно
        Raises:
            ValueError: Если сценарий не найден или недоступен пользователю
        """
<<<<<<< HEAD
        # Проверка существования сценария и прав пользователя
=======
        # Проверка существования и доступности сценария
        # Сценарий доступен, если он системный (created_by IS NULL) или создан этим пользователем.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        scenario_row = query_db("""
            SELECT * FROM scenarios 
            WHERE iid = ? AND (created_by IS NULL OR created_by = ?)
        """, [scenario_id, user_id], one=True)
<<<<<<< HEAD

=======
        # Если сценарий не найден или не принадлежит пользователю, выбрасываем исключение.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        if not scenario_row:
            raise ValueError(
                f"Сценарий с ID {scenario_id} не найден или недоступен пользователю {user_id}"
            )
<<<<<<< HEAD

        # Деактивируем все текущие сценарии для этого устройства
=======
        # Устанавливаем is_active = 0 для всех записей пользователя с данным device_id.
        # Это гарантирует, что у устройства останется только один активный сценарий.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        execute_db("""
            UPDATE user_scenarios 
            SET is_active = 0 
            WHERE user_id = ? AND device_id = ?
        """, [user_id, device_id])
<<<<<<< HEAD

        # Проверяем, существует ли уже связь в БД
=======
        # Проверка, существует ли уже связь (user_id, scenario_id, device_id) в БД
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        existing_link = query_db("""
            SELECT user_id, scenario_id
            FROM user_scenarios 
            WHERE user_id = ? AND scenario_id = ? AND device_id = ?
        """, [user_id, scenario_id, device_id], one=True)
<<<<<<< HEAD

        if existing_link:
            # Связь существует - активируем её
=======
        if existing_link:
            # Если связь уже существует, просто активируем её и обновляем время создания.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
            execute_db("""
                UPDATE user_scenarios 
                SET is_active = 1, created_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND scenario_id = ?
            """, [existing_link['user_id'], existing_link['scenario_id']])
        else:
<<<<<<< HEAD
            # Связи нет - создаём новую
=======
            # Если связи нет, создаём новую запись с активным статусом.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
            execute_db("""
                INSERT INTO user_scenarios (user_id, scenario_id, device_id, is_active)
                VALUES (?, ?, ?, 1)
            """, [user_id, scenario_id, device_id])
<<<<<<< HEAD

        # Очистка кэша для этого устройства
        if device_id in self._scenario_cache:
            del self._scenario_cache[device_id]

        return True

=======
        # Удаляем запись из кэша, чтобы при следующем запросе данные загрузились из БД.
        if device_id in self._scenario_cache:
            del self._scenario_cache[device_id]
        # Возвращаем True в знак успешного назначения.
        return True


>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    def get_available_scenarios(self, user_id: Optional[int] = None) -> List[Scenario]:
        """
        Получает список сценариев, доступных пользователю.
        Args:
            user_id: ID пользователя или None для системных сценариев
        Returns:
            List[Scenario]: Список объектов Scenario
        """
<<<<<<< HEAD
=======
        # Если user_id не передан (None), возвращаем только системные сценарии (created_by IS NULL).
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        if user_id is None:
            rows = query_db("""
                SELECT * FROM scenarios 
                WHERE created_by IS NULL
                ORDER BY iid
            """)
        else:
<<<<<<< HEAD
=======
            # Если user_id передан, возвращаем системные сценарии и созданные этим пользователем.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
            rows = query_db("""
                SELECT * FROM scenarios 
                WHERE created_by IS NULL OR created_by = ?
                ORDER BY created_by, iid
            """, [user_id])
<<<<<<< HEAD

        scenarios = []
        for row in rows:
            row_dict = dict(row)
            # Преобразуем ключ nam -> plant_name для совместимости с моделью
            row_dict['plant_name'] = row_dict.pop('nam')
=======
        # Преобразуем каждую строку результата в объект Scenario.
        scenarios = []
        for row in rows:
            row_dict = dict(row)
            # Переименовываем поле nam в plant_name, так как модель ожидает plant_name.
            row_dict['plant_name'] = row_dict.pop('nam')
            # Создаём объект Scenario с правильными типами.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
            scenario = Scenario(
                iid=int(row_dict['iid']),
                plant_name=row_dict['plant_name'],
                min_temperature=float(row_dict['min_temperature']),
                max_temperature=float(row_dict['max_temperature']),
                min_soil_moisture=int(row_dict['min_soil_moisture']),
                max_soil_moisture=int(row_dict['max_soil_moisture']),
                min_humidity=int(row_dict['min_humidity']),
                max_humidity=int(row_dict['max_humidity']),
                min_light_lux=int(row_dict['min_light_lux']),
                max_light_lux=int(row_dict['max_light_lux']),
                created_by=int(row_dict['created_by'])
            )
            scenarios.append(scenario)
        return scenarios

<<<<<<< HEAD
=======

>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    def create_scenario(self, user_id: int, scenario_data: Dict[str, Any]) -> Scenario:
        """
        Создаёт новый сценарий для пользователя.
        Args:
            user_id: ID пользователя, создающего сценарий
            scenario_data: Данные нового сценария (должны содержать ключ 'plant_name')
        Returns:
            Scenario: Созданный объект Scenario с заполненным ID
        Raises:
            ValueError: Если данные некорректны
        """
<<<<<<< HEAD
        errors = self._validate_scenario_data(scenario_data)
        if errors:
            raise ValueError("; ".join(errors))

=======
        # Валидируем входные данные с помощью внутреннего метода.
        errors = self._validate_scenario_data(scenario_data)
        if errors:
            # Если есть ошибки, объединяем их через точку с запятой и выбрасываем исключение.
            raise ValueError("; ".join(errors))
        # Вставляем новую запись в таблицу scenarios.
        # Поле nam получает значение из ключа 'plant_name' словаря.
        # created_by устанавливается в переданный user_id.
        # created_at заполняется текущим временем через SQLite CURRENT_TIMESTAMP.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        scenario_id = execute_db("""
            INSERT INTO scenarios (
                nam,
                min_temperature, max_temperature,
                min_soil_moisture, max_soil_moisture,
                min_humidity, max_humidity,
                min_light_lux, max_light_lux,
                created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            scenario_data['plant_name'],
            scenario_data['min_temperature'],
            scenario_data['max_temperature'],
            scenario_data['min_soil_moisture'],
            scenario_data['max_soil_moisture'],
            scenario_data['min_humidity'],
            scenario_data['max_humidity'],
            scenario_data['min_light_lux'],
            scenario_data['max_light_lux'],
            user_id
        ))
<<<<<<< HEAD

        new_row = query_db("SELECT * FROM scenarios WHERE iid = ?", [scenario_id], one=True)
        row_dict = dict(new_row)
        row_dict['plant_name'] = row_dict.pop('nam')
=======
        # После вставки запрашиваем только что созданную запись, чтобы получить все поля.
        new_row = query_db("SELECT * FROM scenarios WHERE iid = ?", [scenario_id], one=True)
        row_dict = dict(new_row)
        # Снова переименовываем nam в plant_name.
        row_dict['plant_name'] = row_dict.pop('nam')
        # Создаём объект Scenario.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        scenario = Scenario(
            iid=int(row_dict['iid']),
            plant_name=row_dict['plant_name'],
            min_temperature=float(row_dict['min_temperature']),
            max_temperature=float(row_dict['max_temperature']),
            min_soil_moisture=int(row_dict['min_soil_moisture']),
            max_soil_moisture=int(row_dict['max_soil_moisture']),
            min_humidity=int(row_dict['min_humidity']),
            max_humidity=int(row_dict['max_humidity']),
            min_light_lux=int(row_dict['min_light_lux']),
            max_light_lux=int(row_dict['max_light_lux']),
            created_by=int(row_dict['created_by'])
        )
        return scenario

<<<<<<< HEAD
=======

>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
    def _validate_scenario_data(self, data: Dict[str, Any]) -> List[str]:
        """
        Валидация данных сценария.
        Args:
            data: Данные для валидации (должны содержать ключ 'plant_name')
        Returns:
            List[str]: Список ошибок, пустой если ошибок нет
        """
        errors = []
<<<<<<< HEAD

=======
        # Список обязательных полей, которые должны присутствовать в словаре.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        required_fields = [
            'plant_name', 'min_temperature', 'max_temperature',
            'min_soil_moisture', 'max_soil_moisture',
            'min_humidity', 'max_humidity',
            'min_light_lux', 'max_light_lux'
        ]
<<<<<<< HEAD
        for field in required_fields:
            if field not in data:
                errors.append(f"Отсутствует обязательное поле: {field}")
        if errors:
            return errors

=======
        # Проверяем наличие каждого обязательного поля.
        for field in required_fields:
            if field not in data:
                errors.append(f"Отсутствует обязательное поле: {field}")
        # Если уже есть ошибки по отсутствию полей, дальше проверять бессмысленно.
        if errors:
            return errors
        # Проверка логических соотношений: минимум должен быть меньше максимума.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        if data['min_temperature'] >= data['max_temperature']:
            errors.append("Минимальная температура должна быть меньше максимальной")
        if data['min_soil_moisture'] >= data['max_soil_moisture']:
            errors.append("Минимальная влажность почвы должна быть меньше максимальной")
        if data['min_humidity'] >= data['max_humidity']:
            errors.append("Минимальная влажность воздуха должна быть меньше максимальной")
        if data['min_light_lux'] >= data['max_light_lux']:
            errors.append("Минимальная освещённость должна быть меньше максимальной")
<<<<<<< HEAD

=======
        # Проверка допустимых диапазонов значений.
        # Температура может быть от -50 до 100 градусов Цельсия.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        if not (-50 <= data['min_temperature'] <= 100):
            errors.append("Минимальная температура должна быть от -50 до 100°C")
        if not (-50 <= data['max_temperature'] <= 100):
            errors.append("Максимальная температура должна быть от -50 до 100°C")
<<<<<<< HEAD
=======
        # Влажность почвы и воздуха в процентах от 0 до 100.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        if not (0 <= data['min_soil_moisture'] <= 100):
            errors.append("Минимальная влажность почвы должна быть от 0 до 100%")
        if not (0 <= data['max_soil_moisture'] <= 100):
            errors.append("Максимальная влажность почвы должна быть от 0 до 100%")
        if not (0 <= data['min_humidity'] <= 100):
            errors.append("Минимальная влажность воздуха должна быть от 0 до 100%")
        if not (0 <= data['max_humidity'] <= 100):
            errors.append("Максимальная влажность воздуха должна быть от 0 до 100%")
<<<<<<< HEAD
=======
        # Освещённость не может быть отрицательной.
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        if data['min_light_lux'] < 0:
            errors.append("Минимальная освещённость не может быть отрицательной")
        if data['max_light_lux'] < 0:
            errors.append("Максимальная освещённость не может быть отрицательной")
<<<<<<< HEAD

=======
        # Возвращаем список ошибок (пустой, если всё хорошо).
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f
        return errors