# lab6/conftest.py

import pytest
from app import create_app
from app.models import db, User, Category, Course, Review, Image
from werkzeug.security import generate_password_hash
import os

# Фикстура для создания тестового Flask-приложения
@pytest.fixture()
def app():
    # Используем конфигурацию для тестов
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', # Используем in-memory SQLite для тестов
        'WTF_CSRF_ENABLED': False, # Отключаем CSRF для удобства тестирования форм
        'UPLOAD_FOLDER': 'test_uploads', # Отдельная папка для загрузок тестов
        # 'DEBUG': True,
        # "ENV": "development",
    })

    # Создаем тестовую папку для загрузок, если её нет
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    with app.app_context():
        db.create_all() # Создаем таблицы в in-memory базе данных

        # Добавляем тестовые данные (фикстуры)
        # Пользователи
        user1 = User(first_name='Иван', last_name='Иванов', login='ivan', password_hash=generate_password_hash('password'))
        user2 = User(first_name='Петр', last_name='Петров', login='petr', password_hash=generate_password_hash('password'))
        user3 = User(first_name='Анна', last_name='Сидорова', login='anna', password_hash=generate_password_hash('password'))
        db.session.add_all([user1, user2, user3])
        db.session.commit()

        # Категории
        category1 = Category(name='Программирование')
        category2 = Category(name='Дизайн')
        db.session.add_all([category1, category2])
        db.session.commit()

        # Изображение
        image1 = Image(id='test_img_1', file_name='test.jpg', mime_type='image/jpeg', md5_hash='hash1')
        db.session.add(image1)
        db.session.commit()
        # Создаем пустой файл для img.storage_filename
        with open(os.path.join(app.config['UPLOAD_FOLDER'], image1.storage_filename), 'w') as f:
            f.write("dummy image content")


        # Курсы
        course1 = Course(
            name='Python для начинающих', short_desc='Краткое описание 1', full_desc='Полное описание 1',
            category=category1, author=user1, bg_image=image1
        )
        course2 = Course(
            name='Основы веб-дизайна', short_desc='Краткое описание 2', full_desc='Полное описание 2',
            category=category2, author=user2, bg_image=image1
        )
        db.session.add_all([course1, course2])
        db.session.commit()

        # Отзывы
        review1 = Review(course=course1, user=user2, rating=5, text='Отличный курс, всё очень понятно!')
        review2 = Review(course=course1, user=user3, rating=4, text='Хороший курс, но есть что улучшить.')
        review3 = Review(course=course1, user=user1, rating=2, text='Не очень понятно, нужно доработать.') # Отзыв автора курса
        db.session.add_all([review1, review2, review3])
        db.session.commit()

        # Обновляем рейтинги курсов после добавления отзывов
        # Это должно быть сделано вручную в фикстуре, т.к. репозиторий это делает при вызове метода
        course1.rating_sum += review1.rating + review2.rating + review3.rating
        course1.rating_num += 3
        db.session.commit()

    yield app # Возвращаем приложение для использования в тестах

    # Очистка после тестов
    with app.app_context():
        db.session.remove()
        db.drop_all() # Удаляем все таблицы
        # Удаляем тестовую папку для загрузок
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            os.rmdir(app.config['UPLOAD_FOLDER'])


# Фикстура для клиента тестирования
@pytest.fixture()
def client(app):
    return app.test_client()

# Фикстура для ранера CLI команд
@pytest.fixture()
def runner(app):
    return app.test_cli_runner()

# Фикстура для доступа к тестовым данным
@pytest.fixture()
def test_data(app):
    with app.app_context():
        return {
            'users': {u.login: u for u in db.session.execute(db.select(User)).scalars().all()},
            'categories': {c.name: c for c in db.session.execute(db.select(Category)).scalars().all()},
            'courses': {c.name: c for c in db.session.execute(db.select(Course)).scalars().all()},
            'images': {i.id: i for i in db.session.execute(db.select(Image)).scalars().all()},
            'reviews': db.session.execute(db.select(Review)).scalars().all()
        }