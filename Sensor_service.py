# 1. Импорты - минимальный набор для работы
from typing import Dict, List, Optional
from models_for_sensor import DeviceData, Scenario
from database import query_db, execute_db
from datetime import datetime


# 2. Объявление класса сервиса
class SensorService:
    """
    Гибридный сервис для обработки данных с датчиков.
    Содержит бизнес-логику и простые методы доступа к данным.
    """
    # Константа для обозначения "параметр не используется"
    PARAM_UNUSED = 1000.0

    def __init__(self):
        # Хранилище целевых состояний насоса (device_id -> нужно ли включить)
        self._pump_targets = {}

    # 4. Основной публичный метод
    def process_sensor_data(self, raw_data: Dict) -> Dict:
        """
        Основная бизнес-логика обработки данных.
        Args:
            raw_data: Сырые данные от ESP32 в виде словаря
        Returns:
            Словарь с результатом обработки и командами для устройства
        """
        # 5. Преобразование сырых данных в типизированную модель
        sensor_data = DeviceData(
            device_id=raw_data['device_id'],
            temperature=raw_data['temp'],          # ключ 'temp' от ESP32
            soil_moisture=raw_data['soil_moisture'],
            light=raw_data['light'],
            humidity=raw_data.get('humidity'),
            pump_state=raw_data.get('pump_state', False)
        )

        # 6. Получение активного сценария для устройства
        scenario = self._get_device_scenario(str(sensor_data.device_id))

        # 7. Проверка условий и генерация команд (с уведомлениями)
        commands = self._check_conditions(sensor_data, scenario)

        # 8. Сохранение показаний в БД
        self._save_reading(sensor_data)

        # 9. Формирование ответа
        return {
            "success": True,
            "commands": commands,
            "device_id": sensor_data.device_id,
            "timestamp": datetime.now().isoformat()
        }

    # 10. Приватный метод для получения сценария
    def _get_device_scenario(self, device_id: str) -> Optional[Scenario]:
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
            FROM scenarios s
            INNER JOIN user_scenarios us ON s.iid = us.scenario_id
            WHERE us.device_id = ? AND us.is_active = 1
            ORDER BY us.created_at DESC
            LIMIT 1
        """, [device_id], one=True)
        if row:
            return Scenario(**dict(row))
        return None

    # 11. Приватный метод для сохранения показаний
    def _save_reading(self, data: DeviceData) -> int:
        """
        Сохраняет показания датчиков в базу данных.
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

    # 12. Приватный метод для сохранения уведомлений (исправлен)
    def _save_notification(self, device_id: str, message: str, type: str):
        print(f"🔥 _save_notification ВЫЗВАН с параметрами: {device_id}, {message}, {type}")
        try:
            execute_db('''
                INSERT INTO notifications (device_id, message, type)
                VALUES (?, ?, ?)
            ''', [device_id, message, type])
            print("✅ Уведомление успешно сохранено в БД")
        except Exception as e:
            print(f"❌ Ошибка при сохранении уведомления: {e}")

    # 13. Приватные методы управления целью насоса
    def _get_pump_target(self, device_id: str) -> Optional[bool]:
        return self._pump_targets.get(device_id)

    def _set_pump_target(self, device_id: str, target: bool):
        self._pump_targets[device_id] = target

    # 14. Основная логика проверки условий (исправлена: игнорируем неиспользуемые пороги)
    def _check_conditions(self, data: DeviceData,
                          scenario: Optional[Scenario]) -> List[Dict]:
        """
        Проверяет условия и генерирует команды + уведомления.
        Параметры со значением PARAM_UNUSED (1000.0) игнорируются.
        """
        commands = []
        if not scenario:
            return commands

        device_id = data.device_id
        plant_name = scenario.plant_name # название растения из сценария

        # ----- ВЛАЖНОСТЬ ПОЧВЫ (интеллектуальный полив) -----
        current_soil = data.soil_moisture
        min_soil = scenario.min_soil_moisture
        max_soil = scenario.max_soil_moisture
        pump_target = self._get_pump_target(device_id)

        # Проверяем, что пороги заданы (не равны 1000.0)
        if min_soil != self.PARAM_UNUSED and max_soil != self.PARAM_UNUSED:
            if current_soil < min_soil and pump_target is not True:
                commands.append({
                    "command": "pump_on",
                    "reason": f"Влажность {current_soil}% < {min_soil}%"
                })
                self._set_pump_target(device_id, True)
                self._save_notification(
                    device_id,
                    f"[{plant_name}] Почва слишком сухая ({current_soil}%), включаю насос",
                    "soil"
                )

            elif current_soil >= max_soil and pump_target is True:
                commands.append({
                    "command": "pump_off",
                    "reason": f"Влажность достигла {current_soil}% >= {max_soil}%"
                })
                self._set_pump_target(device_id, False)
                self._save_notification(
                    device_id,
                    f"[{plant_name}] Почва увлажнена до {current_soil}%, насос выключен",
                    "soil"
                )

        # ----- ТЕМПЕРАТУРА -----
        if scenario.min_temperature != self.PARAM_UNUSED and data.temperature < scenario.min_temperature:
            self._save_notification(
                device_id,
                f"[{plant_name}] Температура слишком низкая: {data.temperature}°C < {scenario.min_temperature}°C",
                "temperature"
            )
        if scenario.max_temperature != self.PARAM_UNUSED and data.temperature > scenario.max_temperature:
            self._save_notification(
                device_id,
                f"[{plant_name}] Температура слишком высокая: {data.temperature}°C > {scenario.max_temperature}°C",
                "temperature"
            )

        # ----- ВЛАЖНОСТЬ ВОЗДУХА -----
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

        # ----- ОСВЕЩЁННОСТЬ -----
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