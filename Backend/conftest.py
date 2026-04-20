"""
pytest configuration — force SQLite for all tests.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flowly_backend.test_settings")

import django
django.setup()
