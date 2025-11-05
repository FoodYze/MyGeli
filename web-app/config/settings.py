import os

# Credenciais do banco de dados a serem obtidas de variáveis de ambiente
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'foodyzeadm')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'supfood0017admx')
DB_NAME = os.environ.get('DB_NAME', 'mygeli')
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Outras configurações
REMEMBER_DAYS = 30