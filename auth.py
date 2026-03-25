<<<<<<< HEAD
"""
auth.py - Модуль аутентификации пользователей без токенов
"""
import hashlib
import secrets
from flask import request, jsonify
=======
# auth.py - Модуль аутентификации пользователей без токенов
# Он отвечает за регистрацию и авторизацию пользователя
# Используемые библиотеки и подключения
import hashlib # Для хеширования паролей и создания соли (случайного набора символов, добавляемого к паролю)
import secrets # Для генерации криптографически безопасных случайных чисел и токенов
from flask import request # Для создания объектов запроса в Flask
from flask import jsonify # Для форматирования JSON-ответов
>>>>>>> 8117b917c1557e15f14883016013ba482e8bf59f

def hash_password(password, salt=None):
    """Хеширует пароль с солью."""
    if salt is None:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return salt, hash_obj.hexdigest()

def verify_password(password, stored_salt, stored_hash):
    """Проверяет пароль пользователя."""
    _, input_hash = hash_password(password, stored_salt)
    return input_hash == stored_hash

def verify_user_credentials(username, password):
    """Проверяет username/email и пароль пользователя."""
    from database import query_db

    if not username or not password:
        return None, "Не указаны email или пароль"

    user = query_db(
        "SELECT iid, username, salt, password_hash FROM users WHERE username = ?",
        [username], one=True
    )

    if not user:
        return None, "Пользователь не найден"

    if not verify_password(password, user['salt'], user['password_hash']):
        return None, "Неверный пароль"

    return user, None

def get_user_id_from_credentials():
    """
    Получает user_id из учетных данных в запросе.
    Проверяет username/email и password из тела запроса или заголовков.
    """
    # Сначала пробуем из тела запроса
    data = request.get_json(silent=True)
    username = None
    password = None

    if data:
        username = data.get('username') or data.get('email')
        password = data.get('password')

    # Если нет в теле, пробуем из заголовков
    if not username or not password:
        username = request.headers.get('X-User-Email') or request.headers.get('X-Username')
        password = request.headers.get('X-User-Password')

    if not username or not password:
        return None, "Не указаны учетные данные"

    user, error = verify_user_credentials(username, password)
    if error:
        return None, error

    return user['iid'], None

def register_user():
    """
    Регистрация нового пользователя.
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400

    username = data.get('username') or data.get('email')
    password = data.get('password')

    if not username or not password:
        return jsonify({"success": False, "message": "Необходимо указать email и пароль"}), 400

    if len(password) < 6:
        return jsonify({"success": False, "message": "Пароль должен содержать минимум 6 символов"}), 400

    from database import query_db, execute_db

    # Проверяем существование пользователя
    existing_user = query_db("SELECT 1 FROM users WHERE username = ?", [username], one=True)

    if existing_user:
        return jsonify({"success": False, "message": "Пользователь с таким email уже существует"}), 409

    # Хешируем пароль
    salt, password_hash = hash_password(password)

    try:
        user_id = execute_db(
            "INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?)",
            (username, salt, password_hash)
        )

        return jsonify({
            "success": True,
            "message": "Пользователь успешно зарегистрирован",
            "user": username,
            "user_id": user_id
        }), 201

    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

def login_user():
    """
    Вход пользователя.
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400

    username = data.get('username') or data.get('email')
    password = data.get('password')

    if not username or not password:
        return jsonify({"success": False, "message": "Необходимо указать email и пароль"}), 400

    user, error = verify_user_credentials(username, password)

    if error:
        return jsonify({"success": False, "message": error}), 401

    return jsonify({
        "success": True,
        "message": "Успешный вход",
        "user": user['username'],
        "user_id": user['iid']
    }), 200