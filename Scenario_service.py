# Scenario_Service - сервис для работы со сценариями ухода за растениями.
# Использует модели для безопасности типов и структурирования данных
# Используемые библиотеки
from typing import Dict, List, Optional, Any # Для перевода данных в нужный тип
from datetime import datetime # Для создания времени получения данных
from models_for_scenario import Scenario, DeviceScenario # Для преобразования данных
from database import query_db, execute_db # Для работы с SQL-запросами


class ScenarioService: # Сервис для управления сценариями ухода за растениями.
    # Отвечает за CRUD-операции со сценариями и их назначение устройствам.
    def __init__(self): # Инициализация ScenarioService.
        # Создает кэш для хранения сценариев устройств в памяти.
        self._scenario_cache = {}  # Кэш: {device_id: {"data": DeviceScenario, "cached_at": datetime}}

    def get_device_scenario(self, device_id: str) -> Optional[DeviceScenario]: # Получает активный сценарий для устройства.
        """
        Args:
            device_id: Идентификатор устройства (например, "ESP32_001")
        Returns:
            DeviceScenario: Объект с данными сценария или None
        """
        # Проверка кэша
        if device_id in self._scenario_cache:
            cached_data = self._scenario_cache[device_id]
            # Считаем время от создания кэша
            cache_age = (datetime.now() - cached_data["cached_at"]).seconds
            # Если оно меньше 5 минут (300 секунд), выводим его, в противном случае нужно его удалить
            if cache_age < 300:
                return cached_data["data"]
            else:
                del self._scenario_cache[device_id]
        # SQL-запрос для получения активного сценария устройства
        # Используем алиас (удобное имя) s.nam AS plant_name для совместимости с моделью
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
            FROM scenarios AS s
            INNER JOIN user_scenarios AS us ON s.iid = us.scenario_id
            WHERE us.device_id = ? AND us.is_active = 1
            ORDER BY us.created_at DESC
            LIMIT 1
        """, [device_id], one=True)
        # Если ничего нет, так и говорим
        if not row:
            return None
        # Переводим информацию запроса в словари, затем записываем информацию в модели для сценариев
        row_dict = dict(row)
        # Сначала информацию в модель сценария
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
        # Затем в модель сценария для устройства
        device_scenario = DeviceScenario(
            device_id=device_id,
            scenario=scenario
        )
        # А затем и в модель кэша сценария
        self._scenario_cache[device_id] = {
            "data": device_scenario,
            "cached_at": datetime.now()
        }
        # А после выводим модель сценария для устройства
        return device_scenario


    def assign_scenario_to_device(self, user_id: int, scenario_id: int,
                                  device_id: str) -> bool: # Назначает сценарий устройству пользователя.
        """
        Args:
            user_id: ID пользователя, который делает назначение
            scenario_id: ID сценария для назначения
            device_id: ID устройства, которому назначается сценарий
        Returns:
            bool: True если назначение успешно
        Raises:
            ValueError: Если сценарий не найден или недоступен пользователю
        """
        # Проверка существования сценария и прав пользователя
        scenario_row = query_db("""
            SELECT * FROM scenarios 
            WHERE iid = ? AND (created_by IS NULL OR created_by = ?)
        """, [scenario_id, user_id], one=True)
        # Если пусто, то говорим, что человек бесправный (или просто нет такого сценария)
        if not scenario_row:
            raise ValueError(
                f"Сценарий с ID {scenario_id} не найден или недоступен пользователю {user_id}"
            )
        # Деактивируем все текущие сценарии для этого устройства
        execute_db("""
            UPDATE user_scenarios 
            SET is_active = 0 
            WHERE user_id = ? AND device_id = ?
        """, [user_id, device_id])
        # Проверяем, существует ли уже связь в БД
        existing_link = query_db("""
            SELECT user_id, scenario_id
            FROM user_scenarios 
            WHERE user_id = ? AND scenario_id = ? AND device_id = ?
        """, [user_id, scenario_id, device_id], one=True)
        # Связь существует - активируем её
        if existing_link:
            execute_db("""
                UPDATE user_scenarios 
                SET is_active = 1, created_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND scenario_id = ?
            """, [existing_link['user_id'], existing_link['scenario_id']])
        # Связи нет - создаём новую
        else:
            execute_db("""
                INSERT INTO user_scenarios (user_id, scenario_id, device_id, is_active)
                VALUES (?, ?, ?, 1)
            """, [user_id, scenario_id, device_id])
        # Очистка кэша для этого устройства
        if device_id in self._scenario_cache:
            del self._scenario_cache[device_id]
        # Если всё хорошо, говорим, что всё хорошо
        return True


    def get_available_scenarios(self, user_id: Optional[int] = None) -> List[Scenario]: # Получает список сценариев, доступных пользователю.
        """
        Args:
            user_id: ID пользователя или None для системных сценариев
        Returns:
            List[Scenario]: Список объектов Scenario
        """
        # Если не указан id пользователя, выбираем все встроенные сценарии
        if user_id is None:
            rows = query_db("""
                SELECT * FROM scenarios 
                WHERE created_by IS NULL
                ORDER BY iid
            """)
        # Если он есть, к ним добавляем и созданные пользователем сценарии
        else:
            rows = query_db("""
                SELECT * FROM scenarios 
                WHERE created_by IS NULL OR created_by = ?
                ORDER BY created_by, iid
            """, [user_id])
        # Записываем сценарии в список, который после записи всех сценариев выведем
        scenarios = []
        for row in rows:
            row_dict = dict(row)
            # Преобразуем ключ nam -> plant_name для совместимости с моделью
            row_dict['plant_name'] = row_dict.pop('nam')
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


    def _validate_scenario_data(self, data: Dict[str, Any]) -> List[str]: # Валидация данных сценария.
        """
        Args:
            data: Данные для валидации (должны содержать ключ 'plant_name')
        Returns:
            List[str]: Список ошибок, пустой если ошибок нет
        """
        # Создаём пустой (пока) список ошибок
        errors = []
        # Создаём список нужных колонок в сценарии
        required_fields = [
            'plant_name', 'min_temperature', 'max_temperature',
            'min_soil_moisture', 'max_soil_moisture',
            'min_humidity', 'max_humidity',
            'min_light_lux', 'max_light_lux'
        ]
        # Если какой-то колонки нет, сообщаем об этом
        for field in required_fields:
            if field not in data:
                errors.append(f"Отсутствует обязательное поле: {field}")
        # Если есть ошибки, выводим их
        if errors:
            return errors
        # Проверяем логические ошибки в сценарии (если они есть, потом их выведем)
        if data['min_temperature'] >= data['max_temperature']:
            errors.append("Минимальная температура должна быть меньше максимальной")
        if data['min_soil_moisture'] >= data['max_soil_moisture']:
            errors.append("Минимальная влажность почвы должна быть меньше максимальной")
        if data['min_humidity'] >= data['max_humidity']:
            errors.append("Минимальная влажность воздуха должна быть меньше максимальной")
        if data['min_light_lux'] >= data['max_light_lux']:
            errors.append("Минимальная освещённость должна быть меньше максимальной")
        if not (-50 <= data['min_temperature'] <= 100):
            errors.append("Минимальная температура должна быть от -50 до 100°C")
        if not (-50 <= data['max_temperature'] <= 100):
            errors.append("Максимальная температура должна быть от -50 до 100°C")
        if not (0 <= data['min_soil_moisture'] <= 100):
            errors.append("Минимальная влажность почвы должна быть от 0 до 100%")
        if not (0 <= data['max_soil_moisture'] <= 100):
            errors.append("Максимальная влажность почвы должна быть от 0 до 100%")
        if not (0 <= data['min_humidity'] <= 100):
            errors.append("Минимальная влажность воздуха должна быть от 0 до 100%")
        if not (0 <= data['max_humidity'] <= 100):
            errors.append("Максимальная влажность воздуха должна быть от 0 до 100%")
        if data['min_light_lux'] < 0:
            errors.append("Минимальная освещённость не может быть отрицательной")
        if data['max_light_lux'] < 0:
            errors.append("Максимальная освещённость не может быть отрицательной")
        return errors


    def create_scenario(self, user_id: int, scenario_data: Dict[str, Any]) -> Scenario: # Создаёт новый сценарий для пользователя.
        """
        Args:
            user_id: ID пользователя, создающего сценарий
            scenario_data: Данные нового сценария (должны содержать ключ 'plant_name')
        Returns:
            Scenario: Созданный объект Scenario с заполненным ID
        Raises:
            ValueError: Если данные некорректны
        """
        # Проверяем на ошибки валидации данных сценария (если они есть, выводим их)
        errors = self._validate_scenario_data(scenario_data)
        if errors:
            raise ValueError("; ".join(errors))
        # Создаём новый сценарий
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
        # Переводим данные в словари, записываем их в модель сценариев и выводим её
        new_row = query_db("SELECT * FROM scenarios WHERE iid = ?", [scenario_id], one=True)
        row_dict = dict(new_row)
        row_dict['plant_name'] = row_dict.pop('nam')
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
