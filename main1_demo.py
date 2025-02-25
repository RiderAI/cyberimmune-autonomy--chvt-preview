# Кибериммунная автономность
# Создание конструктивно защищённого автономного автобуса
# Модуль 1
# Версия 1.03

# О кибериммунной разработке
# Больше информации о кибериммунном подходе к разработке можно найти на [этой](https://github.com/sergey-sobolev/cyberimmune-systems/wiki/%D0%9A%D0%B8%D0%B1%D0%B5%D1%80%D0%B8%D0%BC%D0%BC%D1%83%D0%BD%D0%B8%D1%82%D0%B5%D1%82) странице

# Сокращения
# АНТС - автономное наземного транспортное средство

# О задаче
# Автономные наземные транспортные средства с точки зрения архитектуры бортовых информационных систем мало отличаются от подводных, надводных, воздушных или космических.

# Ключевые задачи, которые нужно решить на борту:
# 1. получение задания на перемещение
# 2. расчёт и осуществление перемещения в заданную точку с учётом ограничений в задании и текущих координат
# 3. высадка пассажиров

# Архитектура бортовых информационных систем
# https://raw.githubusercontent.com/sergey-sobolev/cyberimmune-autonomy--chvt-preview/ef43be297502b70b142173f0655d7df5b349d6c3/images/ciac-basic-dfd.png
# Такую архитектуру позволяет реализовать функции автономного перемещения в условиях отсутствия кибератак.
# Взаимодействие компонентов отражено на диаграмме
# https://raw.githubusercontent.com/sergey-sobolev/cyberimmune-autonomy--chvt-preview/ef43be297502b70b142173f0655d7df5b349d6c3/images/basic-scenario.png

# Создадим каталог очередей для передачи сообщений между блоками
from src.queues_dir import QueuesDirectory
queues_dir = QueuesDirectory()  # каталог очередей для передачи сообщений между блоками

# Симулятор изменения физического состояния (перемещения в пространстве)
from src.sitl_json import SITLJson
from geopy import Point as GeoPoint

# Теперь создадим остальные функциональные блоки
from src.communication_gateway import BaseCommunicationGateway
from src.config import CONTROL_SYSTEM_QUEUE_NAME, SERVOS_QUEUE_NAME
from src.event_types import Event
from multiprocessing import Queue


class CommunicationGateway(BaseCommunicationGateway):
    """CommunicationGateway класс для реализации логики взаимодействия
    с системой планирования заданий

    Работает в отдельном процессе, поэтому создаётся как наследник класса Process
    """

    def _send_mission_to_consumers(self):
        """ метод для отправки сообщения с маршрутным заданием в систему управления """

        # имена очередей блоков находятся в файле src/config.py
        # события нужно отправлять в соответствие с диаграммой информационных потоков
        control_q_name = CONTROL_SYSTEM_QUEUE_NAME

        # события передаются в виде экземпляров класса Event,
        # описание класса находится в файле src/event_types.py
        event = Event(source=BaseCommunicationGateway.event_source_name,
                      destination=control_q_name,
                      operation="set_mission", parameters=self._mission
                      )

        # поиск в каталоге нужной очереди (в данном случае - системы управления)
        control_q: Queue = self._queues_dir.get_queue(control_q_name)
        # отправка события в найденную очередь
        control_q.put(event)


# Создадим блоки "Система управления", "Навигация" и другие компоненты
from src.control_system import BaseControlSystem
from src.navigation_system import BaseNavigationSystem
from src.servos import Servos
from src.mission_planner import MissionPlanner


class ControlSystem(BaseControlSystem):
    """ControlSystem блок расчёта управления """

    def _send_speed_and_direction_to_consumers(self, speed, direction):
        servos_q_name = None # замените на правильное название очереди
        servos_q: Queue = self._queues_dir.get_queue(servos_q_name)

        # отправка сообщения с желаемой скоростью
        event_speed = None # замените на код создания сообщения со скоростью для приводов
                           # подсказка, требуемая операция - set_speed

        # отправка сообщения с желаемым направлением
        event_direction = None # замените на код создания сообщения с направлением для приводов
                               # подсказка, требуемая операция - set_direction

        servos_q.put(event_speed)
        servos_q.put(event_direction)


# Создаём навигационную систему
class NavigationSystem(BaseNavigationSystem):
    """ класс навигационного блока """
    def _send_position_to_consumers(self):
        control_q_name = None # замените на правильное название очереди
        event = None # замените на код создания сообщения с координатами для системы управления
                     # подсказка, требуемая операция - position_update
        control_q: Queue = self._queues_dir.get_queue(control_q_name)
        control_q.put(event)
        

def main():
    # Создаем экземпляры основных классов

    # координата текущего положения машинки
    home = GeoPoint(latitude=59.939032, longitude=30.315827)  # Александровская колонна СПб

    # идентификатор машинки (аналог VIN)
    car_id = "m1"

    # симулятор перемещения
    sitl = SITLJson(queues_dir=queues_dir, position=home, car_id=car_id)

    # Экземпляр класса связи
    communication_gateway = CommunicationGateway(queues_dir=queues_dir)

    # Система управления
    control_system = ControlSystem(queues_dir=queues_dir)

    # Система навигации
    navigation_system = NavigationSystem(queues_dir=queues_dir)

    # Приводы
    servos = Servos(queues_dir=queues_dir)

    # Планировщик заданий
    mission_planner = MissionPlanner(queues_dir=queues_dir)

    # Настроим маршрут
    from src.mission_type import Mission, GeoSpecificSpeedLimit

    #Создадим новую задачу на перевозку со следующими параметрами:
    # - home - координаты начальной точки перемещения
    # - waypoints - координаты путевых точек (через них должна проехать наша машинка) UPD: первая точка инорируется?
    # - speed_limits - скоростные ограничения для заданного отрезка пути, 0 - отрезок от 0 до 1 точки, 1 - от 1 до 2 путевой точки;
    # если путевых точек больше, то в отсутствие скоростного ограничения для какого-то сегмента должно использоваться последнее заданное ограничение
    # - armed - разрешение на выезд

    mission = Mission(home=home,
                      waypoints=[
                                 home,
                                 GeoPoint(latitude=59.9386, longitude=30.3149),
                                 GeoPoint(latitude=59.9386, longitude=30.3121),
                                 GeoPoint(latitude=59.940041, longitude=30.309788),
                                 GeoPoint(latitude=59.94139, longitude=30.31231),],
                      speed_limits=[
                          GeoSpecificSpeedLimit(0, 30),
                          GeoSpecificSpeedLimit(1, 60),
                          GeoSpecificSpeedLimit(2, 90),
                          GeoSpecificSpeedLimit(3, 30),
                      ],
                      armed=True)

    mission_planner.set_new_mission(mission=mission)

    # Запустим все компоненты системы

    sitl.start()
    navigation_system.start()
    servos.start()
    communication_gateway.start()
    control_system.start()
    mission_planner.start()

    # Запускаем модуль визуализации перемещений
    # Важно: делаем это после start(), чтобы процессы SITL и прочие уже работали
    from sitl_visualizer import CarVisualization
    # Запуск на 10 секунд и коэффициентом масштаба соответствующими карте:
    # visualize_car(runtime_sec=10, scale_x=4.3, scale_y=5.0, background_image="map.png")
    visualization = CarVisualization(runtime_sec=200, scale_x=4.3, scale_y=5.0, background_image="map.png")
    visualization.start()


    # Останавливаем все компоненты
    control_system.stop()
    communication_gateway.stop()
    mission_planner.stop()
    sitl.stop()
    servos.stop()
    navigation_system.stop()

    # дождёмся завершения работы всех компонентов
    control_system.join()
    communication_gateway.join()
    mission_planner.join()
    sitl.join()
    servos.join()
    navigation_system.join()

    # подчистим все ресурсы для возможности повторного запуска в следующих модулях
    del control_system, communication_gateway, mission_planner, sitl, servos, navigation_system, visualization


# Этот блок проверяет, что код выполняется как основной
if __name__ == '__main__':
    main()

# Задание: дописать в системе управления метод отправки события с командой на отгрузку в конечной точке маршрута.
#
# Сама логика определения конечной точки маршрута уже есть в базовом классе системы управления, не хватает только шага отправки события.
# Для выполнения этой задачи нужно реализовать абстрактные методы _release_cargo (разблокировать грузовой отсек, т.е. оставить груз) и _lock_cargo (заблокировать грузовой отсек, эту команду система управления отправляет в начале следования по маршруту - будет неправильно потерять груз по дороге)