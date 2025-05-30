from datetime import datetime

class VisitLogRepository:
    def __init__(self, db_connector):
        self.db_connector = db_connector

    def create(self, path, user_id=None):
        connection = self.db_connector.connect()
        with connection.cursor() as cursor:
            query = "INSERT INTO visit_logs (path, user_id) VALUES (%s, %s);"
            cursor.execute(query, (path, user_id))
            connection.commit()

    def get_all_logs(self, limit=None, offset=None, user_id=None):
        with self.db_connector.connect().cursor(dictionary=True) as cursor:
            query = """
                SELECT
                    vl.id,
                    vl.path,
                    vl.created_at,
                    u.first_name,
                    u.last_name,
                    u.middle_name
                FROM visit_logs vl
                LEFT JOIN users u ON vl.user_id = u.id
            """
            params = []
            if user_id is not None:
                query += " WHERE vl.user_id = %s"
                params.append(user_id)

            query += " ORDER BY vl.created_at DESC"
            
            if limit is not None and offset is not None:
                query += " LIMIT %s OFFSET %s"
                params.extend([limit, offset])

            cursor.execute(query, tuple(params))
            logs = cursor.fetchall()
        return logs

    def get_log_count(self, user_id=None):
        with self.db_connector.connect().cursor() as cursor:
            query = "SELECT COUNT(*) FROM visit_logs"
            params = []
            if user_id is not None:
                query += " WHERE user_id = %s"
                params.append(user_id)
            cursor.execute(query, tuple(params))
            count = cursor.fetchone()[0]
        return count

    def get_page_visit_stats(self):
        with self.db_connector.connect().cursor(dictionary=True) as cursor:
            query = """
                SELECT
                    path,
                    COUNT(*) AS visit_count
                FROM visit_logs
                GROUP BY path
                ORDER BY visit_count DESC;
            """
            cursor.execute(query)
            stats = cursor.fetchall()
        return stats

    def get_user_visit_stats(self):
        with self.db_connector.connect().cursor(dictionary=True) as cursor:
            query = """
                SELECT
                    u.first_name,
                    u.last_name,
                    u.middle_name,
                    COUNT(vl.id) AS visit_count
                FROM uesrs u
                LEFT JOIN visit_logs vl ON vl.user_id = u.id
                GROUP BY u.id, u.first_name, u.last_name, u.middle_name
                ORDER BY visit_count DESC;
            """
            cursor.execute(query)
            stats = cursor.fetchall()
        return stats