import mysql.connector
from flask import g

class DBConnector:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        if 'db_connector' not in app.extensions:
            app.extensions['db_connector'] = self
            app.teardown_appcontext(self.disconnect)

    def _get_config(self):
        return {
            'user': self.app.config["MYSQL_USER"],
            'password': self.app.config["MYSQL_PASSWORD"],
            'host': self.app.config["MYSQL_HOST"],
            'database': self.app.config["MYSQL_DATABASE"]
        }
    
    def connect(self):
        if 'db' not in g:
            g.db = mysql.connector.connect(**self._get_config())
        return g.db
    
    def disconnect(self, e=None):
        try:
            db = g.pop('db', None)
            if db is not None:
                db.close()
        except RuntimeError:
            pass

dbConnector = DBConnector()