from flask import Flask, render_template, request, make_response

import re

app = Flask(__name__)
application = app


@app.route('/')
@app.route('/headers')
def headers():
    h = request.headers.items()
    return render_template('headers.html', headers = h)

@app.route('/cookies')
def cookies():
    cookie_value = request.args.get('cookie')
    response = make_response()
    
    if 'my_cookie' in request.cookies:
        response.delete_cookie('my_cookie')
        response.set_data(render_template('cookies.html', cookie_exists=False))
    else:
        if cookie_value:
            response.set_cookie('my_cookie', cookie_value)
            response.set_data(render_template('cookies.html', cookie_exists=True, name='my_cookie', value=cookie_value))
        else:
            response.set_data(render_template('cookies.html', cookie_exists=False))
    
    return response

@app.route('/url')
def url():
    params = request.args.items()
    return render_template('url.html', title='Параметры запроса', parameters = params)

@app.route('/form', methods=['GET', 'POST'])
def form():
    params = request.form.items()
    return render_template('form.html', title='Параметры формы', params=params)

def validate_phone(phone):
    cleaned = re.sub(r'[\s\(\)\-\.\+]', '', phone)
    digits = ''

    if not cleaned.isdigit():
        return None, "Недопустимый ввод. В номере телефона встречаются недопустимые символы."
    
    if phone.startswith(('+7', '8')) and len(cleaned) != 11:
        return None, "Недопустимый ввод. Неверное количество цифр."
    elif not phone.startswith(('+7', '8')) and len(cleaned) != 10:
        return None, "Недопустимый ввод. Неверное количество цифр."
    
    if phone.startswith('+7'):
        digits = cleaned[1:]
    elif phone.startswith('8'):
        digits = cleaned[1:]
    else:
        digits = cleaned
    
    formatted = f"8-{digits[:3]}-{digits[3:6]}-{digits[6:8]}-{digits[8:]}"
    return formatted, None

@app.route('/phone', methods=['GET', 'POST'])
def phone():
    error = None
    formatted = None
    phone = None

    if request.method == 'POST':
        phone = request.form.get('phone')
        if phone:
            formatted, error = validate_phone(phone)

    return render_template('phone.html', error=error, formatted=formatted, phone=phone)

if __name__ == "__main__":
    application.run()