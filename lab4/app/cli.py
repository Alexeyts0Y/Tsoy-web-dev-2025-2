import click

from flask import current_app
from .db import dbConnector as db

@click.command('init-db')
def init_db_command():
    with current_app.open_resource('schema.sql') as f:
        connection = db.connect()
        with connection.cursor() as cursor:
            sql_script = f.read().decode('utf8')
            
            for statement in sql_script.split(';'):
                if statement.strip():
                    cursor.execute(statement)
                    
        connection.commit()
    click.echo('Initialized the database.')