# lab6/tests/test_courses_routes.py

import pytest
from flask import url_for
from app.models import db, User, Course, Review
from app.repositories import ReviewRepository # Для проверки состояния БД
from sqlalchemy import func

review_repo = ReviewRepository(db)

# Хелпер для логина пользователя
def login(client, username, password):
    return client.post('/auth/login', data={
        'login': username,
        'password': password
    }, follow_redirects=True)

def logout(client):
    return client.get('/auth/logout', follow_redirects=True)

# Тест страницы курса (отображение последних отзывов и формы)
def test_show_course_page_displays_reviews_and_form(client, app, test_data):
    course = test_data['courses']['Python для начинающих']
    # Отзывы из фикстуры: review1 (user2, 5), review2 (user3, 4), review3 (user1, 2)
    
    response = client.get(url_for('courses.show', course_id=course.id))
    assert response.status_code == 200
    html = response.data.decode('utf-8')

    assert 'Отличный курс, всё очень понятно!' in html # review1
    assert 'Хороший курс, но есть что улучшить.' in html # review2
    assert 'Не очень понятно, нужно доработать.' in html # review3

    assert 'Войдите</a>, чтобы оставить отзыв.' in html
    assert '<form method="POST" action="/courses/' not in html # Форма не видна без логина

    user_with_review = test_data['users']['petr'] # user2 оставил отзыв
    login(client, user_with_review.login, 'password')
    response = client.get(url_for('courses.show', course_id=course.id))
    html = response.data.decode('utf-8')
    assert f'Ваш отзыв</h5>' in html # Заголовок для отзыва пользователя
    assert 'Отличный курс, всё очень понятно!' in html # Текст отзыва пользователя
    assert 'Редактировать отзыв' in html # Кнопка редактирования
    assert f'Отправить отзыв' not in html # Нет кнопки отправки нового отзыва
    logout(client) # Выходим, чтобы не влиять на другие тесты

    user_no_review = test_data['users']['anna'] # user3 оставил отзыв, но не о этом курсе
    login(client, user_no_review.login, 'password')
    response = client.get(url_for('courses.show', course_id=course.id))
    html = response.data.decode('utf-8')

    assert f'Ваш отзыв</h3>' in html # Заголовок
    assert 'Отправить отзыв' not in html # Кнопка отправки нового отзыва
    assert 'Редактировать отзыв' in html # Нет кнопки редактирования
    assert 'Текст отзыва' in html # Форма отзыва видна
    logout(client)

# Тест добавления нового отзыва
def test_submit_new_review(client, app, test_data):
    user = test_data['users']['ivan'] # Этот пользователь еще не оставлял отзыв о курсе "Python для начинающих"
    course = test_data['courses']['Python для начинающих']

    user = test_data['users']['ivan']
    course = test_data['courses']['Python для начинающих']

    with app.app_context():
        # Было: initial_review_count = db.session.execute(db.select(Review).filter_by(course_id=course.id)).scalar_one_or_none()
        # Стало: Используем func.count() для подсчета количества отзывов
        initial_review_count = db.session.scalar(db.select(func.count(Review.id)).filter_by(course_id=course.id)) # <<< Исправлено
        initial_rating_sum = course.rating_sum
        initial_rating_num = course.rating_num

    # Логинимся как пользователь
    login(client, user.login, 'password')

    response = client.post(url_for('courses.submit_review', course_id=course.id), data={
        'rating': 3,
        'text': 'Новый отзыв от Ивана, очень хорошо!'
    }, follow_redirects=True)

    assert response.status_code == 200 # Успешное перенаправление

    with app.app_context():
        updated_review = review_repo.get_review_by_user_and_course(user.id, course.id)
        assert updated_review is not None
        assert updated_review.rating == 3
        assert updated_review.text == 'Новый отзыв от Ивана, очень хорошо!'

        updated_course = db.session.get(Course, course.id)

        assert updated_course.rating_sum == 12
        assert updated_course.rating_num == 3

    logout(client)

# Тест обновления существующего отзыва
def test_update_existing_review(client, app, test_data):
    user = test_data['users']['petr'] # Этот пользователь уже оставил отзыв
    course = test_data['courses']['Python для начинающих']

    with app.app_context():
        existing_review = review_repo.get_review_by_user_and_course(user.id, course.id)
        old_rating = existing_review.rating # Должно быть 5
        initial_rating_sum = course.rating_sum
        initial_rating_num = course.rating_num

    login(client, user.login, 'password')

    response = client.post(url_for('courses.submit_review', course_id=course.id), data={
        'rating': 3,
        'text': 'Обновленный отзыв от Петра, теперь на троечку.'
    }, follow_redirects=True)

    html = response.data.decode('utf-8') # <<< Добавлено декодирование
    assert response.status_code == 200
    assert 'Ваш отзыв был успешно обновлен!' in html

    with app.app_context():
        updated_review = review_repo.get_review_by_user_and_course(user.id, course.id)
        assert updated_review is not None
        assert updated_review.rating == 3
        assert updated_review.text == 'Обновленный отзыв от Петра, теперь на троечку.'

        updated_course = db.session.get(Course, course.id)
        assert updated_course.rating_sum == initial_rating_sum - old_rating + 3
        assert updated_course.rating_num == initial_rating_num # Количество не меняется

    logout(client)

# Тест валидации отзыва
@pytest.mark.parametrize("rating, text, expected_message", [
    (None, "Valid text", 'Пожалуйста, выберите оценку от 0 до 5.'),
    (6, "Valid text", 'Пожалуйста, выберите оценку от 0 до 5.'),
    (3, "", 'Текст отзыва не может быть пустым и должен содержать не менее 10 символов.'),
    (3, "short", 'Текст отзыва не может быть пустым и должен содержать не менее 10 символов.'),
])
def test_submit_review_validation(client, app, test_data, rating, text, expected_message):
    user = test_data['users']['ivan']
    course = test_data['courses']['Python для начинающих']

    login(client, user.login, 'password')

    response = client.post(url_for('courses.submit_review', course_id=course.id), data={
        'rating': rating,
        'text': text
    }, follow_redirects=True)

    html = response.data.decode('utf-8') # <<< Добавлено декодирование
    assert response.status_code == 200
    assert expected_message in html # <<< Сравниваем со строкой
    assert 'Ваш отзыв был успешно добавлен!' not in html

    logout(client)

# Тест доступа к форме отзыва для неавторизованных
def test_submit_review_unauthenticated(client, app, test_data):
    course = test_data['courses']['Python для начинающих']
    response = client.post(url_for('courses.submit_review', course_id=course.id), data={
        'rating': 5,
        'text': 'Это анонимный отзыв!'
    }, follow_redirects=False) # Не следуем редиректу, чтобы проверить 302

    assert response.status_code == 302 # Должен быть редирект на страницу логина
    assert '/auth/login' in response.headers['Location']

# Тест страницы всех отзывов с пагинацией и сортировкой
def test_all_reviews_page_pagination_and_sorting(client, app, test_data):
    course = test_data['courses']['Python для начинающих']
    # Отзывы: review1 (user2, 5), review2 (user3, 4), review3 (user1, 2)
    # Порядок добавления: review1, review2, review3

    # Тест пагинации (первая страница)
    response = client.get(url_for('courses.all_reviews', course_id=course.id, page=1, per_page=2))
    html = response.data.decode('utf-8')
    assert response.status_code == 200
    assert 'Все отзывы о курсе "Python для начинающих"' in html
    assert 'Отличный курс, всё очень понятно!' in html # review1
    assert 'Хороший курс, но есть что улучшить.' in html # review2
    assert 'Не очень понятно, нужно доработать.' in html # review3 на второй странице

    # Тест пагинации (вторая страница)
    response = client.get(url_for('courses.all_reviews', course_id=course.id, page=2, per_page=2))
    html = response.data.decode('utf-8')
    assert response.status_code == 200
    assert 'Отличный курс, всё очень понятно!' not in html
    assert 'Хороший курс, но есть что улучшить.' not in html
    assert 'Не очень понятно, нужно доработать.' not in html # review3 на второй странице

    # Тест сортировки по новизне (newest)
    response = client.get(url_for('courses.all_reviews', course_id=course.id, sort_by='newest'))
    html = response.data.decode('utf-8')
    # Проверяем порядок
    # review3 (user1) был добавлен последним в фикстуре, поэтому должен быть первым
    assert html.find('Не очень понятно, нужно доработать.') < html.find('Хороший курс, но есть что улучшить.')
    assert html.find('Хороший курс, но есть что улучшить.') < html.find('Отличный курс, всё очень понятно!')


    # Тест сортировки по положительным (positive)
    response = client.get(url_for('courses.all_reviews', course_id=course.id, sort_by='positive'))
    html = response.data.decode('utf-8')
    # review1 (5) -> review2 (4) -> review3 (2)
    assert html.find('Отличный курс, всё очень понятно!') < html.find('Хороший курс, но есть что улучшить.')
    assert html.find('Хороший курс, но есть что улучшить.') < html.find('Не очень понятно, нужно доработать.')

    # Тест сортировки по отрицательным (negative)
    response = client.get(url_for('courses.all_reviews', course_id=course.id, sort_by='negative'))
    html = response.data.decode('utf-8')
    # review3 (2) -> review2 (4) -> review1 (5)
    assert html.find('Не очень понятно, нужно доработать.') < html.find('Хороший курс, но есть что улучшить.')
    assert html.find('Хороший курс, но есть что улучшить.') < html.find('Отличный курс, всё очень понятно!')