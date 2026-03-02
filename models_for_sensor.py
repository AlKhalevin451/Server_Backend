from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DeviceData:
    device_id: int
    temperature: float
    soil_moisture: float
    light: int
    humidity: Optional[int] = None
    pump_state: bool = False
    timestamp: datetime = datetime.now()


@dataclass
class Scenario:
    iid: Optional[int] = None
    plant_name: str = ""
    min_temperature: float = 0.0
    max_temperature: float = 0.0
    min_soil_moisture: float = 0.0
    max_soil_moisture: float = 0.0
    min_humidity: float = 0.0
    max_humidity: float = 0.0
    min_light_lux: int = 0
    max_light_lux: int = 0
    created_by: Optional[int] = None