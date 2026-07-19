import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

# --- Content for render.yaml ---
# This file defines the infrastructure on Render using Infrastructure as Code (IaC).
# It sets up a web service (your backend application), a PostgreSQL database,
# and a job to run database migrations.
render_yaml_content = """
services:
  - type: web
    name: your-project-backend
    env: python
    buildCommand: "./build.sh"
    startCommand: "gunicorn your_project_name.wsgi:application --bind 0.0.0.0:$PORT"
    healthCheckPath: /health
    envVars:
      - key: SECRET_KEY
        generateValue: true # Render will generate a strong, unique secret key for production
      - key: DEBUG
        value: "False" # Ensure DEBUG is False in production for security and performance
      - key: ALLOWED_HOSTS
        value: "localhost,127.0.0.1,your-project-backend.onrender.com" # Add your custom domain here if applicable
      - key: DATABASE_URL
        fromDatabase:
          name: your-project-db
          property: connectionString
      - key: STATIC_URL
        value: "/static/" # Default static URL, configure as needed
      - key: MEDIA_URL
        value: "/media/" # Default media URL, consider cloud storage for production media

  - type: postgres
    name: your-project-db
    plan: starter # Choose your desired plan (e.g., 'starter', 'standard')
    databaseName: your_project_db
    user: your_project_user

  - type: job
    name: migrate-db
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python manage.py migrate"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: your-project-db
          property: connectionString
    autoDeploy: false # This job should typically be run manually or triggered explicitly, not on every deploy
"""

# --- Content for Procfile ---
# This file declares the processes that should be run by the application on Render.
# The 'web' process starts the Gunicorn WSGI server to serve your Django application.
procfile_content = """
web: gunicorn your_project_name.wsgi:application --bind 0.0.0.0:$PORT
"""

# --- Content for requirements.txt ---
# This file lists all Python dependencies required for your project.
# Render will use this file to install packages during the build process.
requirements_txt_content = """
Django==4.2.11
gunicorn==21.2.0
psycopg2-binary==2.9.9
dj-database-url==2.1.0
whitenoise==6.6.0
python-dotenv==1.0.1
"""

# --- Content for .env.example ---
# This file serves as a template for your local .env file.
# It lists all necessary environment variables without their sensitive values.
# DO NOT commit your actual .env file to version control.
env_example_content = """
# .env.example - Example environment variables for local development

# Django Secret Key (use a strong, unique key for production, Render will generate one)
SECRET_KEY=your_insecure_local_secret_key_here

# Debug mode (set to True for local development, False for production)
DEBUG=True

# Allowed hosts for Django (comma-separated list)
ALLOWED_HOSTS=localhost,127.0.0.1

# Database URL for local development
# Example for PostgreSQL: postgres://user:password@host:port/database_name
# Example for SQLite: sqlite:///db.sqlite3
DATABASE_URL=sqlite:///db.sqlite3
"""

# --- Content for settings.py (Django example) ---
# This is a simplified Django settings file, configured to read environment
# variables for sensitive data and production settings, suitable for Render.
settings_py_content = """
import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file during local development
# This line should be at the very top of your settings file.
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# It's retrieved from environment variables for production, or uses a fallback for local dev.
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-your-local-fallback-secret-key-for-dev")

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG is controlled by an environment variable.
DEBUG = os.environ.get("DEBUG", "False") == "True"

# Allowed hosts for Django, retrieved from environment variables.
ALLOWED_HOSTS_STR = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(',')]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Your project-specific apps would go here, e.g.:
    # 'your_app_name',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # WhiteNoise must be listed after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'your_project_name.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'your_project_name.wsgi.application'

# Database configuration
# Uses dj-database-url to parse the DATABASE_URL environment variable provided by Render.
# Falls back to SQLite for local development if DATABASE_URL is not set.
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600 # Keep database connections open for up to 10 minutes
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# STATIC_URL is retrieved from environment variables.
STATIC_URL = os.environ.get('STATIC_URL', '/static/')
# STATIC_ROOT is where collected static files will be stored.
STATIC_ROOT = BASE_DIR / 'staticfiles'
# WhiteNoise storage backend for serving compressed and cached static files.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (user-uploaded content)
# For production, consider using a cloud storage service like AWS S3 or a dedicated media CDN.
MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
"""

# --- Content for build.sh ---
# This shell script is executed by Render during the build phase.
# It installs Python dependencies, collects static files, and runs database migrations.
build_sh_content = """
#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Collecting static files..."
# Collects all static files into STATIC_ROOT. --noinput prevents interactive prompts.
python manage.py collectstatic --noinput

echo "Running database migrations..."
# Applies pending database migrations.
python manage.py migrate
"""

# Note: This script defines the content of various configuration files as Python strings.
# To use them, you would typically save each string to its respective file:
#
# with open("render.yaml", "w") as f:
#     f.write(render_yaml_content)
#
# with open("Procfile", "w") as f:
#     f.write(procfile_content)
#
# and so on for the other files.