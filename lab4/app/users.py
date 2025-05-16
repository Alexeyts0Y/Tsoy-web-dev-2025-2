from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
import mysql.connector as connector

from .repositories.user_repository import UserRepository
from .repositories.role_repository import RoleRepository

from .utils.validator import *

from .db import dbConnector as db

user_repository = UserRepository(db)
role_repository = RoleRepository(db)

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/')
def index():
    return render_template('users/index.html', users=user_repository.all())

@bp.route('/<int:user_id>')
def show(user_id):
    user = user_repository.get_by_id(user_id)
    if user is None:
        flash('Пользователя нет в БД!', 'danger')
        return redirect(url_for('users.index'))
    user_role = role_repository.get_by_id(user['role_id'])
    return render_template('users/show.html', user_data=user, user_role=user_role['name'])

@bp.route('/new', methods=['POST', 'GET'])
@login_required
def new():
    user_data = {}
    errors = {}

    if request.method == 'POST':
        fields = ('username', 'password', 'first_name', 'middle_name', 'last_name', 'role_id')
        user_data = {field: request.form.get(field) or None for field in fields}

        errors['username'] = validate_username(user_data['username'])
        errors['password'] = validate_password(user_data['password'])
        errors['first_name'] = validate_name(user_data['first_name'], 'Имя')
        errors['last_name'] = validate_name(user_data['last_name'], 'Фамилия')

        if not any(errors.values()):
            try:
                user_repository.create(**user_data)
                flash('Пользователь создан!', 'success')
                return redirect(url_for('users.index'))
            except connector.errors.DatabaseError:
                flash('Произошла ошибка при создании пользователя. Проверьте, что все необходимые поля заполнены', 'danger')
                db.connect().rollback()

    errors = {k: v for k, v in errors.items() if v}
    return render_template('users/new.html', user_data=user_data, roles=role_repository.all(), errors=errors)

@bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
def delete(user_id):
    user_repository.delete(user_id)
    flash('Пользователь удален!', 'success')
    return redirect(url_for('users.index'))

@bp.route('/<int:user_id>/edit', methods=['POST', 'GET'])
@login_required
def edit(user_id):
    user = user_repository.get_by_id(user_id)

    if user is None:
        flash('Пользователя нет в БД!', 'danger')
        return redirect(url_for('users.index'))

    errors = {}
    
    if request.method == 'POST':
        fields = ('first_name', 'middle_name', 'last_name', 'role_id')
        user_data = {field: request.form.get(field) or None for field in fields}
        user_data['user_id'] = user_id

        errors['first_name'] = validate_name(user_data['first_name'], 'Имя')
        errors['last_name'] = validate_name(user_data['last_name'], 'Фамилия')

        if not any(errors.values()):
            try:
                user_repository.update(**user_data)
                flash('Пользователь изменен!', 'success')
                return redirect(url_for('users.index'))
            except connector.errors.DatabaseError:
                flash('Ошибка при изменении записи!', 'danger')
                db.connect.rollback()
        else:
            user = {**user, **user_data}
            
    errors = {k: v for k, v in errors.items() if v}
    return render_template('users/edit.html', user_data=user, roles=role_repository.all(), errors=errors)

@bp.route('/<int:user_id>/edit_password', methods=['POST', 'GET'])
@login_required
def edit_password(user_id):
    user = user_repository.get_by_id(user_id)

    if user is None:
        flash('Пользователя нет в БД!', 'danger')
        return redirect(url_for('users.index'))
    
    errors = {}

    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        repeat_password = request.form.get('repeat_new_password')

        if not old_password:
            errors['old_password'] = "Введите старый пароль"

        password_errors = validate_password(new_password)
        if password_errors:
            errors['new_password'] = password_errors

        if new_password != repeat_password:
            errors['repeat_new_password'] = ["Пароли не совпадают"]

        if not errors:
            try:
                if not user_repository.check_password(user_id, old_password):
                    errors['old_password'] = ["Неверный текущий пароль"]
                else:
                    user_repository.update_password(user_id, new_password)
                    flash('Пароль изменен!', 'success')
                    return redirect(url_for('users.index'))
            except connector.errors.DatabaseError as e:
                flash(f'Ошибка при изменении пароля: {str(e)}', 'danger')
                db.connect().rollback()
        
        return render_template('users/edit_password.html', errors=errors, old_password=old_password, new_password=new_password)
    
    return render_template('users/edit_password.html')