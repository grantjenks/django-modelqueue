from django.db.backends.signals import connection_created


def improve_sqlite_performance(sender, connection, **kwargs):
    "Improve SQLite performance."
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA journal_mode = WAL')
        cursor.execute('PRAGMA synchronous = NORMAL')

connection_created.connect(improve_sqlite_performance)
