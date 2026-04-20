"""
Flowly Backend - Django Project Package
"""

# Use PyMySQL as MySQL adapter
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

# Initialize Celery app on Django startup (Phase 9)
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    pass
