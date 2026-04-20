"""
Test settings — overrides flowly_backend.settings to use SQLite.

IMPORTANT: Must be set as DJANGO_SETTINGS_MODULE before importing settings.
"""
import os

# Force SQLite BEFORE importing settings to override any DATABASE_URL
os.environ.setdefault("DATABASE_URL", "")  # Clear to force SQLite path

from flowly_backend.settings import *  # noqa: F401, F403

# Force SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable channels for tests
CHANNEL_LAYERS = {}
