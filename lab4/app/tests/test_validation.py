from ..utils.validator import validate_password, validate_name, validate_username
import pytest
from .conftest import test_data
from ..auth import User

def validate_user_data(input_data):
    """Helper function to validate all user data using separate validators"""
    errors = {}
    
    username_error = validate_username(input_data['username'])
    if username_error:
        errors['username'] = username_error
        
    password_error = validate_password(input_data['password'])
    if password_error:
        errors['password'] = password_error
        
    first_name_error = validate_name(input_data['first_name'], 'first_name')
    if first_name_error:
        errors['first_name'] = first_name_error
        
    last_name_error = validate_name(input_data['last_name'], 'last_name')
    if last_name_error:
        errors['last_name'] = last_name_error
        
    return errors

@pytest.mark.parametrize('input_data, expected', test_data())
def test_validate_user_data(input_data, expected):
    result = validate_user_data(input_data)
    
    if expected == {}:
        assert result == {}
    else:
        for field, expected_errors in expected.items():
            assert field in result

            actual_errors = result[field] if isinstance(result[field], list) else [result[field]]
            
            expected_errors_list = expected_errors if isinstance(expected_errors, list) else [expected_errors]
            
            for expected_error in expected_errors_list:
                expected_str = str(expected_error).strip()
                assert any(expected_str in str(actual).strip() for actual in actual_errors), \
                    f"Expected error '{expected_str}' not found in actual errors: {actual_errors}"

@pytest.mark.parametrize('input_data, expected', test_data())
def test_validate_create(logged_in_client, captured_templates, input_data, expected, user_repository):
    with captured_templates as templates:
        new_user_data = {}
        new_user_data['username'] = input_data['username']
        new_user_data['password'] = input_data['password']
        new_user_data['first_name'] = input_data['first_name']
        new_user_data['last_name'] = input_data['last_name']
        new_user_data['middle_name'] = ''
        new_user_data['role_id'] = 1

        response = logged_in_client.post('/users/new', follow_redirects=True, data=new_user_data)
        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        if expected == {}:
            assert template.name == 'users/index.html'
            
            assert 'Пользователь создан!' in response.text

            assert new_user_data['username'] in response.text

            user_repository.delete(
                user_repository.get_by_username_and_password(new_user_data['username'], 
                                                             new_user_data['password'])['id'])
        else:
            assert template.name == 'users/new.html'

            for key in expected.keys():
                assert expected[key] in response.text

def test_validate_create_not_unique_username(app, existing_user, captured_templates):
    with captured_templates as templates:
        with app.app_context():
            user=User(existing_user.id, existing_user.username)
            with app.test_client(user=user) as logged_in_client:
                new_user_data = {}
                new_user_data['username'] = existing_user.username
                new_user_data['password'] = 'Qwerty123'
                new_user_data['first_name'] = existing_user.first_name
                new_user_data['last_name'] = existing_user.last_name
                new_user_data['role_id'] = existing_user.role_id

                response = logged_in_client.post('/users/new', follow_redirects=True, data=new_user_data)
                assert response.status_code == 200

                assert len(templates) == 1
                template = templates[0][0]
                
                assert template.name == 'users/new.html'
                    
                assert 'Произошла ошибка при создании пользователя. Проверьте, что все необходимые поля заполнены' in response.text


@pytest.mark.parametrize('input_data, expected', test_data())
def test_validate_change_password_new_password(app, existing_user, captured_templates, input_data, expected, user_repository):
    with captured_templates as templates:
        with app.app_context():
            user=User(existing_user.id, existing_user.username)
            with app.test_client(user=user) as logged_in_client:
                update_password = {}
                update_password['old_password'] = existing_user.password
                update_password['new_password'] = input_data['password']
                update_password['confirm_new_password'] = input_data['password']

                user_before_change = user_repository.get_by_id(existing_user.id)
                
                response = logged_in_client.post(f'/users/{existing_user.id}/edit_password', follow_redirects=True, data=update_password)
                assert response.status_code == 200

                assert len(templates) == 1
                template = templates[0][0]

                if 'password' not in expected:
                    assert template.name == 'users/index.html'

                    assert 'Пароль изменен!' in response.text
                    
                    user_after_change = user_repository.get_by_id(existing_user.id)
                    assert user_before_change.password_hash != user_after_change.password_hash
                else:
                    assert template.name == 'users/edit_password.html'

                    assert expected['password'] in response.text                   

def test_change_passwords_oldpass_incorrect(app, existing_user, captured_templates):
    with captured_templates as templates:
        with app.app_context():
            user=User(existing_user.id, existing_user.username)
            with app.test_client(user=user) as logged_in_client:
                update_password = {}
                update_password['old_password'] = f"{existing_user.password}+"
                update_password['new_password'] = 'Qwerty1asdf'
                update_password['confirm_new_password'] = 'Qwerty1asdf'
                
                response = logged_in_client.post(f'/users/{existing_user.id}/edit_password', follow_redirects=True, data=update_password)
                assert response.status_code == 200

                assert len(templates) == 1
                template = templates[0][0]

                assert template.name == 'users/edit_password.html'
                # assert 'Неверный текущий пароль' in response.text.lower()

def test_change_passwords_newpass_not_confirmed(app, existing_user, captured_templates):
    with captured_templates as templates:
        with app.app_context():
            user=User(existing_user.id, existing_user.username)
            with app.test_client(user=user) as logged_in_client:
                update_password = {}
                update_password['old_password'] = f"{existing_user.password}+"
                update_password['new_password'] = 'Qwerty1'
                update_password['confirm_new_password'] = '1'
                
                response = logged_in_client.post(f'/users/{existing_user.id}/edit_password', follow_redirects=True, data=update_password)
                assert response.status_code == 200

                assert len(templates) == 1
                template = templates[0][0]

                assert template.name == 'users/edit_password.html'
                assert 'Пароли не совпадают' in response.text 

def test_validate_edit_fail(logged_in_client, captured_templates):
    with captured_templates as templates:
        edit_user_info = {}
        edit_user_info['first_name'] = ''
        edit_user_info['second_name'] = ''
        edit_user_info['middle_name'] = 'Middle-name'
        edit_user_info['role_id'] = 1

        response = logged_in_client.post('/users/1/edit', follow_redirects=True, data=edit_user_info)
        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/edit.html'

        assert 'Поле не может быть пустым' in response.text

def test_validate_edit_success(logged_in_client, captured_templates):
    with captured_templates as templates:
        edit_user_info = {}
        edit_user_info['first_name'] = 'Alexey'
        edit_user_info['last_name'] = 'Tsoy'
        edit_user_info['middle_name'] = 'Middle-name'
        edit_user_info['role_id'] = 1

        response = logged_in_client.post('/users/1/edit', follow_redirects=True, data=edit_user_info)
        assert response.status_code == 200

        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/index.html'

        assert 'Пользователь изменен!' in response.text
