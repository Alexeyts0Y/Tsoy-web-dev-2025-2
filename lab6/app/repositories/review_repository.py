from ..models import Review
from sqlalchemy import desc, asc
from sqlalchemy.orm import joinedload

class ReviewRepository:
    def __init__(self, db):
        self.db = db

    def add_review(self, course_id, user_id, rating, text):
        review = Review(
            course_id=course_id,
            user_id=user_id,
            rating=rating,
            text=text
        )
        self.db.session.add(review)
        self.db.session.commit()
        return review

    def update_review(self, review_id, rating, text):
        review = self.db.session.get(Review, review_id)
        if review:
            review.rating = rating
            review.text = text
            self.db.session.commit()
        return review

    def get_review_by_user_and_course(self, user_id, course_id):
        return self.db.session.execute(
            self.db.select(Review).filter_by(user_id=user_id, course_id=course_id)
        ).scalar_one_or_none()

    def get_latest_reviews_for_course(self, course_id, limit=5):
        return self.db.session.execute(
            self.db.select(Review)
            .filter_by(course_id=course_id)
            .order_by(desc(Review.created_at))
            .limit(limit)
            .options(joinedload(Review.user))
        ).scalars().all()

    def get_paginated_reviews_for_course(self, course_id, page, per_page, sort_by='newest'):
        query = self.db.select(Review).filter_by(course_id=course_id).options(joinedload(Review.user))

        if sort_by == 'positive':
            query = query.order_by(Review.rating.desc(), Review.created_at.desc())
        elif sort_by == 'negative':
            query = query.order_by(Review.rating.asc(), Review.created_at.desc())
        else:
            query = query.order_by(Review.created_at.desc())

        return self.db.paginate(query, page=page, per_page=per_page, error_out=False)