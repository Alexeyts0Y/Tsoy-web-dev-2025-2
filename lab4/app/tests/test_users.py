import re

import pytest
from flask import g
from ..auth import User

def test_navbar_links_unathorized(client, captured_templates):
    try:
        with client.application.app_context():
            db = getattr(g, 'db', None)
            if db:
                db.ping(reconnect=True)
    except Exception as e:
        pytest.fail(f"Database connection failed: {e}")
    with captured_templates as templates:
        response = client.get('/')
        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/index.html'

        assert 'Войти' in response.text
        assert 'Выйти' not in response.text
        assert 'Изменить пароль' not in response.text

def test_navbar_links_authorized(logged_in_client, captured_templates):
    with captured_templates as templates:
        response = logged_in_client.get('/')
        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/index.html'

        assert 'Войти' not in response.text
        assert 'Выйти' in response.text
        assert 'Изменить пароль' in response.text

def test_index_unauthorized(client, captured_templates, example_users):
    with captured_templates as templates:
        response = client.get('/')

        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/index.html'

        assert 'edit' not in response.text

        pattern = re.escape('data-user-id="') + r'\d+' + re.escape('">Удалить</button>')
        assert re.search(pattern, response.text) == None
        
        assert 'Добавить пользователя' not in response.text
        # assert 'btn btn-primary' in response.text 
        # assert 'show' in response.text.lower()

def test_index_authorized(logged_in_client, captured_templates):
    with captured_templates as templates:
        response = logged_in_client.get('/')

        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/index.html'

        assert 'edit' in response.text
        
        # assert 'data-user-id="' in response.text and 'delete</button>' in response.text

        assert 'Добавить пользователя' in response.text
        assert 'show' in response.text.lower()

def test_edit_unauthorized(client, captured_templates, existing_user):
    with captured_templates as templates:
        response = client.get(f'/users/{existing_user.id}/edit', follow_redirects=True)

        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'auth/login.html'

def test_edit_authorized(captured_templates, logged_in_client, user_repository):
    with captured_templates as templates:
        response = logged_in_client.get('/users/1/edit', follow_redirects=True)
        assert response.status_code == 200
        
        user = user_repository.get_by_id(1)
        assert isinstance(user, dict)  # Проверяем тип
        
        update_data = {
            'first_name': f"{user['first_name']}_test",
            'last_name': f"{user['last_name']}_test",
            'middle_name': f"{user.get('middle_name', 'middle')}_test",
            'role_id': user['role_id']
        }
        
        response = logged_in_client.post('/users/1/edit', 
                                       data=update_data,
                                       follow_redirects=True)
        assert response.status_code == 200

def test_delete_unauthorized(client, captured_templates, existing_user):
    with captured_templates as templates:
        response = client.post(f'/users/{existing_user.id}/delete', follow_redirects=True)

        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'auth/login.html'

def test_delete_authorized(logged_in_client, captured_templates, user_repository):
    with captured_templates as templates:
        # Проверяем, что пользователь в БД существует
        assert user_repository.all() != []

        response = logged_in_client.post(f'/users/1/delete', follow_redirects=True)

        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/index.html'

        assert 'Пользователь удален!' in response.text

        # Проверяем, что пользователя после удаления в БД больше нет
        assert user_repository.all() == []

def test_view(client, captured_templates, existing_user, existing_role):
    with captured_templates as templates:
        response = client.get(f'/users/{existing_user.id}', follow_redirects=True)

        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/show.html'

        assert str(existing_user.id) in response.text
        assert existing_user.username in response.text
        assert existing_user.first_name in response.text
        assert existing_user.last_name in response.text
        assert existing_role.name in response.text

def test_view_unexisted_user(client, captured_templates, existing_user, existing_role):
    with captured_templates as templates:
        response = client.get(f'/users/{existing_user.id + 1}', follow_redirects=True)

        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/index.html'

        assert 'Пользователя нет в БД!' in response.text

def test_create_unauthorized(client, captured_templates):
    with captured_templates as templates:
        response = client.get('/users/new', follow_redirects=True)
        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'auth/login.html'

def test_create_authorized(logged_in_client, captured_templates, user_repository):
    with captured_templates as templates:
        response = logged_in_client.get('/users/new', follow_redirects=True)
        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/new.html'

        # Сохранение информации о пользователях до создания нового пользователя
        users = user_repository.all()
        
        new_user_data = {}
        new_user_data['username'] = 'test1'
        new_user_data['password'] = 'Test_password1'
        new_user_data['first_name'] = 'test_first_name'
        new_user_data['middle_name'] = 'test_middle_name'
        new_user_data['last_name'] = 'test_last_name'
        new_user_data['role_id'] = '1'
        response = logged_in_client.post('/users/new', follow_redirects=True, data=new_user_data)

        assert response.status_code == 200

        assert len(templates) == 2
        template = templates[1][0]
        assert template.name == 'users/index.html'  
        
        # Новый пользователь появился на основной странице
        assert new_user_data['username'] in response.text

        # Сохранение информации о пользователях после создания нового пользователя
        new_users = user_repository.all()

        assert len(new_users) == len(users) + 1

        # assert new_user_data['id'] + 1 == new_users[1].id
        assert new_user_data['username'] == new_users[1]['username']
        assert new_user_data['first_name'] == new_users[1]['first_name']
        assert new_user_data['middle_name'] == new_users[1]['middle_name']
        assert new_user_data['last_name'] == new_users[1]['last_name']
        assert int(new_user_data['role_id']) == new_users[1]['role_id']

        # Удаляем нового пользователя
        user_repository.delete(new_users[1]['id'])

def test_change_password_unauthorized(client, captured_templates):
    with captured_templates as templates:
        response = client.get('/users/1/edit_password', follow_redirects=True)
        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'auth/login.html'

def test_change_password_authorized(captured_templates, user_repository, app, existing_user):
    with captured_templates as templates:
        with app.app_context():
            user=User(existing_user.id, existing_user.username)
            with app.test_client(user=user) as logged_in_client:
                response = logged_in_client.get(f'/users/{existing_user.id}/edit_password', follow_redirects=True)
                assert response.status_code == 200

                assert len(templates) == 1
                template = templates[0][0]
                assert template.name == 'users/edit_password.html'

                user_before_change = user_repository.get_by_id(existing_user.id)

                change_password_form = {}
                change_password_form['password'] = 'Qwerty'
                change_password_form['new_password'] = 'Test12345'
                change_password_form['repeat_new_password'] = 'Test12345'
                response = logged_in_client.post(f'/users/{existing_user.id}/edit_password', follow_redirects=True, data=change_password_form)
                assert response.status_code == 200

                assert len(templates) == 2
                template = templates[1][0]
                assert template.name == 'users/edit_password.html'

                assert not user_repository.check_password(existing_user.id, 'Qwerty')

