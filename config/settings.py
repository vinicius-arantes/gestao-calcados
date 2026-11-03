"""
Configurações do projeto Passo Firme — Gestão de Estoque e Produção de Calçados.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-cu*0-v!ga$6)yix2eg3w3+&01v-^m-iz_&)i5x)5m6wjcu3mtd',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    # O Jazzmin precisa vir antes do django.contrib.admin
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Apps do projeto
    'contas',
    'catalogo',
    'estoque',
    'producao',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Jazzmin — tema do ambiente administrativo
# ---------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    'site_title': 'Passo Firme Admin',
    'site_header': 'Passo Firme',
    'site_brand': 'Passo Firme',
    'welcome_sign': 'Ambiente administrativo — Gestão de Calçados',
    'copyright': 'Passo Firme',
    'show_sidebar': True,
    'navigation_expanded': True,
    'order_with_respect_to': [
        'producao', 'catalogo', 'estoque', 'contas', 'auth',
        'catalogo.Modelo', 'catalogo.Variacao', 'catalogo.Categoria',
        'catalogo.Colecao', 'catalogo.Cor', 'catalogo.Tamanho',
        'estoque.Material', 'estoque.Fornecedor',
        'estoque.MovimentacaoMaterial', 'estoque.MovimentacaoProduto',
    ],
    'search_model': ['catalogo.Modelo', 'estoque.Material'],
    'icons': {
        'auth': 'fas fa-users-cog',
        'auth.user': 'fas fa-user',
        'auth.Group': 'fas fa-users',
        'catalogo.Categoria': 'fas fa-tags',
        'catalogo.Colecao': 'fas fa-layer-group',
        'catalogo.Cor': 'fas fa-palette',
        'catalogo.Tamanho': 'fas fa-ruler',
        'catalogo.Modelo': 'fas fa-shoe-prints',
        'catalogo.Variacao': 'fas fa-boxes',
        'estoque.Fornecedor': 'fas fa-truck',
        'estoque.Material': 'fas fa-cut',
        'estoque.MovimentacaoMaterial': 'fas fa-exchange-alt',
        'estoque.MovimentacaoProduto': 'fas fa-dolly',
    },
    'default_icon_parents': 'fas fa-folder',
    'default_icon_children': 'fas fa-circle',
    'related_modal_active': True,
    'changeform_format': 'horizontal_tabs',
    'changeform_format_overrides': {'auth.user': 'collapsible', 'auth.group': 'vertical_tabs'},
    'show_ui_builder': False,
    # Exibe na barra superior o seletor de tema e de modo claro/escuro
    'show_theme_chooser': True,
}

JAZZMIN_UI_TWEAKS = {
    'brand_colour': 'navbar-orange',
    'accent': 'accent-orange',
    'navbar': 'navbar-dark',
    'no_navbar_border': True,
    'navbar_fixed': True,
    'sidebar_fixed': True,
    'sidebar': 'sidebar-dark-orange',
    'sidebar_nav_child_indent': True,
    'sidebar_nav_flat_style': True,
    'theme': 'flatly',
    # Segue o tema do sistema operacional; o usuário pode trocar no seletor da barra superior
    'default_theme_mode': 'auto',
}
