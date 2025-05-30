import pytest

from unittest.mock import MagicMock
from flask import Flask
from flask_login import current_user

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app # Assuming you have a create_app function in app.py
from app.auth import login_manager, User as AuthUser # Import User from auth.py
from app.repositories.user_repository import UserRepository
from app.repositories.visit_log_repository import VisitLogRepository
from app.db import dbConnector

@pytest.fixture
def mock_db_connector():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    return MagicMock(connect=MagicMock(return_value=mock_conn))

@pytest.fixture(scope='session')
def live_db_connector():
    class TestDBConnector:
        def connect(self):
            return dbConnector.connect() # Assuming dbConnector from your db.py handles connection
    return TestDBConnector()

@pytest.fixture
def user_repo(mock_db_connector):
    return UserRepository(mock_db_connector)

@pytest.fixture
def visit_log_repo(mock_db_connector):
    return VisitLogRepository(mock_db_connector)

@pytest.fixture(scope='session')
def app():
    _app = create_app(test_config={
        'TESTING': True,
        'SECRET_KEY': 'your_test_secret_key_here', # Замените на ваш тестовый секретный ключ
    })

    with _app.app_context():
        yield _app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def admin_user(app):
    with app.app_context():
        user = AuthUser(user_id=1, username='admin_test', role_id=1, role_name='admin')
    return user

@pytest.fixture
def regular_user(app):
    with app.app_context():
        user = AuthUser(user_id=2, username='user_test', role_id=2, role_name='user')
    return user

@pytest.fixture
def login_as(mocker):
    def _login_as(user):
        mocker.patch('flask_login.current_user', new=user)
        return user
    return _login_as

@pytest.fixture
def mock_visit_log_creation(mocker):
    return mocker.patch('visit_logger.visit_log_repository.create')

@pytest.fixture
def assert_redirect_and_flash(client):
    def _assert_redirect_and_flash(response, expected_url, expected_message_part):
        assert response.status_code == 302
        assert response.headers['Location'].endswith(expected_url)

        with client.session_transaction() as sess:
            flashed_messages = [msg[0] for msg in sess.get('_flashes', [])]
            assert any(expected_message_part in msg for msg in flashed_messages)

        return _assert_redirect_and_flash
    
