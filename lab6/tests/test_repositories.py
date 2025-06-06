import pytest
from app.repositories import ReviewRepository, CourseRepository
from app.models import db, User, Course, Review
from sqlalchemy.orm import joinedload

def test_add_review(app, test_data):
    with app.app_context():
        review_repo = ReviewRepository(db)
        course_repo = CourseRepository(db)

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

        course_fixture_id = test_data['courses']['Python для начинающих'].id
        user_fixture_id = test_data['users']['petr'].id

        existing_review = db.session.execute(
            db.select(Review)
            .filter_by(user_id=user_fixture_id, course_id=course_fixture_id)

            .options(joinedload(Review.course), joinedload(Review.user))
        ).scalar_one_or_none()

        assert existing_review is not None, "Тестовый отзыв не найден в фикстуре!"

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

        assert latest_reviews[0].user.login == 'ivan'
        assert latest_reviews[1].user.login == 'anna'
        assert latest_reviews[0].created_at >= latest_reviews[1].created_at


def test_get_paginated_reviews_for_course(app, test_data):
    with app.app_context():
        review_repo = ReviewRepository(db)
        course = db.session.get(Course, test_data['courses']['Python для начинающих'].id)

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

        reviews_newest = review_repo.get_paginated_reviews_for_course(course.id, page=1, per_page=3, sort_by='newest').items

        assert reviews_newest[0].user.login == 'ivan'
        assert reviews_newest[1].user.login == 'anna'
        assert reviews_newest[2].user.login == 'petr'

        reviews_positive = review_repo.get_paginated_reviews_for_course(course.id, page=1, per_page=3, sort_by='positive').items

        assert reviews_positive[0].user.login == 'petr'
        assert reviews_positive[1].user.login == 'anna'
        assert reviews_positive[2].user.login == 'ivan'

        reviews_negative = review_repo.get_paginated_reviews_for_course(course.id, page=1, per_page=3, sort_by='negative').items

        assert reviews_negative[0].user.login == 'ivan'
        assert reviews_negative[1].user.login == 'anna'
        assert reviews_negative[2].user.login == 'petr'