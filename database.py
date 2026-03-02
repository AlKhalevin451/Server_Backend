# database.py - Модуль для работы с базой данных SQLite
# Он отвечает за создание таблиц и управление соединениями
# Используемые библиотеки и подключения
import sqlite3 # Для работы с SQLite
from flask import g # Модуль g нужен для хранения данных в течение одного запроса


DATABASE = 'plantcare.db' # Имя файла базы данных


def get_db(): # Получение соединения с базой данных.
    # Использует g для хранения соединения между запросами.
    db = getattr(g, '_database', None) # Получаем соединение с сервером (getattr - для проверки _database)
    # Если его нет, то создаём его
    if db is None:
        new_connection = sqlite3.connect(DATABASE)
        g._database = new_connection # Сохраняем его в объект g (Flask контекст запроса)
        db = new_connection
        db.row_factory = sqlite3.Row  # Возвращает словари вместо кортежей (чтобы обращаться к полям по имени)
    return db


def init_db(): # Инициализация базы данных - создаем все таблицы при их отсутствии.
    # Создаём новое соединение
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # 1. Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            iid INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 2. Таблица сценариев
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scenarios (
            iid INTEGER PRIMARY KEY AUTOINCREMENT,
            nam TEXT NOT NULL,
            min_temperature FLOAT NOT NULL,
            max_temperature FLOAT NOT NULL,
            min_soil_moisture FLOAT NOT NULL,
            max_soil_moisture FLOAT NOT NULL,
            min_humidity FLOAT NOT NULL,
            max_humidity FLOAT NOT NULL,
            min_light_lux INT NOT NULL,
            max_light_lux INT NOT NULL,
            created_by INT,
            original_scenario_id INTEGER DEFAULT NULL
        )
    """)
    # 3. Таблица связей пользователь-сценарий
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_scenarios (
            user_id INTEGER NOT NULL,
            scenario_id INTEGER NOT NULL,
            device_id TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE,
            UNIQUE(user_id, scenario_id, device_id)
        )
    """)
    # 4. Таблица показания счётчиков для некоторого контроллера
    execute_db('''
           CREATE TABLE IF NOT EXISTS sensor_readings (
               iid INTEGER PRIMARY KEY AUTOINCREMENT,
               device_id TEXT NOT NULL,
               temp REAL,
               soil_moisture INTEGER,
               light REAL,
               humidity REAL,
               pump_state BOOLEAN,
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )
       ''')
    # 5. Таблица создания уведомлений
    execute_db('''
            CREATE TABLE IF NOT EXISTS notifications (
                iid INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT NOT NULL,  -- например 'temperature', 'humidity', 'light'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read BOOLEAN DEFAULT 0
            )
        ''')
    # Создаем индексы для ускорения запросов
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_scenarios_user ON user_scenarios(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_scenarios_scenario ON user_scenarios(scenario_id)")
    # Закрываем соединение, заранее сохранив все изменения
    conn.commit()
    conn.close()


def close_db(exception=None): # Закрытие соединения с базой данных.
    db = g.pop('_database', None) # Так удаляем соединение с Базой Данных
    # Если оно не закрыто, то закрываем его
    if db is not None:
        db.close()


def query_db(query, args=(), one=False): # Универсальная функция для выполнения SQL-запросов.
    """
    Args:
        query: SQL запрос
        args: Параметры для запроса
        one: Если True, возвращает одну строку
    Returns:
        Одна строка или список строк
    """
    db = get_db() # Получаем соединение с Базой Данных
    cursor = db.execute(query, args) # Выполняем SQL-запрос с параметрами
    # Если нужна одна строчка, то берём её и закрываем курсор (потому что он больше не нужен)
    if one:
        result = cursor.fetchone()
        cursor.close()
        return result
    # Или берём всё (и закрываем курсор)
    else:
        results = cursor.fetchall()
        cursor.close()
        return results


def execute_db(query, args=()): # Выполняет SQL-запрос и сохраняет изменения.
    """
    Args:
        query: SQL запрос
        args: Параметры для запроса
    Returns:
        ID последней вставленной строки
    """
    db = get_db()  # Получаем соединение с Базой Данных
    cursor = db.execute(query, args)  # Выполняем SQL-запрос с параметрами
    db.commit() # Сохраняем сразу изменения (для упрощения кода)
    # Возвращаем ID последней вставленной записи
    last_id = cursor.lastrowid
    cursor.close()
    return last_id