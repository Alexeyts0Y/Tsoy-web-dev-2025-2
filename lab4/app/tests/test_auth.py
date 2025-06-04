def test_successful_login(client, captured_templates, existing_user):
    with captured_templates as templates:
        login_data = {}
        login_data['username'] = existing_user.username
        login_data['password'] = existing_user.password
        response = client.post('/auth/login', follow_redirects=True, data=login_data)

        assert response.status_code == 200 
        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'users/index.html'
        
        assert 'Вход выполнен успешно!' in response.text

def test_unsuccessful_login(client, captured_templates, nonexisting_user):
    with captured_templates as templates:
        login_data = {}
        login_data['username'] = nonexisting_user.username
        login_data['password'] = nonexisting_user.password
        response = client.post('/auth/login', follow_redirects=True, data=login_data)

        assert response.status_code == 200 
        assert len(templates) == 1
        template = templates[0][0]
        assert template.name == 'auth/login.html'
        
        assert 'Неверное имя пользователя или пароль' in response.text