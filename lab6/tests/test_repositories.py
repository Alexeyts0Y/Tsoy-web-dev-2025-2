import pytest
from app.repositories import ReviewRepository, CourseRepository
from app.models import db, User, Course, Review
from sqlalchemy.orm import joinedload # Импортируем joinedload для "жадной" загрузки

def test_add_review(app, test_data):
    with app.app_context():
        review_repo = ReviewRepository(db)
        course_repo = CourseRepository(db)

        # Перезагружаем объекты курса и пользователя в текущем контексте теста
        # Это гарантирует, что они привязаны к текущей сессии SQLAlchemy
        course = db.session.get(Course, test_data['courses']['Python для начинающих'].id)
        user = db.session.get(User, test_data['users']['ivan'].id)

        initial_rating_sum = course.rating_sum
        initial_rating_num = course.rating_num

        new_review = review_repo.add_review(course.id, user.id, 5, 'Это супер курс, мне очень понравилось!')
        course_repo.update_course_rating(course.id, None, 5)

        assert new_review is not None
        assert new_review.course_id == course.id
        assert new_review.user_id == user.id
        assert new_review.rating == 5
        assert new_review.text == 'Это супер курс, мне очень понравилось!'

        updated_course = db.session.get(Course, course.id)
        assert updated_course.rating_sum == initial_rating_sum + 5

def test_update_review(app, test_data):
    with app.app_context():
        review_repo = ReviewRepository(db)
        course_repo = CourseRepository(db)

        # Чтобы найти существующий отзыв безопасно, запрашиваем его в текущей сессии.
        # Используем id из test_data, но получаем свежий объект из БД.
        course_fixture_id = test_data['courses']['Python для начинающих'].id
        user_fixture_id = test_data['users']['petr'].id

        existing_review = db.session.execute(
            db.select(Review)
            .filter_by(user_id=user_fixture_id, course_id=course_fixture_id)
            # Жадная загрузка связанных объектов course и user
            # Это предотвращает DetachedInstanceError при доступе к ним
            .options(joinedload(Review.course), joinedload(Review.user))
        ).scalar_one_or_none()

        assert existing_review is not None, "Тестовый отзыв не найден в фикстуре!"

        # Перезагружаем объект курса, чтобы убедиться, что он привязан к текущей сессии
        course = db.session.get(Course, existing_review.course_id)

        old_rating = existing_review.rating
        initial_rating_sum = course.rating_sum
        initial_rating_num = course.rating_num

        updated_review = review_repo.update_review(existing_review.id, 3, 'Передумал, так себе курс.')
        course_repo.update_course_rating(course.id, old_rating, 3)

        assert updated_review is not None
        assert updated_review.id == existing_review.id
        assert updated_review.rating == 3
        assert updated_review.text == 'Передумал, так себе курс.'

        updated_course = db.session.get(Course, course.id)
        assert updated_course.rating_sum == initial_rating_sum - old_rating + 3
        assert updated_course.rating_num == initial_rating_num

def test_get_review_by_user_and_course(app, test_data):
    with app.app_context():
        review_repo = ReviewRepository(db)
        # Перезагружаем объекты
        course = db.session.get(Course, test_data['courses']['Python для начинающих'].id)
        user = db.session.get(User, test_data['users']['petr'].id)

        review = review_repo.get_review_by_user_and_course(user.id, course.id)
        assert review is not None
        assert review.user_id == user.id
        assert review.course_id == course.id
        assert review.rating == 5

        non_existent_course = db.session.get(Course, test_data['courses']['Основы веб-дизайна'].id)
        non_existent_review = review_repo.get_review_by_user_and_course(user.id, non_existent_course.id)
        assert non_existent_review is None

def test_get_latest_reviews_for_course(app, test_data):
    with app.app_context():
        review_repo = ReviewRepository(db)
        course = db.session.get(Course, test_data['courses']['Python для начинающих'].id)

        latest_reviews = review_repo.get_latest_reviews_for_course(course.id, limit=2)
        assert len(latest_reviews) == 2
        # Отзывы должны быть отсортированы по убыванию created_at.
        # В фикстуре reviews: review1 (user2), review2 (user3), review3 (user1).
        # user1 (review3) был добавлен последним, поэтому должен быть первым.
        assert latest_reviews[0].user.login == 'ivan' # Отзыв 3 (user1) - добавлен последним
        assert latest_reviews[1].user.login == 'anna' # Отзыв 2 (user3) - добавлен вторым
        assert latest_reviews[0].created_at >= latest_reviews[1].created_at


def test_get_paginated_reviews_for_course(app, test_data):
    with app.app_context():
        review_repo = ReviewRepository(db)
        course = db.session.get(Course, test_data['courses']['Python для начинающих'].id)

        # Тест пагинации
        pagination = review_repo.get_paginated_reviews_for_course(course.id, page=1, per_page=2)
        assert pagination.page == 1
        assert len(pagination.items) == 2
        assert pagination.total == 3
        assert pagination.has_next

        pagination = review_repo.get_paginated_reviews_for_course(course.id, page=2, per_page=2)
        assert pagination.page == 2
        assert len(pagination.items) == 1
        assert pagination.has_prev
        assert not pagination.has_next

        # Тест сортировки 'newest' (по умолчанию)
        reviews_newest = review_repo.get_paginated_reviews_for_course(course.id, page=1, per_page=3, sort_by='newest').items
        # Отзывы в фикстуре добавлены в порядке: review1 (user2), review2 (user3), review3 (user1).
        # Таким образом, review3 от user1 будет самым "новым".
        assert reviews_newest[0].user.login == 'ivan' # review3 от user1
        assert reviews_newest[1].user.login == 'anna' # review2 от user3
        assert reviews_newest[2].user.login == 'petr' # review1 от user2

        # Тест сортировки 'positive'
        reviews_positive = review_repo.get_paginated_reviews_for_course(course.id, page=1, per_page=3, sort_by='positive').items
        # Порядок по рейтингу DESC, затем по created_at DESC (если рейтинги одинаковые)
        # review1 (5) от user2, review2 (4) от user3, review3 (2) от user1
        assert reviews_positive[0].user.login == 'petr' # review1
        assert reviews_positive[1].user.login == 'anna' # review2
        assert reviews_positive[2].user.login == 'ivan' # review3

        # Тест сортировки 'negative'
        reviews_negative = review_repo.get_paginated_reviews_for_course(course.id, page=1, per_page=3, sort_by='negative').items
        # Порядок по рейтингу ASC, затем по created_at DESC (если рейтинги одинаковые)
        # review3 (2) от user1, review2 (4) от user3, review1 (5) от user2
        assert reviews_negative[0].user.login == 'ivan' # review3
        assert reviews_negative[1].user.login == 'anna' # review2
        assert reviews_negative[2].user.login == 'petr' # review1