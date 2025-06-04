import pytest
from flask import url_for
from unittest.mock import patch, ANY
from conftest import admin_user_data, regular_user_data, another_user_data

def test_users_index_admin(client, login_as, mock_admin_user, mock_user_repo):
    login_as(mock_admin_user)
    mock_user_repo.all.return_value = [admin_user_data, regular_user_data]
    
    response = client.get(url_for('users.index'))
    assert response.status_code == 200
    assert f"Управление пользователями" in response.data.decode('utf-8')
    assert f"Добавить пользователя" in response.data.decode('utf-8')
    assert admin_user_data['username'] in response.data.decode('utf-8')
    assert regular_user_data['username'] in response.data.decode('utf-8')
    mock_user_repo.all.assert_called_once()

def test_users_index_user(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    mock_user_repo.all.return_value = [admin_user_data, regular_user_data]

    response = client.get(url_for('users.index'))
    assert response.status_code == 200
    assert f"Управление пользователями" not in response.data.decode('utf-8')
    assert f"Добавить пользователя" not in response.data.decode('utf-8')
    assert admin_user_data['username'] in response.data.decode('utf-8')
    assert regular_user_data['username'] in response.data.decode('utf-8')
    mock_user_repo.all.assert_called_once()

def test_users_show_admin_views_other(client, login_as, mock_admin_user, mock_user_repo):
    login_as(mock_admin_user)
    mock_user_repo.get_by_id.return_value = regular_user_data
    
    response = client.get(url_for('users.show', user_id=regular_user_data['id']))
    assert response.status_code == 302
    assert regular_user_data['username'] not in response.data.decode('utf-8')
    mock_user_repo.get_by_id.assert_called_once_with(regular_user_data['id'])

def test_users_show_user_views_self(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    mock_user_repo.get_by_id.return_value = regular_user_data
    
    response = client.get(url_for('users.show', user_id=regular_user_data['id']))
    assert response.status_code == 200
    assert regular_user_data['username'] in response.data.decode('utf-8')
    mock_user_repo.get_by_id.assert_called_once_with(regular_user_data['id'])

def test_users_show_user_views_other_denied(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    
    response = client.get(url_for('users.show', user_id=admin_user_data['id']))
    assert response.status_code == 302
    assert response.location == url_for('index', _external=False)
    resp_redirected = client.get(response.location)
    assert f"У вас недостаточно прав" in resp_redirected.data.decode('utf-8')

def test_users_show_non_existent(client, login_as, mock_admin_user, mock_user_repo):
    login_as(mock_admin_user)
    mock_user_repo.get_by_id.return_value = None
    
    response = client.get(url_for('users.show', user_id=999))
    assert response.status_code == 302
    assert response.location == url_for('users.index', _external=False)
    resp_redirected = client.get(response.location)
    assert f"Пользователя нет в БД!" in resp_redirected.data.decode('utf-8')

def test_users_new_get_admin(client, login_as, mock_admin_user, mock_role_repo):
    login_as(mock_admin_user)
    response = client.get(url_for('users.new'))
    assert response.status_code == 200
    assert f"Добавление пользователя" in response.data.decode('utf-8')
    mock_role_repo.all.assert_called_once()

def test_users_new_post_admin_success(client, login_as, mock_admin_user, mock_user_repo, mock_role_repo):
    login_as(mock_admin_user)
    new_user_form_data = {
        'username': 'newbie', 'password': 'Password123!',
        'first_name': 'New', 'last_name': 'User', 'middle_name': 'Bee', 'role_id': '2'
    }
    mock_user_repo.create.return_value = None

    response = client.post(url_for('users.new'), data=new_user_form_data, follow_redirects=False)
    assert response.status_code == 302
    assert response.location == url_for('users.index', _external=False)
    mock_user_repo.create.assert_called_once_with(
        username='newbie', password='Password123!', first_name='New', 
        middle_name='Bee', last_name='User', role_id='2'
    )
    resp_redirected = client.get(response.location)
    assert f"Пользователь создан!" in resp_redirected.data.decode('utf-8')

def test_users_new_post_admin_validation_error(client, login_as, mock_admin_user, mock_role_repo):
    login_as(mock_admin_user)
    invalid_data = {'username': '', 'password': 'short', 'first_name': '123', 'last_name': ''}
    
    response = client.post(url_for('users.new'), data=invalid_data)
    assert response.status_code == 200
    assert f"Добавление пользователя" in response.data.decode('utf-8')
    mock_role_repo.all.assert_called()

def test_users_new_user_denied(client, login_as, mock_regular_user):
    login_as(mock_regular_user)
    response = client.get(url_for('users.new'))
    assert response.status_code == 302
    assert response.location == url_for('index', _external=False)

def test_users_delete_admin_deletes_other(client, login_as, mock_admin_user, mock_user_repo):
    login_as(mock_admin_user)
    target_user_id = regular_user_data['id']
    
    response = client.post(url_for('users.delete', user_id=target_user_id), follow_redirects=False)
    assert response.status_code == 302
    assert response.location == url_for('users.index', _external=False)
    mock_user_repo.delete.assert_called_once_with(target_user_id)
    resp_redirected = client.get(response.location)
    assert f"Пользователь удален!" in resp_redirected.data.decode('utf-8')

def test_users_delete_admin_deletes_self_denied(client, login_as, mock_admin_user, mock_user_repo):
    login_as(mock_admin_user)
    
    response = client.post(url_for('users.delete', user_id=mock_admin_user.id), follow_redirects=True)
    assert response.status_code == 200
    assert f"Вы не можете удалить свой собственный аккаунт" in response.data.decode('utf-8')
    mock_user_repo.delete.assert_not_called()

def test_users_delete_user_denied(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    response = client.post(url_for('users.delete', user_id=admin_user_data['id']))
    assert response.status_code == 302
    assert response.location == url_for('index', _external=False)
    mock_user_repo.delete.assert_not_called()

def test_users_edit_post_user_updates_self_role_not_changed(client, login_as, mock_regular_user, mock_user_repo, mock_role_repo):
    login_as(mock_regular_user)
    mock_user_repo.get_by_id.return_value = {**regular_user_data, 'id': mock_regular_user.id, 'role_id': mock_regular_user.role_id}
    
    form_data = {
        'first_name': 'SelfUpdatedFirst', 'last_name': 'SelfUpdatedLast',
        'middle_name': '', 'role_id': '1'
    }
    response = client.post(url_for('users.edit', user_id=mock_regular_user.id), data=form_data, follow_redirects=False)
    assert response.status_code == 302
    assert response.location == url_for('users.index', _external=False)

    mock_user_repo.update.assert_called_once_with(
        user_id=mock_regular_user.id, first_name='SelfUpdatedFirst', middle_name=None,
        last_name='SelfUpdatedLast', role_id=mock_regular_user.role_id
    )

def test_users_edit_user_edits_other_denied(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    response = client.get(url_for('users.edit', user_id=admin_user_data['id']))
    assert response.status_code == 302
    assert response.location == url_for('index', _external=False)

def test_users_edit_password_get(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    mock_user_repo.get_by_id.return_value = regular_user_data
    response = client.get(url_for('users.edit_password', user_id=mock_regular_user.id))
    assert response.status_code == 200
    assert f"Изменить пароль" in response.data.decode('utf-8')
    assert f"Старый Пароль" in response.data.decode('utf-8')
    mock_user_repo.get_by_id.assert_called_once_with(mock_regular_user.id)

def test_users_edit_password_post_success(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    mock_user_repo.get_by_id.return_value = regular_user_data
    mock_user_repo.check_password.return_value = True
    
    form_data = {
        'old_password': 'oldPassword123',
        'new_password': 'NewPassword123!',
        'repeat_new_password': 'NewPassword123!'
    }
    response = client.post(url_for('users.edit_password', user_id=mock_regular_user.id), data=form_data, follow_redirects=False)
    assert response.status_code == 302
    assert response.location == url_for('users.index', _external=False)
    mock_user_repo.check_password.assert_called_once_with(mock_regular_user.id, 'oldPassword123')
    mock_user_repo.update_password.assert_called_once_with(mock_regular_user.id, 'NewPassword123!')
    resp_redirected = client.get(response.location)
    assert f"Пароль изменен!" in resp_redirected.data.decode('utf-8')

def test_users_edit_password_post_wrong_old_password(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    mock_user_repo.get_by_id.return_value = regular_user_data
    mock_user_repo.check_password.return_value = False
    
    form_data = {'old_password': 'wrongOld', 'new_password': 'NewPass123!', 'repeat_new_password': 'NewPass123!'}
    response = client.post(url_for('users.edit_password', user_id=mock_regular_user.id), data=form_data)
    assert response.status_code == 200
    assert f"Неверный текущий пароль" in response.data.decode('utf-8')
    mock_user_repo.update_password.assert_not_called()

def test_users_edit_password_post_mismatch_new_password(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    mock_user_repo.get_by_id.return_value = regular_user_data
    
    form_data = {'old_password': 'oldPass', 'new_password': 'NewPass123!', 'repeat_new_password': 'DifferentPass123!'}
    response = client.post(url_for('users.edit_password', user_id=mock_regular_user.id), data=form_data)
    assert response.status_code == 200
    assert f"Пароли не совпадают" in response.data.decode('utf-8')
    mock_user_repo.update_password.assert_not_called()

def test_users_edit_password_post_invalid_new_password(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    mock_user_repo.get_by_id.return_value = regular_user_data
    
    form_data = {'old_password': 'oldPass', 'new_password': 'short', 'repeat_new_password': 'short'}
    response = client.post(url_for('users.edit_password', user_id=mock_regular_user.id), data=form_data)
    assert response.status_code == 200
    mock_user_repo.update_password.assert_not_called()

def test_users_edit_password_user_edits_other_denied(client, login_as, mock_regular_user, mock_user_repo):
    login_as(mock_regular_user)
    mock_user_repo.get_by_id.return_value = admin_user_data
    response = client.get(url_for('users.edit_password', user_id=admin_user_data['id']))
    assert response.status_code == 302
    assert response.location == url_for('index', _external=False)