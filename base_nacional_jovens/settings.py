"""
Django settings for base_nacional_jovens project.
Base Nacional de Jovens - São Tomé e Príncipe
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Simple .env loader (optional)
def _load_env_file():
    env_path = BASE_DIR / '.env'
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

_load_env_file()

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

if DB_ENGINE == 'mysql':
    try:
        import pymysql
    except ImportError as exc:
        raise ImportError(
            'PyMySQL is required to use the MySQL database configuration.'
        ) from exc

    pymysql.version_info = (2, 2, 1, 'final', 0)
    pymysql.install_as_MySQLdb()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-9rg3#jyllnh3+_vc3s*mpz#siz8-bnea0n+yldb^8*6kx6$8*^'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Apps do projeto
    'accounts',
    'profiles',
    'companies',
    'dashboard',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.AuditLogMiddleware',
]

ROOT_URLCONF = 'base_nacional_jovens.urls'

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
                'core.context_processors.user_profile',
            ],
        },
    },
]

WSGI_APPLICATION = 'base_nacional_jovens.wsgi.application'

# Database
if DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'base_nacional_jovens.db_backends.mysql_xampp',
            'NAME': os.environ.get('DB_NAME', 'base_nacional_jovens'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            'TEST': {
                'CHARSET': 'utf8mb4',
                'COLLATION': 'utf8mb4_unicode_ci',
            },
        }
    }
elif DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    raise ValueError(f'Unsupported DB_ENGINE: {DB_ENGINE}')

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
LANGUAGE_CODE = 'pt-pt'
TIME_ZONE = 'Africa/Sao_Tome'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Login/Logout URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 horas
SESSION_SAVE_EVERY_REQUEST = True

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Company logo processing settings
# Maximum logo size in megabytes
COMPANY_LOGO_MAX_SIZE_MB = 2
# Maximum dimensions (width, height) used when resizing uploaded logos
COMPANY_LOGO_MAX_DIM = (512, 512)
# JPEG quality used when saving processed logos (1-95)
COMPANY_LOGO_QUALITY = 85

# Districts de São Tomé e Príncipe
DISTRICTS = [
    ('AG', 'Água Grande'),
    ('CA', 'Cantagalo'),
    ('CO', 'Caué'),
    ('LE', 'Lembá'),
    ('LO', 'Lobata'),
    ('ME', 'Mé-Zóchi'),
    ('PR', 'Príncipe'),
]

# Níveis de Educação
EDUCATION_LEVELS = [
    ('BAS', 'Básico'),
    ('SEC', 'Secundário'),
    ('TEC', 'Técnico'),
    ('SUP', 'Superior'),
]

# Áreas de Formação
AREAS_FORMACAO = [
    ('AGR', 'Agricultura'),
    ('TUR', 'Turismo'),
    ('TIC', 'Tecnologias de Informação'),
    ('IND', 'Indústria'),
    ('SER', 'Serviços'),
    ('ENE', 'Energias Renováveis'),
    ('ADM', 'Administração'),
    ('SAU', 'Saúde'),
    ('EDU', 'Educação'),
    ('CON', 'Construção'),
    ('ELE', 'Eletricidade'),
    ('CAN', 'Canalização'),
    ('INF', 'Informática'),
    ('OUT', 'Outra'),
]

# Skills Técnicas
SKILLS_TECNICAS = [
    ('eletricidade', 'Eletricidade'),
    ('canalizacao', 'Canalização'),
    ('informatica', 'Informática'),
    ('energias_renovaveis', 'Energias Renováveis'),
    ('mecanica', 'Mecânica'),
    ('carpintaria', 'Carpintaria'),
    ('pedreiro', 'Pedreiro'),
    ('soldadura', 'Soldadura'),
    ('confeitaria', 'Confeitaria'),
    ('costura', 'Costura'),
    ('agricultura', 'Agricultura'),
    ('pescaria', 'Pescaria'),
    ('turismo', 'Turismo'),
    ('programacao', 'Programação'),
    ('design', 'Design Gráfico'),
    ('marketing', 'Marketing Digital'),
]

# Skills Transversais
SKILLS_TRANSVERSAIS = [
    ('comunicacao', 'Comunicação'),
    ('trabalho_equipa', 'Trabalho em Equipa'),
    ('lideranca', 'Liderança'),
    ('resolucao_problemas', 'Resolução de Problemas'),
    ('gestao_tempo', 'Gestão do Tempo'),
    ('adaptabilidade', 'Adaptabilidade'),
    ('criatividade', 'Criatividade'),
    ('pensamento_critico', 'Pensamento Crítico'),
    ('negociacao', 'Negociação'),
    ('empatia', 'Empatia'),
]

# SMS / Phone change settings
SMS_BACKEND = os.environ.get('SMS_BACKEND', 'console')  # 'console' or 'twilio'
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER', '')

# Email settings
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@basenacionaljovens.st')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '1') == '1'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', '0') == '1'

# Phone change rate limiting
PHONE_CHANGE_LIMIT_PER_DAY = int(os.environ.get('PHONE_CHANGE_LIMIT_PER_DAY', '3'))
PHONE_CHANGE_MIN_INTERVAL_SECONDS = int(os.environ.get('PHONE_CHANGE_MIN_INTERVAL_SECONDS', '300'))

# Situação Profissional
SITUACAO_PROFISSIONAL = [
    ('EMP', 'Empregado'),
    ('DES', 'Desempregado'),
    ('PEM', 'Primeiro Emprego'),
]

# Tipos de Oportunidade
TIPOS_OPORTUNIDADE = [
    ('EST', 'Estágio'),
    ('EMP', 'Emprego'),
    ('FOR', 'Formação de Curta Duração'),
    ('EMPRE', 'Empreendedorismo'),
]

# Tipos de Vaga
TIPOS_VAGA = [
    ('EST', 'Estágio'),
    ('EMP', 'Emprego'),
    ('FOR', 'Formação'),
]

# Estados de Vaga
ESTADOS_VAGA = [
    ('ATIVA', 'Ativa'),
    ('FECHADA', 'Fechada'),
    ('PAUSADA', 'Pausada'),
]

# Estados de Candidatura
ESTADOS_CANDIDATURA = [
    ('PENDENTE', 'Pendente'),
    ('EM_ANALISE', 'Em Análise'),
    ('ACEITE', 'Aceite'),
    ('REJEITADA', 'Rejeitada'),
]

# Estados de Pedido de Contacto
ESTADOS_CONTACTO = [
    ('PENDENTE', 'Pendente'),
    ('APROVADO', 'Aprovado'),
    ('REJEITADO', 'Rejeitado'),
]

# Tipos de Documento
TIPOS_DOCUMENTO = [
    ('CV', 'Curriculum Vitae'),
    ('CERT', 'Certificado'),
    ('BI', 'Bilhete de Identidade'),
    ('OUTRO', 'Outro'),
]
