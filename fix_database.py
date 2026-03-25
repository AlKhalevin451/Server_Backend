import sqlite3

DATABASE = 'plantcare.db'


def fix_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Добавляем колонку original_scenario_id
        cursor.execute("ALTER TABLE scenarios ADD COLUMN original_scenario_id INTEGER DEFAULT NULL")
        print("✓ Добавлена колонка original_scenario_id")
    except sqlite3.OperationalError as e:
        print(f"Колонка original_scenario_id уже существует или другая ошибка: {e}")

    try:
        # Добавляем колонку description
        cursor.execute("ALTER TABLE scenarios ADD COLUMN description TEXT DEFAULT NULL")
        print("✓ Добавлена колонка description")
    except sqlite3.OperationalError as e:
        print(f"Колонка description уже существует или другая ошибка: {e}")

    # Проверяем структуру таблицы
    cursor.execute("PRAGMA table_info(scenarios)")
    print("\nСтруктура таблицы scenarios:")
    for col in cursor.fetchall():
        print(f"  {col[0]}: {col[1]} ({col[2]})")

    conn.commit()
    conn.close()
    print("\nБаза данных успешно обновлена!")


if __name__ == "__main__":
    fix_database()