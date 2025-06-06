from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from .models import db
from .repositories import CourseRepository, UserRepository, CategoryRepository, ImageRepository, ReviewRepository

user_repository = UserRepository(db)
course_repository = CourseRepository(db)
category_repository = CategoryRepository(db)
image_repository = ImageRepository(db)
review_repository = ReviewRepository(db)

bp = Blueprint('courses', __name__, url_prefix='/courses')

COURSE_PARAMS = [
    'author_id', 'name', 'category_id', 'short_desc', 'full_desc'
]

def params():
    return { p: request.form.get(p) or None for p in COURSE_PARAMS }

def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': [x for x in request.args.getlist('category_ids') if x],
    }

@bp.route('/')
def index():
    pagination = course_repository.get_pagination_info(**search_params())
    courses = course_repository.get_all_courses(pagination=pagination)
    categories = category_repository.get_all_categories()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())

@bp.route('/new')
@login_required
def new():
    course = course_repository.new_course()
    categories = category_repository.get_all_categories()
    users = user_repository.get_all_users()
    return render_template('courses/new.html',
                           categories=categories,
                           users=users,
                           course=course)

@bp.route('/create', methods=['POST'])
@login_required
def create():
    f = request.files.get('background_img')
    img = None
    course = None 

    try:
        if f and f.filename:
            img = image_repository.add_image(f)

        image_id = img.id if img else None
        course = course_repository.add_course(**params(), background_image_id=image_id)
    except IntegrityError as err:
        flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных. ({err})', 'danger')
        categories = category_repository.get_all_categories()
        users = user_repository.get_all_users()
        return render_template('courses/new.html',
                            categories=categories,
                            users=users,
                            course=course)

    flash(f'Курс {course.name} был успешно добавлен!', 'success')

    return redirect(url_for('courses.index'))

@bp.route('/<int:course_id>')
def show(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    latest_reviews = review_repository.get_latest_reviews_for_course(course_id, limit=5)

    user_review = None
    if current_user.is_authenticated:
        user_review = review_repository.get_review_by_user_and_course(current_user.id, course_id)

    return render_template('courses/show.html', 
                           course=course,
                           latest_reviews=latest_reviews,
                           user_review=user_review)

@bp.route('/<int:course_id>/reviews')
def all_reviews(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'newest')
    
    per_page = 10
    
    pagination = review_repository.get_paginated_reviews_for_course(course_id, page, per_page, sort_by)
    reviews = pagination.items

    user_review = None
    if current_user.is_authenticated:
        user_review = review_repository.get_review_by_user_and_course(current_user.id, course_id)

    return render_template('courses/reviews.html',
                           course=course,
                           reviews=reviews,
                           pagination=pagination,
                           user_review=user_review,
                           sort_by=sort_by)

@bp.route('/<int:course_id>/reviews/submit', methods=['POST'])
@login_required
def submit_review(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    rating = request.form.get('rating', type=int)
    text = request.form.get('text')

    if rating is None or not (0 <= rating <= 5):
        flash('Пожалуйста, выберите оценку от 0 до 5.', 'danger')
        return redirect(request.referrer or url_for('courses.show', course_id=course_id))
    if not text or len(text.strip()) < 10:
        flash('Текст отзыва не может быть пустым и должен содержать не менее 10 символов.', 'danger')
        return redirect(request.referrer or url_for('courses.show', course_id=course_id))

    user_id = current_user.id
    existing_review = review_repository.get_review_by_user_and_course(user_id, course_id)
    print("EXISTING REVIEW: ", existing_review)
    if existing_review:
        old_rating = existing_review.rating
        review_repository.update_review(existing_review.id, rating, text)
        course_repository.update_course_rating(course_id, old_rating, rating)
        flash('Ваш отзыв был успешно обновлен!', 'success')
    else:
        review_repository.add_review(course_id, user_id, rating, text)
        # print('Rating : ', rating)
        course_repository.update_course_rating(course_id, None, rating)
        flash('Ваш отзыв был успешно добавлен!', 'success')
    
    return redirect(request.referrer or url_for('courses.all_reviews', course_id=course_id))