# Импорты - минимальный набор для работы
from typing import Dict, List, Optional
from models_for_sensor import DeviceData, Scenario
from database import query_db, execute_db
from datetime import datetime


# Объявление класса сервиса
class SensorService:
    """
    Гибридный сервис для обработки данных с датчиков.
    Содержит бизнес-логику и простые методы доступа к данным.
    """
    # Константа для обозначения "параметр не используется"
    # Значение 1000.0 выбрано как заведомо невозможное для реальных показаний,
    # чтобы отличать пороги, которые не заданы в сценарии.
    PARAM_UNUSED = 1000.0
    def __init__(self):
        """
        Инициализация сервиса.
        Создаёт внутреннее хранилище целевых состояний насоса для каждого устройства.
        _pump_targets: словарь {device_id: True/False}, где True означает,
                       что насос должен быть включён (команда уже отправлена).
                       Используется для предотвращения повторных команд включения/выключения.
        """
        self._pump_targets = {}

    # Основной публичный метод
    def process_sensor_data(self, raw_data: Dict) -> Dict:
        """
        Основная бизнес-логика обработки данных.
        Вызывается при получении показаний от ESP32.
        Args:
            raw_data: Сырые данные от ESP32 в виде словаря.
                      Ожидается наличие ключей: device_id, temp, soil_moisture,
                      light, (опционально humidity, pump_state).
        Returns:
            Словарь с результатом обработки и командами для устройства.
            Структура: {
                "success": bool,
                "commands": List[Dict],  # команды для устройства
                "device_id": str,
                "timestamp": str (ISO формат)
            }
        """
        # Преобразование сырых данных в типизированную модель DeviceData.
        # Это повышает типобезопасность и упрощает дальнейшую работу.
        sensor_data = DeviceData(
            device_id=raw_data['device_id'],
            temperature=raw_data['temp'],          # ключ 'temp' от ESP32
            soil_moisture=raw_data['soil_moisture'],
            light=raw_data['light'],
            humidity=raw_data.get('humidity'),     # может отсутствовать
            pump_state=raw_data.get('pump_state', False)  # по умолчанию False
        )
        # Получение активного сценария для устройства.
        # Сценарий определяет допустимые диапазоны параметров.
        scenario = self._get_device_scenario(str(sensor_data.device_id))
        # Проверка условий и генерация команд (с уведомлениями).
        # Здесь анализируются текущие показания и сценарий,
        # формируются команды для насоса и сохраняются уведомления.
        commands = self._check_conditions(sensor_data, scenario)
        # Сохранение показаний в БД.
        # История измерений хранится для последующего анализа.
        self._save_reading(sensor_data)
        # Формирование ответа устройству.
        return {
            "success": True,
            "commands": commands,
            "device_id": sensor_data.device_id,
            "timestamp": datetime.now().isoformat()
        }

    # Приватный метод для получения сценария
    def _get_device_scenario(self, device_id: str) -> Optional[Scenario]:
        """
        Получает активный сценарий для указанного устройства из базы данных.
        Args:
            device_id: Идентификатор устройства.
        Returns:
            Объект Scenario или None, если активный сценарий не найден.
        """
        # SQL-запрос: выбираем сценарий, связанный с устройством через user_scenarios,
        # который является активным (is_active = 1).
        # Поле s.nam переименовываем в plant_name для соответствия модели Scenario.
        row = query_db("""
            SELECT 
                s.iid,
                s.nam AS plant_name,           -- преобразуем nam в plant_name
                s.min_temperature, 
                s.max_temperature,
                s.min_soil_moisture, 
                s.max_soil_moisture,
                s.min_humidity, 
                s.max_humidity,
                s.min_light_lux, 
                s.max_light_lux,
                s.created_by
            FROM scenarios AS s
            INNER JOIN user_scenarios us ON s.iid = us.scenario_id
            WHERE us.device_id = ? AND us.is_active = 1
            ORDER BY us.created_at DESC
            LIMIT 1
        """, [device_id], one=True)
        if row:
            # Преобразуем строку результата в словарь и создаём модель Scenario.
            return Scenario(**dict(row))
        return None

    # Приватный метод для сохранения показаний
    def _save_reading(self, data: DeviceData) -> int:
        """
        Сохраняет показания датчиков в таблицу sensor_readings.
        Args:
            data: Объект DeviceData с текущими показаниями.
        Returns:
            ID вставленной записи (генерируется базой данных).
        """
        reading_id = execute_db("""
            INSERT INTO sensor_readings 
            (device_id, temp, soil_moisture, light, humidity, pump_state)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.device_id,
            data.temperature,
            data.soil_moisture,
            data.light,
            data.humidity,
            data.pump_state
        ))
        return reading_id

    # Приватный метод для сохранения уведомлений (исправлен)
    def _save_notification(self, device_id: str, message: str, type: str):
        """
        Сохраняет уведомление в таблицу notifications.
        Args:
            device_id: ID устройства.
            message: Текст уведомления.
            type: Тип уведомления (soil, temperature, humidity, light).
        """
        # Отладочный вывод для проверки вызова (можно удалить в продакшне)
        print(f"_save_notification ВЫЗВАН с параметрами: {device_id}, {message}, {type}")
        try:
            execute_db('''
                INSERT INTO notifications (device_id, message, type)
                VALUES (?, ?, ?)
            ''', [device_id, message, type])
            print("Уведомление успешно сохранено в БД.")
        except Exception as e:
            print(f"Ошибка при сохранении уведомления: {e}")

    # Приватные методы управления целью насоса
    def _get_pump_target(self, device_id: str) -> Optional[bool]:
        """
        Возвращает текущую цель состояния насоса для устройства.
        Используется для избежания повторной отправки одной и той же команды.
        """
        return self._pump_targets.get(device_id)


    def _set_pump_target(self, device_id: str, target: bool):
        """
        Устанавливает цель состояния насоса для устройства.
        """
        self._pump_targets[device_id] = target

    # Основная логика проверки условий
    def _check_conditions(self, data: DeviceData,
                          scenario: Optional[Scenario]) -> List[Dict]:
        """
        Проверяет текущие показания на соответствие сценарию.
        Генерирует команды для устройства (включение/выключение насоса)
        и сохраняет уведомления о выходе параметров за допустимые пределы.
        Параметры со значением PARAM_UNUSED (1000.0) игнорируются,
        то есть соответствующие проверки не выполняются.
        Args:
            data: Текущие показания датчиков.
            scenario: Сценарий с пороговыми значениями (может быть None).
        Returns:
            Список команд для отправки устройству. Каждая команда — словарь
            с ключами "command" и "reason".
        """
        commands = []
        if not scenario:
            # Если сценарий не назначен, никаких действий не требуется.
            return commands
        device_id = data.device_id
        plant_name = scenario.plant_name  # Название растения из сценария
        current_soil = data.soil_moisture
        min_soil = scenario.min_soil_moisture
        max_soil = scenario.max_soil_moisture
        pump_target = self._get_pump_target(device_id)
        # Проверка влажности почвы и управление насосом
        # Проверяем, что пороги почвы заданы (не равны 1000.0)
        if min_soil != self.PARAM_UNUSED and max_soil != self.PARAM_UNUSED:
            # Если почва слишком сухая и насос ещё не включён по нашей команде
            if current_soil < min_soil and pump_target is not True:
                # Формируем команду включения насоса
                commands.append({
                    "command": "pump_on",
                    "reason": f"Влажность {current_soil}% < {min_soil}%"
                })
                # Запоминаем, что мы отправили команду на включение
                self._set_pump_target(device_id, True)
                # Создаём уведомление для пользователя
                self._save_notification(
                    device_id,
                    f"[{plant_name}] Почва слишком сухая ({current_soil}%), включаю насос",
                    "soil"
                )
            # Если влажность достигла верхнего порога и насос был включён
            elif current_soil >= max_soil and pump_target is True:
                # Команда выключения насоса
                commands.append({
                    "command": "pump_off",
                    "reason": f"Влажность достигла {current_soil}% >= {max_soil}%"
                })
                # Сбрасываем цель
                self._set_pump_target(device_id, False)
                # Уведомление
                self._save_notification(
                    device_id,
                    f"[{plant_name}] Почва увлажнена до {current_soil}%, насос выключен",
                    "soil"
                )
        # Проверка температуры (нижний порог)
        if scenario.min_temperature != self.PARAM_UNUSED and data.temperature < scenario.min_temperature:
            self._save_notification(
                device_id,
                f"[{plant_name}] Температура слишком низкая: {data.temperature}°C < {scenario.min_temperature}°C",
                "temperature"
            )
        # Проверка температуры (верхний порог)
        if scenario.max_temperature != self.PARAM_UNUSED and data.temperature > scenario.max_temperature:
            self._save_notification(
                device_id,
                f"[{plant_name}] Температура слишком высокая: {data.temperature}°C > {scenario.max_temperature}°C",
                "temperature"
            )
        # Проверка влажности воздуха (если датчик её передаёт)
        if data.humidity is not None:
            if scenario.min_humidity != self.PARAM_UNUSED and data.humidity < scenario.min_humidity:
                self._save_notification(
                    device_id,
                    f"[{plant_name}] Влажность воздуха слишком низкая: {data.humidity}% < {scenario.min_humidity}%",
                    "humidity"
                )
            if scenario.max_humidity != self.PARAM_UNUSED and data.humidity > scenario.max_humidity:
                self._save_notification(
                    device_id,
                    f"[{plant_name}] Влажность воздуха слишком высокая: {data.humidity}% > {scenario.max_humidity}%",
                    "humidity"
                )
        # Проверка освещённости
        if scenario.min_light_lux != self.PARAM_UNUSED and data.light < scenario.min_light_lux:
            self._save_notification(
                device_id,
                f"[{plant_name}] Освещённость слишком низкая: {data.light} лк < {scenario.min_light_lux} лк",
                "light"
            )
        if scenario.max_light_lux != self.PARAM_UNUSED and data.light > scenario.max_light_lux:
            self._save_notification(
                device_id,
                f"[{plant_name}] Освещённость слишком высокая: {data.light} лк > {scenario.max_light_lux} лк",
                "light"
            )
        return commands