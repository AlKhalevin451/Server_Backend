# models/scenario_models.py
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class Scenario:
    """Модель сценария для бизнес-логики"""
    iid: Optional[int] = None
    plant_name: str = ""
    min_temperature: float = 0.0
    max_temperature: float = 0.0
    min_soil_moisture: float = 0
    max_soil_moisture: float = 0
    min_humidity: float = 0
    max_humidity: float = 0
    min_light_lux: int = 0
    max_light_lux: int = 0
    created_by: Optional[int] = None


    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для API"""
        return asdict(self)


    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scenario':
        """Создание из словаря (например, из БД)"""
        return cls(**data)


@dataclass
class DeviceScenario:
    """Модель для ответа со сценарием устройства"""
    device_id: str
    scenario: Scenario


    def to_api_response(self) -> Dict[str, Any]:
        """Форматирование для API"""
        return {
            "device_id": self.device_id,
            "scenario": self.scenario.to_dict()
        }