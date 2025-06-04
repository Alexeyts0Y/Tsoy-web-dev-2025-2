import pytest
from flask import url_for, current_app
from unittest.mock import ANY, call
import csv
from io import StringIO
from datetime import datetime
from conftest import admin_user_data, regular_user_data

def test_log_request_info_authenticated_user(client, login_as, mock_admin_user, mock_visit_log_repo):
    login_as(mock_admin_user)
    test_path = url_for('users.index')
    client.get(test_path)
    mock_visit_log_repo.create.assert_called_with(test_path, mock_admin_user.id)

def test_log_request_info_unauthenticated_user(client, mock_visit_log_repo, app, login_as):

    login_as(None)

    test_path = url_for('auth.login')
    client.get(test_path)

    mock_visit_log_repo.create.assert_called_with(test_path, None)

def test_log_request_info_skips_static_and_favicon(client, mock_visit_log_repo):

    mock_visit_log_repo.reset_mock()
    client.get('/favicon.ico')
    mock_visit_log_repo.create.assert_not_called()

    mock_visit_log_repo.reset_mock()
    client.get(url_for('auth.logout'))
    mock_visit_log_repo.create.assert_not_called()

def test_visit_logs_index_admin_sees_all(client, login_as, mock_admin_user, mock_visit_log_repo):
    login_as(mock_admin_user)
    mock_logs = [
        {'id': 1, 'path': '/p1', 'created_at': datetime(2023,1,1,10,0), 'first_name': 'A', 'last_name': 'D', 'middle_name': 'M'},
        {'id': 2, 'path': '/p2', 'created_at': datetime(2023,1,1,11,0), 'first_name': 'R', 'last_name': 'U', 'middle_name': None}
    ]
    mock_visit_log_repo.get_log_count.return_value = 2
    mock_visit_log_repo.get_all_logs.return_value = mock_logs
    
    response = client.get(url_for('visit_logs.index'))
    assert response.status_code == 200
    assert "Журнал посещений" in response.data.decode('utf-8')
    assert "D A M" in response.data.decode('utf-8')
    assert "U R" in response.data.decode('utf-8')
    assert "/p1" in response.data.decode('utf-8')
    mock_visit_log_repo.get_log_count.assert_called_once_with(user_id=None)
    mock_visit_log_repo.get_all_logs.assert_called_once_with(limit=10, offset=0, user_id=None)

def test_visit_logs_index_user_sees_own(client, login_as, mock_regular_user, mock_visit_log_repo):
    login_as(mock_regular_user)
    user_log = {'id': 1, 'path': '/my_page', 'created_at': datetime(2023,1,1,10,0), 
                'first_name': mock_regular_user.username, 'last_name': 'Surname', 'middle_name': None}
    
    mock_visit_log_repo.get_log_count.return_value = 1
    mock_visit_log_repo.get_all_logs.return_value = [user_log]
    
    response = client.get(url_for('visit_logs.index'))
    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert "Журнал посещений" in response_text

    expected_user_string = "Surname " + mock_regular_user.username
    assert expected_user_string in response_text
    assert "/my_page" in response_text

    assert "Отчет по страницам" in response.data.decode('utf-8')
    assert "Отчет по пользователям" in response.data.decode('utf-8')

    mock_visit_log_repo.get_log_count.assert_called_once_with(user_id=mock_regular_user.id)
    mock_visit_log_repo.get_all_logs.assert_called_once_with(limit=10, offset=0, user_id=mock_regular_user.id)

def test_visit_logs_index_pagination(client, login_as, mock_admin_user, mock_visit_log_repo):
    login_as(mock_admin_user)
    mock_visit_log_repo.get_log_count.return_value = 15
    mock_visit_log_repo.get_all_logs.return_value = []

    client.get(url_for('visit_logs.index', page=2))
    mock_visit_log_repo.get_all_logs.assert_called_once_with(limit=10, offset=10, user_id=None)

def test_visit_logs_pages_report_get_admin(client, login_as, mock_admin_user, mock_visit_log_repo):
    login_as(mock_admin_user)
    stats = [{'path': '/home', 'visit_count': 100}, {'path': '/profile', 'visit_count': 50}]
    mock_visit_log_repo.get_page_visit_stats.return_value = stats
    
    response = client.get(url_for('visit_logs.pages_report'))
    assert response.status_code == 200
    assert "Отчет по посещениям страниц" in response.data.decode('utf-8')
    assert "/home" in response.data.decode('utf-8')
    assert "100" in response.data.decode('utf-8')
    assert "Экспорт в CSV" in response.data.decode('utf-8')
    mock_visit_log_repo.get_page_visit_stats.assert_called_once()

def test_visit_logs_pages_report_get_user_denied(client, login_as, mock_regular_user):
    login_as(mock_regular_user)
    response = client.get(url_for('visit_logs.pages_report'))
    assert response.status_code == 302
    assert response.location == url_for('index', _external=False)

def test_visit_logs_pages_report_export_csv_admin(client, login_as, mock_admin_user, mock_visit_log_repo):
    login_as(mock_admin_user)
    stats = [{'path': '/home', 'visit_count': 100}, {'path': '/profile', 'visit_count': 50}]
    mock_visit_log_repo.get_page_visit_stats.return_value = stats

    response = client.get(url_for('visit_logs.pages_report_export_csv'))
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert response.headers['Content-Disposition'].startswith("attachment; filename=pages_report.csv")
    
    csv_data = response.data.decode('utf-8')
    reader = csv.reader(StringIO(csv_data))
    rows = list(reader)
    assert rows[0] == ['№', 'Страница', 'Количество посещений']
    mock_visit_log_repo.get_page_visit_stats.assert_called_once()

def test_visit_logs_users_report_get_admin(client, login_as, mock_admin_user, mock_visit_log_repo):
    login_as(mock_admin_user)
    stats = [
        {'first_name': 'Admin', 'last_name': 'User', 'middle_name': None, 'visit_count': 200},
        {'first_name': None, 'last_name': None, 'middle_name': None, 'visit_count': 10}
    ]
    mock_visit_log_repo.get_user_visit_stats.return_value = stats
    
    response = client.get(url_for('visit_logs.users_report'))
    assert response.status_code == 200
    assert "Отчет по посещениям пользователей" in response.data.decode('utf-8')
    assert "User Admin" in response.data.decode('utf-8')
    assert "Неаутентифицированный пользователь" in response.data.decode('utf-8')
    assert "200" in response.data.decode('utf-8')
    mock_visit_log_repo.get_user_visit_stats.assert_called_once()

def test_visit_logs_users_report_export_csv_admin(client, login_as, mock_admin_user, mock_visit_log_repo):
    login_as(mock_admin_user)
    stats = [
        {'first_name': 'Admin', 'last_name': 'User', 'middle_name': 'The', 'visit_count': 200},
        {'first_name': None, 'last_name': None, 'middle_name': None, 'visit_count': 10}
    ]
    mock_visit_log_repo.get_user_visit_stats.return_value = stats

    response = client.get(url_for('visit_logs.users_report_export_csv'))
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert response.headers['Content-Disposition'].startswith("attachment; filename=users_report.csv")

    csv_data = response.data.decode('utf-8')
    reader = csv.reader(StringIO(csv_data))
    rows = list(reader)
    assert rows[0] == ['№', 'Пользователь', 'Количество посещений']
    mock_visit_log_repo.get_user_visit_stats.assert_called_once()

    # Пагинация, хостинг