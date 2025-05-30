from flask import url_for
from models.models import db, User, VisitLog, Role
import pytest

def test_visit_logging(test_client):
    test_client.post('/login', data={'login': 'admin', 'password': 'adminpass'})
    test_client.get('/')
    with test_client.application.app_context():
        log = VisitLog.query.filter_by(path='/').first()
        assert log is not None
        assert log.user_id == 1

def test_visit_log_export(test_client):
    test_client.post('/login', data={
        'login': 'admin',
        'password': 'adminpass'
    })
    
    response = test_client.get('/visit-log/by-page/export')
    assert response.status_code == 200
    assert 'text/csv' in response.headers['Content-Type']
    assert 'visits_by_page.csv' in response.headers['Content-Disposition']

def test_pagination_links(test_client):
    with test_client.application.app_context():
        VisitLog.query.delete()
        for i in range(25):
            log = VisitLog(path=f'/page/{i}', user_id=1)
            db.session.add(log)
        db.session.commit()

    test_client.post('/login', data={'login': 'admin', 'password': 'adminpass'})
    
    response = test_client.get(url_for('visit_log.index', page=1))
    html = response.data.decode('utf-8')
    assert 'page=2' in html  # cсылка на следующую страницу
    assert '25' in html      
    
    response = test_client.get(url_for('visit_log.index', page=2))
    html = response.data.decode('utf-8')
    assert 'page=1' in html  # cсылка на предыдущую страницу

def test_pagination_page_numbers(test_client):
    with test_client.application.app_context():
        VisitLog.query.delete()
        for i in range(15):
            log = VisitLog(path=f'/test-page/{i}', user_id=1)
            db.session.add(log)
        db.session.commit()

    
    test_client.post('/login', data={'login': 'admin', 'password': 'adminpass'})
    
    response = test_client.get(url_for('visit_log.index', page=1))
    html = response.data.decode('utf-8')

    assert 'class="page-item active"' in html, "Активная страница не выделена"
    assert '?page=1' in html, "Некорректная ссылка на текущую страницу"


def test_pagination_items_per_page(test_client):
    with test_client.application.app_context():
        VisitLog.query.delete()
        for i in range(15):
            log = VisitLog(path=f'/test-page/{i}', user_id=1)
            db.session.add(log)
        db.session.commit()

    # как админ
    test_client.post('/login', data={'login': 'admin', 'password': 'adminpass'})
    
    # запрос первой страницы
    response = test_client.get(url_for('visit_log.index', page=1))
    html = response.data.decode('utf-8')
    
    total_rows = html.count('<tr>') - 1

    assert total_rows == 17, f"Ожидалось 17 записей, получено {total_rows}"

def test_statistics_count(test_client):
    with test_client.application.app_context():
        VisitLog.query.delete()
        paths = ['/', '/about', '/', '/contact', '/']
        for path in paths:
            log = VisitLog(path=path, user_id=1)
            db.session.add(log)
        db.session.commit()
    
    test_client.post('/login', data={'login': 'admin', 'password': 'adminpass'})
    
    response = test_client.get(url_for('visit_log.by_page'))
    html = response.data.decode('utf-8')
    assert '3</td>' in html  
    assert '1</td>' in html  

def test_user_permission_checks(test_client):
    with test_client.application.app_context():
        user_role = Role.query.filter_by(name='Пользователь').first()
        user = User(
            login='user',
            first_name='Test',  
            role_id=user_role.id
        )
        user.set_password('pass')
        db.session.add(user)
        db.session.commit()

    # вход обычного пользователя
    test_client.post('/login', data={'login': 'user', 'password': 'pass'})
    
    # доступ к общему журналу
    response = test_client.get(url_for('visit_log.index'))
    assert response.status_code == 302
    