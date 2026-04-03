# auth - Модуль аутентификации пользователей без токенов
# Он отвечает за регистрацию и вход пользователя, а также за функции, связанные с этим
# Используемые библиотеки
import hashlib # Для хеширования паролей
import secrets # Для создания соли (случайной и криптографически безопасной строки)
from flask import request # Для получения HTTP-запросов
from flask import jsonify # Для преобразования данных в JSON-ответ, который можно отдать клиенту


def hash_password(password, salt=None): # Хеширует пароль с солью.
    # Если пароль без соли, то тогда создаём её
    if salt is None:
        salt = secrets.token_hex(16)
    # Хешируем пароль с солью и возвращаем её с хешированным паролем
    hash_obj = hashlib.sha256((password + salt).encode())
    return salt, hash_obj.hexdigest()


def verify_password(password, stored_salt, stored_hash): # Проверяет пароль пользователя.
    _, input_hash = hash_password(password, stored_salt)
    return input_hash == stored_hash


def verify_user_credentials(username, password): # Проверяет username/email и пароль пользователя.
    from database import query_db
    # Если нет пароля или имени пользователя, так и говорим
    if not username or not password:
        return None, "Не указаны email или пароль"
    # Берём информацию о пользователе с именем = username
    user = query_db(
        "SELECT iid, username, salt, password_hash FROM users WHERE username = ?",
        [username], one=True
    )
    # Если user пустой, то это означает, что такого пользователя нет
    if not user:
        return None, "Пользователь не найден"
    # Если пароли не совпали, так и говорим
    if not verify_password(password, user['salt'], user['password_hash']):
        return None, "Неверный пароль"
    # Если всё хорошо, то тогда выводим информацию о пользователе
    return user, None


def get_user_id_from_credentials(): # Получает user_id из учетных данных в запросе.
    # Проверяет username/email и password из тела запроса или заголовков.
    # Сначала пробуем получить информацию из тела запроса
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
    # Если всё равно нет её, то тогда выводим ошибку
    if not username or not password:
        return None, "Не указаны учетные данные"
    # Проверяем на ошибки, связанные с введёнными паролем и именем пользователя
    user, error = verify_user_credentials(username, password)
    if error:
        return None, error
    # Если их нет, выводим информацию об этом пользователе
    return user['iid'], None


def register_user(): # Регистрация нового пользователя.
    # Сначала берём информацию из тела запроса (если её нет, так и говорим)
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400
    # Записываем информацию о пользователе
    username = data.get('username') or data.get('email')
    password = data.get('password')
    # Если чего-то нет, значит, это не указано пользователем
    if not username or not password:
        return jsonify({"success": False, "message": "Необходимо указать email и пароль"}), 400
    # Маленькая длина пароля - плохо, поэтому если это так, то нужно сказать пользователю, что это плохо
    if len(password) < 6:
        return jsonify({"success": False, "message": "Пароль должен содержать минимум 6 символов"}), 400
    # Импортируем функции с SQL-функциями из database
    from database import query_db, execute_db
    # Проверяем существование пользователя
    existing_user = query_db("SELECT 1 FROM users WHERE username = ?", [username], one=True)
    # Если он есть, значит, ещё раз создать аккаунт не получится, и об этом нужно сообщить пользователю
    if existing_user:
        return jsonify({"success": False, "message": "Пользователь с таким email уже существует"}), 409
    # Хешируем пароль
    salt, password_hash = hash_password(password)
    # Пробуем регистрацию пользователя
    try:
        user_id = execute_db(
            "INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?)",
            (username, salt, password_hash)
        )
        # Выводим JSON-ответ на успешную регистрацию пользователя с кодом 201
        return jsonify({
            "success": True,
            "message": "Пользователь успешно зарегистрирован",
            "user": username,
            "user_id": user_id
        }), 201
    # Если произошла какая-то неизвестная ошибка, нужно сообщить об этом пользователю
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500


def login_user(): # Вход пользователя в приложение.
    # Сначала берём информацию из тела запроса (если её нет, так и говорим)
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Отсутствуют данные"}), 400
    # Записываем информацию о пользователе
    username = data.get('username') or data.get('email')
    password = data.get('password')
    # Если чего-то нет, значит, это не указано пользователем
    if not username or not password:
        return jsonify({"success": False, "message": "Необходимо указать email и пароль"}), 400
    # Проверяем на ошибки вход пользователя
    user, error = verify_user_credentials(username, password)
    # Если что-то есть, сообщаем об этом
    if error:
        return jsonify({"success": False, "message": error}), 401
    # Если нет, выводим JSON-ответ на успешный вход пользователя в аккаунт с кодом 200
    return jsonify({
        "success": True,
        "message": "Успешный вход",
        "user": user['username'],
        "user_id": user['iid']
    }), 200