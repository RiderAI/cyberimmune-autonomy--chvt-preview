import turtle
import json
import os
import time
from tkinter import TclError
from pyproj import Transformer

# Путь к файлу телеметрии
TELEMETRY_FILE = "telemetry.json"


class CoordinateTransformer:
    """
    Класс для преобразования географических координат в локальную систему координат (UTM).
    """

    def __init__(self, reference_lat, reference_lon):
        self.transformer, self.ref_x, self.ref_y = self.create_transformer(reference_lat, reference_lon)

    def create_transformer(self, reference_lat, reference_lon):
        """
        Создает преобразователь координат из WGS84 в UTM (зона 36N). Соответствует городу Санкт-Петербург
        Преобразует координаты опорной точки в метры.
        """
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:32636", always_xy=True)
        ref_x, ref_y = transformer.transform(reference_lon, reference_lat)
        return transformer, ref_x, ref_y

    def convert(self, lat, lon, scale_x=1.0, scale_y=1.0):
        """
        Преобразует географические координаты (lat, lon) в локальную декартову систему координат.

        :param lat: Широта
        :param lon: Долгота
        :param scale_x: Масштаб по оси X
        :param scale_y: Масштаб по оси Y
        :return: Преобразованные координаты
        """
        x, y = self.transformer.transform(lon, lat)
        return (x - self.ref_x) * scale_x, (y - self.ref_y) * scale_y


class CarVisualization:
    """
    Класс для визуализации пути автомобиля
    """

    def __init__(self, runtime_sec=5, scale_x=1.0, scale_y=1.0, background_image=None, reference_lat=59.9390,
                 reference_lon=30.3158):
        """
        Инициализация класса для визуализации.

        :param runtime_sec: Время работы окна (в секундах)
        :param scale_x: Масштаб по оси X
        :param scale_y: Масштаб по оси Y
        :param background_image: Путь к фоновому изображению
        :param reference_lat: Широта опорной точки
        :param reference_lon: Долгота опорной точки
        """
        self.runtime_sec = runtime_sec
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.background_image = background_image
        self.reference_lat = reference_lat
        self.reference_lon = reference_lon

        # Инициализация графики и преобразователя координат
        self.screen = turtle.Screen()
        self.screen.title("Car visualization (SITL)")
        self.screen.setup(width=800, height=600)
        self.screen.setworldcoordinates(-1000, -1000, 1000, 1000)
        if self.background_image:
            self.load_background()

        self.transformer = CoordinateTransformer(self.reference_lat, self.reference_lon)
        self.setup_turtles()

    def load_background(self):
        """
        Загружает фоновое изображение в окно Turtle.
        """
        try:
            self.screen.bgpic(self.background_image)
        except (TclError, turtle.Terminator):
            print(f"Не удалось загрузить фон: {self.background_image}")

    def setup_turtles(self):
        self.path_turtle = turtle.Turtle()
        self.path_turtle.color("blue")
        self.path_turtle.speed(0)
        self.path_turtle.penup()
        self.path_turtle.pensize(3)

        self.car_turtle = turtle.Turtle()
        self.car_turtle.shape("triangle")
        self.car_turtle.color("red")
        self.car_turtle.penup()
        self.car_turtle.shapesize(1.5, 1.5)

        self.info_turtle = turtle.Turtle()
        self.info_turtle.penup()
        self.info_turtle.hideturtle()
        self.info_turtle.setposition(-900, 600)
        self.info_turtle.color("black")

    def update_visualization(self):
        last_x, last_y = None, None
        start_time = time.time()

        while True:
            if (time.time() - start_time) >= self.runtime_sec:
                break

            if os.path.exists(TELEMETRY_FILE):
                try:
                    with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    lat = data.get("latitude", self.reference_lat)
                    lon = data.get("longitude", self.reference_lon)
                    spd = data.get("speed_kmh", 0.0)
                    bearing = data.get("direction_deg", 0.0)

                    # Преобразуем координаты
                    x, y = self.transformer.convert(lat, lon, self.scale_x, self.scale_y)

                    if last_x is not None and last_y is not None:
                        self.path_turtle.setposition(last_x, last_y)
                        self.path_turtle.pendown()
                        self.path_turtle.goto(x, y)
                        self.path_turtle.penup()

                    last_x, last_y = x, y

                    self.car_turtle.setposition(x, y)
                    heading_for_turtle = 90.0 - bearing
                    self.car_turtle.setheading(heading_for_turtle)

                    info_text = (
                        f"Speed: {spd:.1f} km/h\n"
                        f"Direction: {bearing:.1f} deg\n"
                        f"Lat: {lat:.5f}\nLon: {lon:.5f}"
                    )
                    self.info_turtle.clear()
                    self.info_turtle.write(info_text, font=("Arial", 14, "normal"))

                except Exception:
                    pass

            turtle.update()
            time.sleep(0.1)

    def start(self):
        """
        Запускает процесс визуализации.
        """
        turtle.tracer(0, 0)
        try:
            self.update_visualization()
        except (turtle.Terminator, TclError):
            pass
        finally:
            try:
                turtle.bye()
            except:
                pass


# Запуск в виде отдельного процесса
if __name__ == "__main__":
    try:
        # Проверяем наличие файла с данными
        if not os.path.exists(TELEMETRY_FILE) or os.stat(TELEMETRY_FILE).st_size == 0:
            # Если файл пуст или не существует, выводим сообщение
            screen = turtle.Screen()
            screen.title("Car visualization (SITL)")
            screen.setup(width=800, height=600)
            screen.setworldcoordinates(-1000, -1000, 1000, 1000)
            info_turtle = turtle.Turtle()
            info_turtle.penup()
            info_turtle.hideturtle()
            info_turtle.color("black")
            info_turtle.setposition(0, 0)
            info_turtle.write("Нет данных", align="center", font=("Arial", 24, "normal"))
            turtle.done()
        else:
            # Если данные есть, запускаем визуализацию
            visualization = CarVisualization(runtime_sec=5)
            visualization.start()
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        # В случае ошибки также выводим сообщение
        screen = turtle.Screen()
        screen.title("Car visualization (SITL)")
        screen.setup(width=800, height=600)
        screen.setworldcoordinates(-1000, -1000, 1000, 1000)
        info_turtle = turtle.Turtle()
        info_turtle.penup()
        info_turtle.hideturtle()
        info_turtle.color("black")
        info_turtle.setposition(0, 0)
        info_turtle.write("Ошибка при запуске", align="center", font=("Arial", 24, "normal"))
        turtle.done()
