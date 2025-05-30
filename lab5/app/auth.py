from functools import wraps
from flask import Blueprint, request, render_template, url_for, flash, redirect, session, current_app
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from .repositories.user_repository import UserRepository
from .repositories.role_repository import RoleRepository
from .db import dbConnector as db

user_repository = UserRepository(db)
role_repository = RoleRepository(db)

bp = Blueprint('auth', __name__, url_prefix='/auth')

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Авторизуйтесь для доступа к этой странице.'
login_manager.login_message_category = 'warning'

class User(UserMixin):
    def __init__(self, user_id, username, role_id, role_name):
        self.id = user_id
        self.username = username
        self.role_id = role_id
        self.role_name = role_name

    @property
    def is_admin(self):
        return self.role_id == 1
    
    @property
    def is_user(self):
        return self.role_id == 2

@login_manager.user_loader
def load_user(user_id):
    user_data = user_repository.get_by_id(user_id)
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['role_id'], user_data['role_name'])
    return None

def check_rights(allowed_roles):
    def decorator(f):
        @wraps(f) 
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Авторизуйтесь для доступа к этой странице.', 'warning')
                return redirect(url_for('auth.login', next=request.url))

            if current_user.role_name in allowed_roles:
                return f(*args, **kwargs)
            else:
                flash('У вас недостаточно прав для доступа к данной странице.', 'danger')
                return redirect(url_for('index'))
        return decorated_function
    return decorator

@bp.route('/login', methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember_me = request.form.get('remember_me', None) == 'on'

        user = user_repository.get_by_username_and_password(username, password)

        if user is not None:
            flash('Вход выполнен успешно!', 'success')
            login_user(User(user['id'], user['username'], user['role_id'], user['role_name']), remember = remember_me)
            next_url = request.args.get('next', url_for('index'))
            return redirect(next_url)
        flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('users.index'))