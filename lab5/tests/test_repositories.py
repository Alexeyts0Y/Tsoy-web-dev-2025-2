import pytest
from unittest.mock import MagicMock

from app.repositories.user_repository import UserRepository
from app.repositories.visit_log_repository import VisitLogRepository
from datetime import datetime

def test_user_repository_get_by_id(mock_db_connector):
    repo = UserRepository(mock_db_connector)
    mock_cursor = mock_db_connector.connect.return_value.cursor.return_value.__enter__.return_value
    mock_cursor.fetchone.return_value = {'id': 1, 'username': 'testuser', 'role_id': 1, 'role_name': 'admin'}

    user = repo.get_by_id(1)

    assert user is not None
    assert user['username'] == 'testuser'
    mock_cursor.execute.assert_called_once_with(
        'SELECT users.*, roles.name AS role_name FROM users LEFT JOIN roles ON users.role_id = roles.id WHERE users.id = %s;', (1,)
    )

def test_user_repository_get_by_username_and_password(mock_db_connector):
    repo = UserRepository(mock_db_connector)
    mock_cursor = mock_db_connector.connect.return_value.cursor.return_value.__enter__.return_value
    mock_cursor.fetchone.return_value = {'id': 1, 'username': 'admin', 'role_id': 1, 'role_name': 'admin'}

    user = repo.get_by_username_and_password('admin', 'password')

    assert user is not None
    assert user['username'] == 'admin'

    actual_query = mock_cursor.execute.call_args[0][0]
    actual_params = mock_cursor.execute.call_args[0][1]

    assert 'SHA2(%s, 256)' in actual_query
    assert actual_params == ('admin', 'password')

def test_user_repository_create(mock_db_connector):
    repo = UserRepository(mock_db_connector)
    mock_connection = mock_db_connector.connect.return_value
    mock_cursor = mock_connection.cursor.return_value.__enter__.return_value

    repo.create('newuser', 'pass123', 'John', None, 'Doe', 2)

    mock_cursor.execute.assert_called_once()
    mock_connection.commit.assert_called_once()
    actual_query = mock_cursor.execute.call_args[0][0]
    actual_params = mock_cursor.execute.call_args[0][1]

    assert 'INSERT INTO users' in actual_query
    assert actual_params[0] == 'newuser'
    assert actual_params[1] == 'pass123'

def test_user_repository_update(mock_db_connector):
    repo = UserRepository(mock_db_connector)
    mock_connection = mock_db_connector.connect.return_value
    mock_cursor = mock_connection.cursor.return_value.__enter__.return_value

    repo.update(1, 'Jane', 'Middle', 'Doe', 2)

    mock_cursor.execute.assert_called_once()
    mock_connection.commit.assert_called_once()
    actual_query = mock_cursor.execute.call_args[0][0]
    actual_params = mock_cursor.execute.call_args[0][1]

    assert 'UPDATE users SET first_name = %s' in actual_query
    assert actual_params[0] == 'Jane'
    assert actual_params[4] == 1

def test_user_repository_delete(mock_db_connector):
    repo = UserRepository(mock_db_connector)
    mock_connection = mock_db_connector.connect.return_value
    mock_cursor = mock_connection.cursor.return_value.__enter__.return_value

    repo.delete(1)

    mock_cursor.execute.assert_called_once_with('DELETE FROM users WHERE id = %s', (1,))
    mock_connection.commit.assert_called_once()

def test_user_repository_check_password(mock_db_connector):
    repo = UserRepository(mock_db_connector)
    mock_cursor = mock_db_connector.connect.return_value.cursor.return_value.__enter__.return_value
    mock_cursor.fetchone.return_value = (1,)

    result = repo.check_password(1, 'correct_password')

    assert result is not None
    mock_cursor.execute.assert_called_once()
    actual_query = mock_cursor.execute.call_args[0][0]
    actual_params = mock_cursor.execute.call_args[0][1]

    assert 'WHERE id = %s AND password_hash = SHA2(%s, 256)' in actual_query
    assert actual_params == (1, 'correct_password')

def test_user_repository_check_password_no_match(mock_db_connector):
    repo = UserRepository(mock_db_connector)
    mock_cursor = mock_db_connector.connect.return_value.cursor.return_value.__enter__.return_value
    mock_cursor.fetchone.return_value = None

    result = repo.check_password(1, 'wrong_password')

    assert result is None
    mock_cursor.execute.assert_called_once()

def test_visit_log_repository_create(mock_db_connector):
    repo = VisitLogRepository(mock_db_connector)
    mock_connection = mock_db_connector.connect.return_value
    mock_cursor = mock_connection.cursor.return_value.__enter__.return_value

    repo.create('/some/path', user_id=1)

    mock_cursor.execute.assert_called_once()
    mock_connection.commit.assert_called_once()
    actual_query = mock_cursor.execute.call_args[0][0]
    actual_params = mock_cursor.execute.call_args[0][1]

    assert 'INSERT INTO visit_logs (path, user_id) VALUES (%s, %s);' in actual_query
    assert actual_params == ('/some/path', 1)

def test_visit_log_repository_get_all_logs(mock_db_connector):
    repo = VisitLogRepository(mock_db_connector)
    mock_cursor = mock_db_connector.connect.return_value.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = [
        {'id': 1, 'path': '/page1', 'created_at': datetime.now(), 'first_name': 'A', 'last_name': 'B', 'middle_name': None},
        {'id': 2, 'path': '/page2', 'created_at': datetime.now(), 'first_name': None, 'last_name': None, 'middle_name': None}
    ]

    logs = repo.get_all_logs(limit=10, offset=0, user_id=1)

    assert len(logs) == 2
    assert logs[0]['path'] == '/page1'
    mock_cursor.execute.assert_called_once()
    actual_query = mock_cursor.execute.call_args[0][0]
    actual_params = mock_cursor.execute.call_args[0][1]

    assert 'ORDER BY vl.created_at DESC LIMIT %s OFFSET %s' in actual_query
    assert actual_params == (1, 10, 0)

def test_visit_log_repository_get_log_count(mock_db_connector):
    repo = VisitLogRepository(mock_db_connector)
    mock_cursor = mock_db_connector.connect.return_value.cursor.return_value.__enter__.return_value
    mock_cursor.fetchone.return_value = (5,)

    count = repo.get_log_count(user_id=1)

    assert count == 5
    mock_cursor.execute.assert_called_once_with('SELECT COUNT(*) FROM visit_logs WHERE user_id = %s', (1,))

    mock_cursor.reset_mock()
    count_all = repo.get_log_count(user_id=None)
    assert count_all == 5
    mock_cursor.execute.assert_called_once_with('SELECT COUNT(*) FROM visit_logs', ())


def test_visit_log_repository_get_page_visit_stats(mock_db_connector):
    repo = VisitLogRepository(mock_db_connector)
    mock_cursor = mock_db_connector.connect.return_value.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = [
        {'path': '/page1', 'visit_count': 5},
        {'path': '/page2', 'visit_count': 3}
    ]

    stats = repo.get_page_visit_stats()

    assert len(stats) == 2
    assert stats[0]['path'] == '/page1'
    mock_cursor.execute.assert_called_once()
    actual_query = mock_cursor.execute.call_args[0][0]

    cleaned_query = ' '.join(actual_query.split()).strip()

    expected_part = 'GROUP BY path ORDER BY visit_count DESC;'
    assert expected_part in cleaned_query

def test_visit_log_repository_get_user_visit_stats(mock_db_connector):
    repo = VisitLogRepository(mock_db_connector)
    mock_cursor = mock_db_connector.connect.return_value.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = [
        {'first_name': 'John', 'last_name': 'Doe', 'middle_name': None, 'visit_count': 10},
        {'first_name': None, 'last_name': None, 'middle_name': None, 'visit_count': 7}
    ]

    stats = repo.get_user_visit_stats()

    assert len(stats) == 2
    assert stats[0]['first_name'] == 'John'
    mock_cursor.execute.assert_called_once()
    actual_query = mock_cursor.execute.call_args[0][0]

    cleaned_query = ' '.join(actual_query.split()).strip()

    expected_part = 'GROUP BY u.id, u.first_name, u.last_name, u.middle_name ORDER BY visit_count DESC;'
    assert expected_part in cleaned_query