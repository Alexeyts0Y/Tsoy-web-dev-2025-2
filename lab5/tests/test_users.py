from ..app.auth import User
from ..app.db import dbConnector as db 

def test_change_password(test_client):
    test_client.post('/login', data={
        'login': 'admin',
        'password': 'adminpass'
    }, follow_redirects=True)

    response = test_client.post('/change-password', data={
        'old_password': 'adminpass',
        'new_password': 'NewPass123!',
        'confirm_password': 'NewPass123!'
    }, follow_redirects=True)

    assert 'Пароль успешно изменен'.encode('utf-8') in response.data
    
    with test_client.application.app_context():
        user = db.session.get(User, 1)
        assert user.check_password('NewPass123!') is True