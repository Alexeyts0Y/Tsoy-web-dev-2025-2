import pytest
from flask import url_for
from app.models import db, User, Course, Review
from app.repositories import ReviewRepository
from sqlalchemy import func

review_repo = ReviewRepository(db)

def login(client, username, password):
    return client.post('/auth/login', data={
        'login': username,
        'password': password
    }, follow_redirects=True)

def logout(client):
    return client.get('/auth/logout', follow_redirects=True)

def test_show_course_page_displays_reviews_and_form(client, app, test_data):
    course = test_data['courses']['Python для начинающих']
    
    response = client.get(url_for('courses.show', course_id=course.id))
    assert response.status_code == 200
    html = response.data.decode('utf-8')

    assert 'Отличный курс, всё очень понятно!' in html
    assert 'Хороший курс, но есть что улучшить.' in html
    assert 'Не очень понятно, нужно доработать.' in html

    assert 'Войдите</a>, чтобы оставить отзыв.' in html
    assert '<form method="POST" action="/courses/' not in html

    user_with_review = test_data['users']['petr']
    login(client, user_with_review.login, 'password')
    response = client.get(url_for('courses.show', course_id=course.id))
    html = response.data.decode('utf-8')
    assert f'Ваш отзыв</h5>' in html
    assert 'Отличный курс, всё очень понятно!' in html
    assert 'Редактировать отзыв' in html
    assert f'Отправить отзыв' not in html
    logout(client)

    user_no_review = test_data['users']['anna']
    login(client, user_no_review.login, 'password')
    response = client.get(url_for('courses.show', course_id=course.id))
    html = response.data.decode('utf-8')

    assert f'Ваш отзыв</h3>' in html
    assert 'Отправить отзыв' not in html
    assert 'Редактировать отзыв' in html
    assert 'Текст отзыва' in html
    logout(client)

def test_submit_new_review(client, app, test_data):
    user = test_data['users']['ivan']
    course = test_data['courses']['Python для начинающих']

    user = test_data['users']['ivan']
    course = test_data['courses']['Python для начинающих']

    with app.app_context():
        initial_review_count = db.session.scalar(db.select(func.count(Review.id)).filter_by(course_id=course.id))
        initial_rating_sum = course.rating_sum
        initial_rating_num = course.rating_num

    login(client, user.login, 'password')

    response = client.post(url_for('courses.submit_review', course_id=course.id), data={
        'rating': 3,
        'text': 'Новый отзыв от Ивана, очень хорошо!'
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        updated_review = review_repo.get_review_by_user_and_course(user.id, course.id)
        assert updated_review is not None
        assert updated_review.rating == 3
        assert updated_review.text == 'Новый отзыв от Ивана, очень хорошо!'

        updated_course = db.session.get(Course, course.id)

        assert updated_course.rating_sum == 12
        assert updated_course.rating_num == 3

    logout(client)

def test_update_existing_review(client, app, test_data):
    user = test_data['users']['petr']
    course = test_data['courses']['Python для начинающих']

    with app.app_context():
        existing_review = review_repo.get_review_by_user_and_course(user.id, course.id)
        old_rating = existing_review.rating
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

    html = response.data.decode('utf-8')
    assert response.status_code == 200
    assert expected_message in html
    assert 'Ваш отзыв был успешно добавлен!' not in html

    logout(client)

def test_submit_review_unauthenticated(client, app, test_data):
    course = test_data['courses']['Python для начинающих']
    response = client.post(url_for('courses.submit_review', course_id=course.id), data={
        'rating': 5,
        'text': 'Это анонимный отзыв!'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']

def test_all_reviews_page_pagination_and_sorting(client, app, test_data):
    course = test_data['courses']['Python для начинающих']

    response = client.get(url_for('courses.all_reviews', course_id=course.id, page=1, per_page=2))
    html = response.data.decode('utf-8')
    assert response.status_code == 200
    assert 'Все отзывы о курсе "Python для начинающих"' in html
    assert 'Отличный курс, всё очень понятно!' in html
    assert 'Хороший курс, но есть что улучшить.' in html
    assert 'Не очень понятно, нужно доработать.' in html

    response = client.get(url_for('courses.all_reviews', course_id=course.id, page=2, per_page=2))
    html = response.data.decode('utf-8')
    assert response.status_code == 200
    assert 'Отличный курс, всё очень понятно!' not in html
    assert 'Хороший курс, но есть что улучшить.' not in html
    assert 'Не очень понятно, нужно доработать.' not in html

    response = client.get(url_for('courses.all_reviews', course_id=course.id, sort_by='newest'))
    html = response.data.decode('utf-8')

    assert html.find('Не очень понятно, нужно доработать.') < html.find('Хороший курс, но есть что улучшить.')
    assert html.find('Хороший курс, но есть что улучшить.') < html.find('Отличный курс, всё очень понятно!')

    response = client.get(url_for('courses.all_reviews', course_id=course.id, sort_by='positive'))
    html = response.data.decode('utf-8')

    assert html.find('Отличный курс, всё очень понятно!') < html.find('Хороший курс, но есть что улучшить.')
    assert html.find('Хороший курс, но есть что улучшить.') < html.find('Не очень понятно, нужно доработать.')

    response = client.get(url_for('courses.all_reviews', course_id=course.id, sort_by='negative'))
    html = response.data.decode('utf-8')

    assert html.find('Не очень понятно, нужно доработать.') < html.find('Хороший курс, но есть что улучшить.')
    assert html.find('Хороший курс, но есть что улучшить.') < html.find('Отличный курс, всё очень понятно!')