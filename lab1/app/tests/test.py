import pytest
from flask import url_for, template_rendered
from bs4 import BeautifulSoup
from app import app as flask_app, posts_list
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

def test_index_page_uses_correct_template(client, app):
    with captured_templates(app) as templates:
        response = client.get(url_for('index'))
        assert response.status_code == 200
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'index.html'

def test_posts_page_uses_correct_template(client, app):
    with captured_templates(app) as templates:
        response = client.get(url_for('posts'))
        assert response.status_code == 200
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'posts.html'

def test_post_detail_page_uses_correct_template(client, app):
    with captured_templates(app) as templates:
        response = client.get(url_for('post', index=0))
        assert response.status_code == 200
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'post.html'

def test_about_page_uses_correct_template(client, app):
    with captured_templates(app) as templates:
        response = client.get(url_for('about'))
        assert response.status_code == 200
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'about.html'

def test_posts_page_passes_correct_data(client):
    response = client.get(url_for('posts'))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')
    posts = posts_list

    assert len(posts) == 5
    for post in posts:
        assert post['title'] in response.data.decode()

def test_post_detail_page_passes_correct_data1(client):
    post = posts_list[0]
    response = client.get(url_for('post', index=0))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')

    title = soup.find("h1", class_="post-title")
    assert title is not None
    assert title.text.strip() == post['title']

    author_date = soup.find("p", class_="post-meta")
    assert author_date is not None
    expected_author_date = f"{post['author']}, {post['date'].strftime('%d.%m.%Y')}"
    assert author_date.text.strip() == expected_author_date

    image = soup.find("img", class_="post-image")
    assert image is not None
    assert image["src"] == url_for('static', filename='images/' + post['image_id'])
    assert image["alt"] == post['title']

    post_text = soup.find("p", class_="post-text")
    assert post_text is not None
    assert post_text.text.strip() == post['text']

def test_post_detail_page_passes_correct_data2(client):
    post = posts_list[1]
    response = client.get(url_for('post', index=1))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')

    title = soup.find("h1", class_="post-title")
    assert title is not None
    assert title.text.strip() == post['title']

    author_date = soup.find("p", class_="post-meta")
    assert author_date is not None
    expected_author_date = f"{post['author']}, {post['date'].strftime('%d.%m.%Y')}"
    assert author_date.text.strip() == expected_author_date

    image = soup.find("img", class_="post-image")
    assert image is not None
    assert image["src"] == url_for('static', filename='images/' + post['image_id'])
    assert image["alt"] == post['title']

    post_text = soup.find("p", class_="post-text")
    assert post_text is not None
    assert post_text.text.strip() == post['text']

def test_post_detail_page_displays_comments(client):
    post = posts_list[0]
    response = client.get(url_for('post', index=0))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')

    comments = soup.find_all("div", class_="comment")
    assert len(comments) == len(post['comments'])
    for i, comment in enumerate(comments):
        comment_author = comment.find("div", class_="comment-author")
        assert comment_author is not None
        assert comment_author.text.strip() == post['comments'][i]['author']

        comment_text = comment.find("div", class_="comment-text")
        assert comment_text is not None
        assert comment_text.text.strip() == post['comments'][i]['text']

def test_post_detail_page_displays_comment_form(client):
    response = client.get(url_for('post', index=0))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')

    form = soup.find("form", class_="comment-form")
    assert form is not None
    textarea = form.find("textarea", class_="comment-textarea")
    assert textarea is not None
    assert textarea["placeholder"] == "Ваш комментарий"
    submit_button = form.find("button", class_="comment-submit")
    assert submit_button is not None
    assert submit_button.text.strip() == "Отправить"

def test_post_not_found_returns_404(client):
    response = client.get(url_for('post', index=999))
    assert response.status_code == 404

def test_post_date_format(client):
    post = posts_list[0]
    response = client.get(url_for('post', index=0))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')

    author_date = soup.find("p", class_="post-meta")
    assert author_date is not None
    expected_date = post['date'].strftime('%d.%m.%Y')
    assert expected_date in author_date.text

def test_posts_page_displays_all_posts(client):
    response = client.get(url_for('posts'))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')

    posts = posts_list
    for post in posts:
        assert post['title'] in response.data.decode()

def test_post_detail_page_displays_correct_image(client):
    post = posts_list[0]
    response = client.get(url_for('post', index=0))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')

    image = soup.find("img", class_="post-image")
    assert image is not None
    assert image["src"] == url_for('static', filename='images/' + post['image_id'])
    assert image["alt"] == post['title']

def test_post_detail_page_displays_correct_author(client):
    post = posts_list[0]
    response = client.get(url_for('post', index=0))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')

    author_date = soup.find("p", class_="post-meta")
    assert author_date is not None
    assert post['author'] in author_date.text

def test_post_detail_page_displays_correct_text(client):
    post = posts_list[0]
    response = client.get(url_for('post', index=0))
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')

    post_text = soup.find("p", class_="post-text")
    assert post_text is not None
    assert post['text'] in post_text.text