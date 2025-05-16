from functools import wraps
from flask import Blueprint, request, render_template, url_for, flash, redirect, session
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from .repositories.user_repository import UserRepository
from .db import dbConnector as db

user_repository = UserRepository(db)

bp = Blueprint('auth', __name__, url_prefix='/auth')

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Авторизуйтесь для доступа к этой странице'
login_manager.login_message_category = 'warning'

class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    user = user_repository.get_by_id(user_id)
    if user is not None:
        return User(user['id'], user['username'])
    
@bp.route('/login', methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember_me = request.form.get('remember_me', None) == 'on'

        user = user_repository.get_by_username_and_password(username, password)

        if user is not None:
            flash('Вход выполнен успешно!', 'success')
            login_user(User(user['id'], user['username']), remember = remember_me)
            next_url = request.args.get('next', url_for('index'))
            return redirect(next_url)
        flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('users.index'))