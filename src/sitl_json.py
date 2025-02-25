import json
import os
import time
from src.sitl import SITL  # ваш оригинальный SITL
from geopy import Point as GeoPoint

class SITLJson(SITL):
    """
    Наследник от SITL, который при каждом пересчёте положения
    пишет координаты, скорость и направление в локальный JSON-файл.
    """

    def __init__(self, queues_dir, position: GeoPoint = None, car_id: str = "C1",
                 post_telemetry: bool = False, log_level=2, json_file_path="telemetry.json"):
        super().__init__(queues_dir, position, car_id, post_telemetry, log_level)
        self._json_file_path = json_file_path
        if os.path.exists(self._json_file_path):
            os.remove(self._json_file_path)

    def _write_to_json(self):
        """
        Записываем в JSON-файл текущие координаты, скорость и направление.
        Углы и скорости в вашем коде уже есть как self._bearing и self._speed_kmph.
        """
        data = {
            "timestamp": time.time(),
            "latitude": self._position.latitude,
            "longitude": self._position.longitude,
            "speed_kmh": self._speed_kmph,
            "direction_deg": self._bearing
        }
        try:
            with open(self._json_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log_message(1, f"Ошибка записи в JSON: {e}")  # 1 => LOG_ERROR

    def _recalc(self):
        """
        Переопределяем метод, в котором у SITL пересчитываются координаты.
        После вызова базового метода – пишем обновлённые данные в JSON.
        """
        super()._recalc()
        self._write_to_json()
