from flask import Flask, request, session, render_template, redirect, flash, url_for
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from lab3.app.user import User

import os

app = Flask(__name__)
application = app

load_dotenv()
app.secret_key = os.getenv('SECRET_KEY')

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'
login_manager.login_message = 'Авторизуйтесь для доступа к этой странице'
login_manager.login_message_category = 'warning'

def get_users():
    return [
        {
            'id': '1',
            'username': 'user',
            'password': 'qwerty'
        },
        {
            'id': '2',
            'username': 'Bob',
            'password': 'Password'
        }
    ]

@login_manager.user_loader
def load_user(user_id):
    for user in get_users():
        if user_id == user['id']:
            return User(user['id'], user['username'])
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/counter')
def counter():
    if session.get('counter'):
        session['counter'] += 1
    else:
        session['counter'] = 1
    return render_template('counter.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me') == 'on'
        if username and password:
            for user in get_users():
                if user['username'] == username and user['password'] == password:
                    user = User(user['id'], user['username'])
                    login_user(user, remember = remember_me)
                    flash('Вход выполнен успешно!', 'success')
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('index'))
            return render_template('login.html', error='Пользователь с таким именем не найден!')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Выход выполнен успешно!', 'success')
    return redirect(url_for('index'))

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html')

if __name__ == "__main__":
    application.run()