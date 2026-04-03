# Sensor_service - Сервис обработки данных с датчиков
# Он отвечает за получение данных от аппаратной части, их обработку и их передачу в приложение
# Используемые библиотеки
from typing import Dict, List, Optional # Для перевода типов данных в словарь, список или какой хочется
from models_for_sensor import DeviceData, Scenario # Для записи данных с контроллера
from database import query_db, execute_db # Для работы с SQL-запросы
from datetime import datetime # Для создания времени получения данных


class SensorService: # Класс сервиса обработки данных с датчиков.
    PARAM_UNUSED = 1000.0 # Переменная, которая нужна для обозначения того, что параметр не используется
    def __init__(self): # Хранилище целевых состояний насоса
        self._pump_targets = {}


    def process_sensor_data(self, raw_data: Dict) -> Dict: # Функция обработки данных.
        """
        Args:
            raw_data: Сырые данные от ESP32 в виде словаря
        Returns:
            Словарь с результатом обработки и командами для устройства
        """
        # Преобразуем данные с контроллера в модель устройства
        sensor_data = DeviceData(
            device_id=raw_data['device_id'],
            temperature=raw_data['temp'],
            soil_moisture=raw_data['soil_moisture'],
            light=raw_data['light'],
            humidity=raw_data.get('humidity'),
            pump_state=raw_data.get('pump_state', False)
        )
        # Возьмём активный сценарий для устройства
        scenario = self._get_device_scenario(str(sensor_data.device_id))
        # Проверим условия и сделаем уведомления, если не всё хорошо с условиями
        commands = self._check_conditions(sensor_data, scenario)
        # Сохраним всё в Базу Данных
        self._save_reading(sensor_data)
        # Создадим ответ для пользователя после обработки данных
        return {
            "success": True,
            "commands": commands,
            "device_id": sensor_data.device_id,
            "timestamp": datetime.now().isoformat()
        }


    def _get_device_scenario(self, device_id: str) -> Optional[Scenario]: # Функция для получения сценария
        # Возьмём активный для устройства сценарий
        row = query_db("""
            SELECT 
                s.iid,
                s.nam AS plant_name,           
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
            INNER JOIN user_scenarios AS us ON s.iid = us.scenario_id
            WHERE us.device_id = ? AND us.is_active = 1
            ORDER BY us.created_at DESC
            LIMIT 1
        """, [device_id], one=True)
        # Если в переменной что-то есть, значит, сценарий нашёлся, и его можно вывести (если нет, значит, ничего не выводим)
        if row:
            return Scenario(**dict(row))
        return None


    def _save_reading(self, data: DeviceData) -> int: # Функция для сохранения показаний
        # Берём данные с датчиков и выводим их
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


    def _save_notification(self, device_id: str, message: str, type: str): # Метод для сохранения уведомлений
        # Вставляем уведомление в Базу Данных (если произошла ошибка - так и говорим)
        print(f"Параметры уведомлений: {device_id}, {message}, {type}")
        try:
            execute_db('''
                INSERT INTO notifications (device_id, message, type)
                VALUES (?, ?, ?)
            ''', [device_id, message, type])
            print("Уведомление успешно сохранено в Базу Данных")
        except Exception as e:
            print(f"Ошибка при сохранении уведомления: {e}")


    def _get_pump_target(self, device_id: str) -> Optional[bool]: # Функция для просмотра состояния насоса
        return self._pump_targets.get(device_id)


    def _set_pump_target(self, device_id: str, target: bool): # Функция для включения или выключения насоса
        self._pump_targets[device_id] = target


    def _check_conditions(self, data: DeviceData,
                          scenario: Optional[Scenario]) -> List[Dict]: # Метод проверки условий
        # Создаём список (пока пустой) команд для пользователя
        commands = []
        # Нет сценария - нет команд
        if not scenario:
            return commands
        device_id = data.device_id # ID устройства
        plant_name = scenario.plant_name # Название растения из сценария
        # Данные для влажности почвы
        current_soil = data.soil_moisture
        min_soil = scenario.min_soil_moisture
        max_soil = scenario.max_soil_moisture
        pump_target = self._get_pump_target(device_id)
        # Проверяем, что пороги параметров заданы (не равны 1000.0)
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
        # Также, как и с влажностью почвы, проверяем температуру
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
        # Также делаем и с влажностью воздуха
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
        # Также делаем и с освещённостью
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
        # Выводим все уведомления (если они есть)
        return commands