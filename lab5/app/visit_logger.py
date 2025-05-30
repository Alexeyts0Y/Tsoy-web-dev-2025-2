import csv
from io import StringIO, BytesIO
from flask import Blueprint, request, render_template, current_app, send_file, flash, redirect, url_for
from flask_login import current_user
from .repositories.visit_log_repository import VisitLogRepository
from .db import dbConnector as db
from .auth import check_rights

bp = Blueprint('visit_logs', __name__, url_prefix='/visit_logs')

visit_log_repository = VisitLogRepository(db)

RECORDS_PER_PAGE = 10

@bp.before_app_request
def log_request_info():
    if request.endpoint and (request.endpoint.startswith('static') or \
                            request.endpoint == 'auth.logout' or \
                            request.endpoint == 'None'):
        return

    user_id = current_user.id if current_user.is_authenticated else None
    path = request.path

    if path == '/favicon.ico':
        return
        
    visit_log_repository.create(path, user_id)

@bp.route('/')
@check_rights(['admin', 'user'])
def index():
    page = request.args.get('page', 1, type=int)

    if current_user.is_authenticated and current_user.is_admin:
        user_id = None
    else:
        user_id = current_user.id if current_user.is_authenticated else None

    total_records = visit_log_repository.get_log_count(user_id=user_id)
    total_pages = (total_records + RECORDS_PER_PAGE - 1) // RECORDS_PER_PAGE
    offset = (page - 1) * RECORDS_PER_PAGE

    logs = visit_log_repository.get_all_logs(limit=RECORDS_PER_PAGE, offset=offset, user_id=user_id)
    
    formatted_logs = []
    for log in logs:
        user_full_name = "Неаутентифицированный пользователь"
        if log.get('first_name') and log.get('last_name'):
            user_full_name = f"{log['last_name']} {log['first_name']}"
            if log.get('middle_name'):
                user_full_name += f" {log['middle_name']}"
        
        formatted_logs.append({
            'id': log['id'],
            'user': user_full_name,
            'path': log['path'],
            'created_at': log['created_at'].strftime('%d.%m.%Y %H:%M:%S')
        })
    
    return render_template('visit_logs/index.html', 
                           logs=formatted_logs, 
                           page=page, 
                           total_pages=total_pages,
                           total_records=total_records)

@bp.route('/pages_report')
@check_rights(['admin'])
def pages_report():
    stats = visit_log_repository.get_page_visit_stats()
    return render_template('visit_logs/pages_report.html', stats=stats)

@bp.route('/pages_report/export_csv')
@check_rights(['admin'])
def pages_report_export_csv():
    stats = visit_log_repository.get_page_visit_stats()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['№', 'Страница', 'Количество посещений'])
    for i, row in enumerate(stats):
        cw.writerow([i + 1, row['path'], row['visit_count']])

    output_bytes = BytesIO(si.getvalue().encode('utf-8'))
    output_bytes.seek(0) # Указатель в начало файла
    
    return send_file(
        output_bytes,
        mimetype='text/csv',
        as_attachment=True,
        download_name='pages_report.csv'
    )

@bp.route('/users_report')
@check_rights(['admin'])
def users_report():
    stats = visit_log_repository.get_user_visit_stats()
    formatted_stats = []
    for stat in stats:
        user_full_name = "Неаутентифицированный пользователь"
        if stat.get('first_name') and stat.get('last_name'):
            user_full_name = f"{stat['last_name']} {stat['first_name']}"
            if stat.get('middle_name'):
                user_full_name += f" {stat['middle_name']}"
        
        formatted_stats.append({
            'user': user_full_name,
            'visit_count': stat['visit_count']
        })
    return render_template('visit_logs/users_report.html', stats=formatted_stats)

@bp.route('/users_report/export_csv')
@check_rights(['admin'])
def users_report_export_csv():
    stats = visit_log_repository.get_user_visit_stats()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['№', 'Пользователь', 'Количество посещений'])
    for i, row in enumerate(stats):
        user_full_name = "Неаутентифицированный пользователь"

        if row.get('first_name') and row.get('last_name'):
            user_full_name = f"{row['last_name']} {row['first_name']}"
            if row.get('middle_name'):
                user_full_name += f" {row['middle_name']}"
        cw.writerow([i + 1, user_full_name, row['visit_count']])

    output_bytes = BytesIO(si.getvalue().encode('utf-8'))
    output_bytes.seek(0)
    
    return send_file(
        output_bytes,
        mimetype='text/csv', 
        as_attachment=True,#
        download_name='users_report.csv'
    )