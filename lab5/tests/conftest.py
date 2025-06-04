import pytest
from unittest.mock import MagicMock, patch
from flask import Flask
from app import create_app 
from app.auth import User as AuthUser
from app.db import dbConnector

admin_user_data = {'id': 1, 'username': 'admin', 'role_id': 1, 'role_name': 'admin', 'first_name': 'Admin', 'last_name': 'User', 'middle_name': None, 'created_at': '2023-01-01'}
regular_user_data = {'id': 2, 'username': 'user1', 'role_id': 2, 'role_name': 'user', 'first_name': 'Regular', 'last_name': 'User1', 'middle_name': 'Test', 'created_at': '2023-01-02'}
another_user_data = {'id': 3, 'username': 'user2', 'role_id': 2, 'role_name': 'user', 'first_name': 'Another', 'last_name': 'User2', 'middle_name': None, 'created_at': '2023-01-03'}

@pytest.fixture(scope='session')
def app():
    app_instance = create_app({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'LOGIN_DISABLED': False,
        'SECRET_KEY': 'test_secret_key',
        'SERVER_NAME': 'localhost.test',
        'APPLICATION_ROOT': '/',
        'PREFERRED_URL_SCHEME': 'http',
        'MYSQL_USER': 'test_user',
        'MYSQL_PASSWORD': 'test_password',
        'MYSQL_HOST': 'localhost',
        'MYSQL_DATABASE': 'test_db'
    })

    mock_db_connection_actual = MagicMock()
    mock_db_cursor_actual = MagicMock()
    mock_db_connection_actual.cursor.return_value.__enter__.return_value = mock_db_cursor_actual
    
    with patch('mysql.connector.connect', return_value=mock_db_connection_actual) as _:
        if hasattr(dbConnector, 'init_app') and callable(getattr(dbConnector, 'init_app')):
            dbConnector.init_app(app_instance)

        with app_instance.app_context():
            yield app_instance

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_db_connector():
    mock_connector_instance = MagicMock(spec=dbConnector)
    mock_connection = MagicMock()
    mock_cursor = MagicMock()

    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    mock_connector_instance.connect.return_value = mock_connection
    return mock_connector_instance

@pytest.fixture
def mock_admin_user():
    return AuthUser(admin_user_data['id'], admin_user_data['username'], admin_user_data['role_id'], admin_user_data['role_name'])

@pytest.fixture
def mock_regular_user():
    return AuthUser(regular_user_data['id'], regular_user_data['username'], regular_user_data['role_id'], regular_user_data['role_name'])

@pytest.fixture
def mock_another_user():
    return AuthUser(another_user_data['id'], another_user_data['username'], another_user_data['role_id'], another_user_data['role_name'])

@pytest.fixture
def mock_user_repo(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr('app.auth.user_repository', mock)
    monkeypatch.setattr('app.users.user_repository', mock)
    mock.get_by_id.return_value = None
    return mock

@pytest.fixture
def mock_role_repo(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr('app.auth.role_repository', mock)
    monkeypatch.setattr('app.users.role_repository', mock)
    mock.all.return_value = [
        {'id': 1, 'name': 'admin'},
        {'id': 2, 'name': 'user'}
    ]
    return mock

@pytest.fixture
def mock_visit_log_repo(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr('app.visit_logger.visit_log_repository', mock)
    return mock


@pytest.fixture
def login_as(app, client, monkeypatch, mock_user_repo):
    def _login_as(user_to_login_obj):
        if user_to_login_obj:
            user_data_for_load = {
                'id': user_to_login_obj.id,
                'username': user_to_login_obj.username,
                'role_id': user_to_login_obj.role_id,
                'role_name': user_to_login_obj.role_name
            }

            def side_effect_get_by_id(user_id_arg):
                if str(user_id_arg) == str(user_to_login_obj.id):
                    return user_data_for_load
                return None
            mock_user_repo.get_by_id.side_effect = side_effect_get_by_id

            monkeypatch.setattr('flask_login.utils._get_user', lambda: user_to_login_obj)

            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_to_login_obj.id)
                sess['_fresh'] = True
        else:
            mock_user_repo.get_by_id.side_effect = None
            mock_user_repo.get_by_id.return_value = None

            anonymous_user_instance = app.login_manager.anonymous_user()
            monkeypatch.setattr('flask_login.utils._get_user', lambda: anonymous_user_instance)

            with client.session_transaction() as sess:
                sess.pop('_user_id', None)
                sess.pop('_fresh', None)
    return _login_as