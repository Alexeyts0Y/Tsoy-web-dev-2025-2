import os
from functools import reduce
from collections import namedtuple
import logging
import pytest
import mysql.connector
from .. import create_app
from ..db import DBConnector
from ..repositories.role_repository import RoleRepository
from ..repositories.user_repository import UserRepository

from flask_login import FlaskLoginClient
from contextlib import contextmanager
from flask import Flask, template_rendered
from ..auth import User

TEST_DB_CONFIG = {
    'MYSQL_USER': 'tsoy',
    'MYSQL_PASSWORD': 'password',
    'MYSQL_HOST': 'localhost',
    'MYSQL_DATABASE': 'tsoy_lab4'
}

RoleRow = namedtuple('RoleRow', ['id', 'name'])
UserRow = namedtuple('UserRow', ['id', 'username', 'password', 'first_name', 'last_name', 'role_id'])

def get_connection(app):
    return mysql.connector.connect(
        user = app.config['MYSQL_USER'],
        password = app.config['MYSQL_PASSWORD'],
        host = app.config['MYSQL_HOST']
    )

def setup_db(app):
    logging.getLogger().info("Create db...")

    test_db_name = app.config['MYSQL_DATABASE']
    create_db_query = f"""DROP DATABASE IF EXISTS {test_db_name}; 
                          CREATE DATABASE {test_db_name}; 
                          USE {test_db_name};"""

    with app.open_resource('tests/test_schema.sql') as f:
        connection = get_connection(app)

        sql_script = f.read().decode('utf8')
        schema_query = [q.strip() for q in sql_script.split(';') if q.strip()]

        create_db_queries = [q.strip() for q in create_db_query.split(';') if q.strip()]
        # queries = '\n'.join([create_db_query, schema_query])

        with connection.cursor() as cursor:
            for query in create_db_queries:
                if query:
                    cursor.execute(query)
            for query in schema_query:
                if query:
                    cursor.execute(query)
        connection.commit()
        connection.close()

def teardown_db(app):
    logging.getLogger().info("Drop db...")
    test_db_name = app.config['MYSQL_DATABASE']
    connection = get_connection(app)
    with connection.cursor() as cursor:
        cursor.execute(f'DROP DATABASE IF EXISTS {test_db_name}')
    connection.close()

###############################

@pytest.fixture(scope='session')
def app():
    app = create_app(TEST_DB_CONFIG)
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False
    })
    app.test_client_class = FlaskLoginClient
    yield app

@pytest.fixture
@contextmanager
def captured_templates(app):
    recorded = []
    def record(sender, template, context, **extra):
        print(**extra)
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)

@pytest.fixture()
def client(app):
    with app.app_context():
        with app.test_client() as client:
            yield client

@pytest.fixture
def logged_in_client(app, existing_user):
    with app.app_context():
        user=User(existing_user.id, existing_user.username)
        with app.test_client(user=user) as logged_in_client:
            yield logged_in_client

#################################

@pytest.fixture(scope='session')
def db_connector(app):
    conn = mysql.connector.connect(
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        host=app.config['MYSQL_HOST']
    )
    cursor = conn.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {app.config['MYSQL_DATABASE']}")
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    setup_db(app)
    
    connector = DBConnector(app)
    yield connector

    connector.disconnect()
    teardown_db(app)

@pytest.fixture
def role_repository(db_connector):
    return RoleRepository(db_connector)

@pytest.fixture
def existing_role(db_connector):
    data = (1, 'admin')
    role = RoleRow(*data)

    connection = db_connector.connect()
    with connection.cursor() as cursor:
        cursor.execute('DELETE FROM users WHERE role_id = %s', (data[0],))
        connection.commit()
        
        cursor.execute('INSERT INTO roles(id, name) VALUES (%s, %s);', data)
        connection.commit()

    yield role

    with connection.cursor() as cursor:
        cursor.execute('DELETE FROM users WHERE role_id = %s', (role.id,))
        cursor.execute('DELETE FROM roles WHERE id = %s', (role.id,))
        connection.commit()

@pytest.fixture
def nonexisting_role_id():
    return 1

@pytest.fixture
def example_roles(db_connector):
    data = [(1, 'admin'), (2, 'test')]
    roles = [RoleRow(*row_data) for row_data in data]

    connection = db_connector.connect()
    with connection.cursor() as cursor:
        placeholders = ', '.join(['(%s, %s)' for _ in range(len(data))])
        query = f'INSERT INTO roles(id, name) VALUES {placeholders};'
        cursor.execute(query, reduce(lambda seq, x: seq + list(x), data, []))
        connection.commit()

    yield roles

    with connection.cursor() as cursor:
        role_ids = ', '.join([str(role.id) for role in roles])
        query = f'DELETE FROM roles WHERE id IN ({role_ids});'
        cursor.execute(query)
        connection.commit()

@pytest.fixture
def user_repository(db_connector):
    return UserRepository(db_connector)

@pytest.fixture
def existing_user(db_connector, existing_role):
    user_data = (1, 'admin', 'qwerty', 'Студент', 'Студент', int(existing_role.id))
    user = UserRow(*user_data)

    connection = db_connector.connect()
    with connection.cursor() as cursor:
        query = (
            "INSERT INTO users (id, username, password_hash, first_name, last_name, role_id) VALUES "
            "(%s, %s, SHA2(%s, 256), %s, %s, %s);"
        )
        cursor.execute(query, user_data)
        connection.commit()

    yield user

    with connection.cursor() as cursor:
        query = 'DELETE FROM users WHERE id=%s'
        cursor.execute(query, (user.id,))
        connection.commit()

@pytest.fixture
def nonexisting_user():
    user_data = (1, 'admin', 'qwerty', 'Студент', 'Студент', '1')
    return UserRow(*user_data)

@pytest.fixture
def example_users(db_connector, existing_role):
    data = [
        (1, 'admin', 'qwerty', 'Студент', 'Студент', existing_role.id), 
        (2, 'test', 'qwerty', 'Тест', 'Тест', existing_role.id)
    ]
    users = [UserRow(*row_data) for row_data in data]

    connection = db_connector.connect()
    with connection.cursor() as cursor:
        placeholders = ', '.join(['(%s, %s, SHA2(%s, 256), %s, %s, %s)' for _ in range(len(data))])
        query = f"INSERT INTO users(id, username, password_hash, first_name, last_name, role_id) VALUES {placeholders};"
        cursor.execute(query, reduce(lambda seq, x: seq + list(x), data, []))
        connection.commit()

    yield users

    with connection.cursor() as cursor:
        user_ids = ', '.join([str(user.id) for user in users])
        query = f'DELETE FROM users WHERE id IN ({user_ids});'
        cursor.execute(query)
        connection.commit()


def test_data():
    return [
        (
            {'username': '',
             'password': '',
             'first_name': '',
             'last_name': ''}, 
            {'username': 'Логин не может быть пустым',
             'password': 'Пароль не может быть пустым',
             'first_name': 'Поле не может быть пустым',
             'last_name': 'Поле не может быть пустым'}
        ),
        (
            {'username': 'Test1',
             'password': 'Test123',
             'first_name': 'Test',
             'last_name': 'Test'},
            {'password': 'Пароль должен содержать минимум 8 символов'}
        ),
        (
            {'username': 'Test1',
             'password': 'Qa2345678910Qa2345678910Qa2345678910Qa2345678910Qa23456789'
            '10Qa2345678910Qa2345678910Qa2345678910Qa2345678910Qa2345678910Qa2345678910Qa2345678910Qa2345678910',
             'first_name': 'Test',
             'last_name': 'Test'},
            {'password': 'Пароль должен содержать не более 128 символов'}
        ),
        (
            {'username': 'Test1',
             'password': 'a1234567',
             'first_name': 'Test',
             'last_name': 'Test'},
            {'password': 'Пароль должен содержать хотя бы одну заглавную букву'}
        ),
        (
            {'username': 'Test1',
             'password': 'Q12345678',
             'first_name': 'Test',
             'last_name': 'Test'},
            {'password': 'Пароль должен содержать хотя бы одну строчную букву'}
        ),
        (
            {'username': 'Test1',
             'password': 'Qazwsxedc',
             'first_name': 'Test',
             'last_name': 'Test'},
            {'password': 'Пароль должен содержать хотя бы одну цифру'}
        ),
        (
            {'username': 'Test1',
             'password': 'Qazwsxe132c☻♠○◘♣♥•♦☺♫◄↕☺►♪',
             'first_name': 'Test',
             'last_name': 'Test'},
            {'password': 'Пароль содержит недопустимые символы'}
        ),
    ]