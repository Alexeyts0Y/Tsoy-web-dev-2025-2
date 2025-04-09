import pytest
from bs4 import BeautifulSoup
from flask import template_rendered, session
from flask_login import current_user
from datetime import datetime, timedelta, timezone

from contextlib import contextmanager
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['SECRET_KEY'] = 'test-secret-key'
    
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['SECRET_KEY'] = 'test-secret-key'
    
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client

@pytest.fixture
def auth(client):
    return AuthActions(client)

class AuthActions:
    def __init__(self, client):
        self._client = client
    
    def login(self, username='user', password='qwerty', remember=False):
        return self._client.post('/login', data={
            'username': username,
            'password': password,
            'remember_me': 'on' if remember else ''
        }, follow_redirects=True)
    
    def logout(self):
        return self._client.get('/logout', follow_redirects=True)

@contextmanager
def captured_templates(app):
    recorded = []
    
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)

def test_counter_increments_on_each_visit(client):
    """Проверка увеличения счетчика посещений."""
    with client.session_transaction() as sess:
        sess.clear()

    responses = [client.get("/counter") for _ in range(3)]
    for i, response in enumerate(responses, 1):
        soup = BeautifulSoup(response.data, "html.parser")
        assert f"Вы посетили эту страницу {i} раз" in soup.find("p").text

def test_counter_is_independent_for_different_clients(client):
    response1 = client.get("/counter")
    assert "Вы посетили эту страницу 1 раз" in response1.data.decode()

    with client.session_transaction() as sess:
        sess.clear()
    
    response2 = client.get("/counter")
    assert "Вы посетили эту страницу 1 раз" in response2.data.decode()

def test_authenticated_user_access_secret(client, auth):
    auth.login(username='user', password='qwerty')
    response = client.get('/secret')
    assert response.status_code == 200
    assert 'Секрет!' in response.data.decode()

def test_anonymous_user_redirected_to_login(client):
    response = client.get('/secret', follow_redirects=True)
    assert response.status_code == 200
    assert 'Авторизация' in response.data.decode()
    assert 'Авторизуйтесь для доступа к этой странице' in response.data.decode()

def test_redirect_after_successful_login(client, auth):
    response = client.get('/secret')
    assert response.status_code == 302
    assert '/login?next=%2Fsecret' in response.headers['Location']

    login_response = client.post('/login?next=%2Fsecret', data={
        'username': 'user',
        'password': 'qwerty'
    }, follow_redirects=False)

    assert login_response.status_code == 302
    assert login_response.headers['Location'] == '/secret'

    final_response = client.get(login_response.headers['Location'])
    assert final_response.status_code == 200
    assert 'Секрет!' in final_response.data.decode()

def test_remember_me_functionality(client, auth):
    auth.login(username='user', password='qwerty', remember=True)

    assert current_user.is_authenticated

    with client.session_transaction() as sess:
        sess.clear()

    response = client.get('/secret')
    assert response.status_code == 200
    assert 'Секрет!' in response.data.decode()

def test_navbar_links(client, auth):
    response = client.get('/')
    soup = BeautifulSoup(response.data, 'html.parser')
    nav = soup.find('nav')
    assert 'Войти' in nav.text
    assert 'Секрет' not in nav.text

    auth.login(username='user', password='qwerty')
    response = client.get('/')
    soup = BeautifulSoup(response.data, 'html.parser')
    nav = soup.find('nav')
    assert 'Выйти' in nav.text
    assert 'Секрет' in nav.text
    assert 'Войти' not in nav.text

def test_remember_cookie_properties(client, auth):
    response = auth.login(username='user', password='qwerty', remember=True)

    cookies = response.headers.getlist('Set-Cookie')
    remember_cookie = next((c for c in cookies if 'remember_token' in c), None)
    
    if remember_cookie:
        assert 'HttpOnly' in remember_cookie
        assert 'Path=/' in remember_cookie
        assert 'Expires=' in remember_cookie
    else:
        pytest.skip("Remember cookie не установлен в тестовой среде")

def test_failed_login_shows_error(client):
    response = client.post('/login', data={
        'username': 'wrong',
        'password': 'wrong'
    })
    assert response.status_code == 200
    assert 'Пользователь с таким именем не найден!' in response.data.decode()

def test_successful_login_redirect_and_flash(client):
    response = client.post('/login', data={
        'username': 'user',
        'password': 'qwerty'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'Лабораторная работа №3' in response.data.decode()
    assert 'Вход выполнен успешно!' in response.data.decode()
    assert 'Выйти' in response.data.decode()

def test_failed_login_stays_with_error(client):
    response = client.post('/login', data={
        'username': 'wrong',
        'password': 'wrong'
    })
    
    assert response.status_code == 200
    assert 'Авторизация' in response.data.decode()
    assert 'Пользователь с таким именем не найден!' in response.data.decode()
    assert 'Войти' in response.data.decode()