import pytest
from flask import url_for, template_rendered, request
from bs4 import BeautifulSoup
from app.app import app as flask_app
from contextlib import contextmanager

@pytest.fixture
def app():
    flask_app.config['TESTING'] = True
    return flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)

def test_url_page_renders_correct_template(client, app):
    with captured_templates(app) as templates:
        response = client.get(url_for('url'))
        assert response.status_code == 200
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'url.html'

def test_url_page_displays_single_parameter(client):
    test_param = {'name': 'John'}
    response = client.get(url_for('url', **test_param))
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    parameter_items = [p for p in soup.find_all('p') if "Ключ:" in p.text]
    
    assert len(parameter_items) == 1
    assert f"Ключ: name, значение: {test_param['name']}" in parameter_items[0].text

def test_url_page_displays_multiple_parameters(client):
    test_params = {'name': 'John', 'age': '30', 'city': 'Moscow'}
    response = client.get(url_for('url', **test_params))
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    parameter_items = [p for p in soup.find_all('p') if "Ключ:" in p.text]
    
    assert len(parameter_items) == len(test_params)
    for key, value in test_params.items():
        found = any(f"Ключ: {key}, значение: {value}" in p.text for p in parameter_items)
        assert found, f"Параметр {key}={value} не найден на странице"

def test_headers_page_renders_correct_template(client, app):
    with captured_templates(app) as templates:
        response = client.get(url_for('headers'))
        assert response.status_code == 200
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'headers.html'

def test_headers_page_displays_request_headers(client):
    response = client.get(url_for('headers'))
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    header_items = soup.select('.row.mb-3 p')

    required_headers = ['Host', 'User-Agent']
    found_headers = [p.text for p in header_items]
    
    for header in required_headers:
        assert any(header in h for h in found_headers), f"Заголовок {header} не найден"

def test_headers_page_displays_custom_headers(client):
    custom_headers = {
        'X-Custom-Header': 'TestValue',
        'X-Another-Header': 'AnotherValue'
    }
    
    response = client.get(url_for('headers'), headers=custom_headers)
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    header_items = soup.select('.row.mb-3 p')
    
    for name, value in custom_headers.items():
        expected_text = f"Название: {name}, значение: {value}"
        assert any(expected_text in p.text for p in header_items), f"Заголовок {name} не найден"

def test_cookie_page_template(client, app):
    with captured_templates(app) as templates:
        response = client.get(url_for('cookies'))
        assert response.status_code == 200
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'cookies.html'

def test_cookie_set_and_display(client):
    response = client.get(url_for('cookies'))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')
    assert "Куки не установлен" in soup.find('div', class_='row').text

    test_value = "test_value"
    response = client.get(url_for('cookies', cookie=test_value))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')
    assert f"Название: my_cookie, значение: {test_value}" in soup.find('div', class_='row').text

    set_cookie_header = response.headers.get('Set-Cookie', '')
    assert 'my_cookie' in set_cookie_header
    assert test_value in set_cookie_header

def test_cookie_delete(client):
    test_value = "test_value"
    client.get(url_for('cookies', cookie=test_value))

    response = client.get(url_for('cookies'))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')
    assert "Куки не установлен" in soup.find('div', class_='row').text

    set_cookie_header = response.headers.get('Set-Cookie', '')
    assert 'my_cookie=' in set_cookie_header
    assert 'expires=0' in set_cookie_header.lower() or 'max-age=0' in set_cookie_header.lower()

def test_form_page_renders_correct_template(client, app):
    with captured_templates(app) as templates:
        response = client.get(url_for('form'))
        assert response.status_code == 200
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'form.html'

def test_form_displays_empty_state(client):
    response = client.get(url_for('form'))
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    form = soup.find('form')
    assert form is not None
    
    # Проверяем наличие всех полей формы
    assert soup.find('input', {'name': 'first'}) is not None
    assert soup.find('input', {'name': 'second'}) is not None
    assert soup.find('input', {'name': 'third'}) is not None
    assert soup.find('button', {'type': 'submit'}) is not None

def test_form_submission_displays_parameters(client):
    test_data = {
        'first': 'test_value_1',
        'second': 'test_value_2', 
        'third': 'test_value_3'
    }

    response = client.post(url_for('form'), data=test_data)
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')

    rows = soup.find_all('div', class_='row')
    assert len(rows) >= 2, "Не найдены все div с классом row"
    params_container = rows[1]

    paragraphs_text = [p.text for p in params_container.find_all('p')]
    print("\nFound paragraphs:", paragraphs_text)
    
    for name, value in test_data.items():
        param_text = f"Название: {name}, значение: {value}"
        assert param_text in paragraphs_text, f"Не найден параметр: {param_text}"

def test_phone_validation_success(client):
    test_cases = [
        ('+7 (123) 456-75-90', '8-123-456-75-90'),
        ('8(123)4567590', '8-123-456-75-90'),
        ('123.456.75.90', '8-123-456-75-90'),
        ('+71234567890', '8-123-456-78-90'),
        ('81234567890', '8-123-456-78-90'),
        ('1234567890', '8-123-456-78-90')
    ]
    
    for input_phone, expected in test_cases:
        response = client.post(url_for('phone'), data={'phone': input_phone})
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        success_alert = soup.find('div', class_='alert-success')
        assert success_alert is not None
        assert f"Форматированный номер: {expected}" in success_alert.text

def test_phone_validation_errors(client):
    test_cases = [
        ('+7 (123) 456-75', 'Недопустимый ввод. Неверное количество цифр.'),
        ('8(123)456', 'Недопустимый ввод. Неверное количество цифр.'),
        ('123.45.75.90', 'Недопустимый ввод. Неверное количество цифр.'),
        ('+7abc4567890', 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.'),
        ('8!234567890', 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.')
    ]
    
    for input_phone, expected_error in test_cases:
        response = client.post(url_for('phone'), data={'phone': input_phone})
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')

        input_field = soup.find('input', id='phone')
        assert 'is-invalid' in input_field['class']

        error_div = soup.find('div', class_='invalid-feedback')
        assert error_div is not None
        assert expected_error in error_div.text

        assert soup.find('div', class_='alert-success') is None

def test_phone_page_structure(client):
    response = client.get(url_for('phone'))
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')

    form = soup.find('form')
    assert form is not None
    assert form.get('method') == 'POST'
    assert form.get('action') == url_for('phone')

    input_field = soup.find('input', id='phone')
    assert input_field is not None
    assert input_field['name'] == 'phone'

    assert soup.find('button', type='submit') is not None