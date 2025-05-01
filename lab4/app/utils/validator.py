import re

def validate_password(password):
    errors = []
    
    if not password:
        errors.append("Пароль не может быть пустым")
    elif len(password) < 8:
        errors.append("Пароль должен содержать минимум 8 символов")
    elif len(password) > 128:
        errors.append("Пароль должен содержать не более 128 символов")
    elif not re.search(r'[A-ZА-Я]', password):
        errors.append("Пароль должен содержать хотя бы одну заглавную букву")
    elif not re.search(r'[a-zа-я]', password):
        errors.append("Пароль должен содержать хотя бы одну строчную букву")
    elif not re.search(r'[0-9]', password):
        errors.append("Пароль должен содержать хотя бы одну цифру")
    elif re.search(r'\s', password):
        errors.append("Пароль не должен содержать пробелы")
    elif not re.fullmatch(r'[A-Za-zА-Яа-я0-9~!?@#$%^&*_\-+()\[\]{}><\/\\|"\'\.,:;]+', password):
        errors.append("Пароль содержит недопустимые символы")
    
    return errors

def validate_username(username):
    errors = []
    if not username:
        errors.append("Логин не может быть пустым")
    elif len(username) < 5:
        errors.append("Логин должен содержать минимум 5 символов")
    elif not re.fullmatch(r'^[a-zA-Z0-9]+$', username):
        errors.append("Логин должен содержать только латинские буквы и цифры")
    return errors

def validate_name(name, field_name):
    errors = []
    if not name:
        errors.append(f"{field_name} не может быть пустым")
    return errors