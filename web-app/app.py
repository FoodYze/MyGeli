from flask import Flask, request, redirect, session, make_response, abort, render_template, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import errorcode, IntegrityError
import os
import hashlib
from datetime import datetime, timedelta
import json
from infrastructure.database_repository import UserProfileRepository, MySQLConnection

# --- Configurações Comuns ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'foodyzeadm',
    'password': 'supfood0017admx',
    'database': 'mygeli',
    'raise_on_warnings': True,
    'autocommit': False
}
REMEMBER_DAYS = 30

# --- CORREÇÃO 1: Inicialização do Flask ---
# Supondo que app.py está na raiz da pasta web-app e 'templates' está nela
app = Flask(__name__, template_folder='templates', static_folder='static') 
# Define explicitamente as pastas

app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- Serviços (UserDBService continua o mesmo) ---
class UserDBService:
    def __init__(self, db_config):
        self.db_config = db_config

    def get_db_connection(self):
        try:
            return mysql.connector.connect(**self.db_config)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                raise RuntimeError("Erro de autenticação no banco de dados.")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                raise RuntimeError("Banco de dados não existe.")
            else:
                raise RuntimeError(f"Erro inesperado de banco: {err}")

    def create_remember_token(self):
        selector = os.urandom(16).hex()
        authenticator = os.urandom(32).hex()
        hashed_authenticator = hashlib.sha256(authenticator.encode()).hexdigest()
        return selector, authenticator, hashed_authenticator

    def save_remember_token(self, user_id, selector, hashed_authenticator):
        expires_dt = datetime.utcnow() + timedelta(days=REMEMBER_DAYS)
        # expires_str = expires_dt.strftime('%Y-%m-%d %H:%M:%S') # MySQL Connector/Python lida com datetime

        cnx = self.get_db_connection()
        cursor = cnx.cursor()
        try:
            # Remove tokens antigos do mesmo usuário para evitar acúmulo (opcional, mas bom)
            cursor.execute("DELETE FROM login_tokens WHERE user_id = %s", (user_id,))
            
            cursor.execute(
                "INSERT INTO login_tokens (user_id, selector, hashed_token, expires) VALUES (%s, %s, %s, %s)",
                (user_id, selector, hashed_authenticator, expires_dt) # Passa o objeto datetime
            )
            cnx.commit()
            return selector, hashed_authenticator, expires_dt
        except mysql.connector.Error as e:
            cnx.rollback()
            raise RuntimeError(f"Erro ao salvar token de login: {e}")
        finally:
            cursor.close()
            cnx.close()

db_service = UserDBService(DB_CONFIG)

mysql_connection = MySQLConnection(DB_CONFIG['host'], DB_CONFIG['user'], DB_CONFIG['password'], DB_CONFIG['database'])
user_profile_repo = UserProfileRepository(mysql_connection)

# --- Rotas ---

@app.route('/')
def home():
    # Redireciona para o login se não estiver logado, senão para a página geral
    if 'user_id' in session:
        return redirect(url_for('general_page'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login-page.html') # Caminho correto

    # ... (lógica do POST continua a mesma) ...
    try:
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        lembrar = request.form.get('lembrar_de_mim') is not None

        cnx = db_service.get_db_connection()
        cursor = cnx.cursor(dictionary=True)
        query = "SELECT id, email, senha FROM usuarios WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        cursor.close()
        cnx.close()

        if not user or not check_password_hash(user['senha'], senha):
            raise ValueError("E-mail ou senha inválidos.")

        session.clear()
        session['user_id'] = user['id']

        response = make_response(redirect(url_for('general_page'))) 

        if lembrar:
            selector, authenticator, hashed_authenticator = db_service.create_remember_token()
            db_service.save_remember_token(user['id'], selector, hashed_authenticator)
            cookie_expires = datetime.utcnow() + timedelta(days=REMEMBER_DAYS)
            cookie_value = f"{selector}:{authenticator}"
            response.set_cookie('remember_me', cookie_value, expires=cookie_expires, path='/', httponly=True, secure=False, samesite='Lax')
        return response

    # --- CORREÇÃO 2: Caminhos nos Erros ---
    except ValueError as ve:
        return render_template('login-page.html', error=str(ve)), 400 # Caminho correto
    except RuntimeError as re:
        return render_template('login-page.html', error=str(re)), 500 # Caminho correto
    except Exception as e:
        # É bom logar o erro 'e' aqui para depuração
        print(f"Erro inesperado no login: {e}") 
        return render_template('login-page.html', error="Erro inesperado. Tente novamente."), 500 # Caminho correto


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register-page.html') # Caminho correto

    # ... (lógica do POST continua a mesma) ...
    try:
        nome = request.form.get('nome', '').strip()
        telefone = request.form.get('telefone', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        confirm_senha = request.form.get('confirm-senha', '')
        remember = request.form.get('remember') is not None

        if not nome or not email or not senha:
            raise ValueError("Campos obrigatórios ausentes.")
        if senha != confirm_senha:
            raise ValueError("As senhas não coincidem.")
        if len(senha) < 6:
            raise ValueError("A senha deve ter no mínimo 6 caracteres.")

        senha_hash = generate_password_hash(senha)

        cnx = db_service.get_db_connection()
        cursor = cnx.cursor()
        try:
            cursor.execute(
                "INSERT INTO usuarios (nome, telefone, email, senha) VALUES (%s, %s, %s, %s)",
                (nome, telefone, email, senha_hash)
            )
            cnx.commit()
            user_id = cursor.lastrowid
        except IntegrityError:
            cnx.rollback()
            raise ValueError("Já existe um usuário com esse e-mail.")
        except mysql.connector.Error as e:
            cnx.rollback()
            raise RuntimeError(f"Erro ao inserir usuário: {e}")
        finally:
            cursor.close()
            cnx.close()

        session.clear()
        session['user_id'] = user_id

        response = make_response(redirect(url_for('general_page'))) 

        if remember:
            selector, authenticator, hashed_authenticator = db_service.create_remember_token()
            db_service.save_remember_token(user_id, selector, hashed_authenticator)
            cookie_expires = datetime.utcnow() + timedelta(days=REMEMBER_DAYS)
            cookie_value = f"{selector}:{authenticator}"
            response.set_cookie('remember_me', cookie_value, expires=cookie_expires, path='/', httponly=True, secure=False, samesite='Lax')
        return response

    # --- CORREÇÃO 2: Caminhos nos Erros ---
    except ValueError as ve:
        return render_template('register-page.html', error=str(ve)), 400 # Caminho correto
    except RuntimeError as re:
        return render_template('register-page.html', error=str(re)), 500 # Caminho correto
    except Exception as e:
        # É bom logar o erro 'e' aqui para depuração
        print(f"Erro inesperado no registro: {e}") 
        return render_template('register-page.html', error="Erro inesperado. Tente novamente."), 500 # Caminho correto


# --- CORREÇÃO 3: Renderizar Template na Página Geral ---
@app.route('/general-page') # Rota mais simples
def general_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Aqui você pode buscar dados do usuário se precisar e passar para o template
    # user_data = buscar_dados_usuario(session['user_id']) 
    return render_template('general-page.html') # Renderiza o HTML

@app.route('/chatbot') # Defines the URL, e.g., http://127.0.0.1:5000/chatbot
def chatbot_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    stock_dict = {}
    cnx = None
    cursor = None
    
    try:
        cnx = db_service.get_db_connection()
        cursor = cnx.cursor(dictionary=True)
        
        query = "SELECT nome_produto, quantidade_produto, tipo_volume from produtos WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        
        for row in cursor.fetchall():
            item_name = row['nome_produto']
            item_qty = row['quantidade_produto']
            item_unit = row['tipo_volume']
            
            stock_dict[item_name] = f"{item_qty} {item_unit}"
            
    except mysql.connector.Error as err:
        print(f"Erro ao buscar estoque do usuário {user_id}: {err}")
    finally:
        if cursor:
            cursor.close()
        if cnx:
            cnx.close()
            
    stock_json = json.dumps(stock_dict)
    
    return render_template('chatbot-page.html', user_stock_json=stock_json)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    success_message = None

    if request.method == 'POST':
        preferences_data = {
            'allergies': request.form.get('allergies', ''),
            'dietary_restrictions': request.form.get('dietary_restrictions', ''),
            'other': request.form.get('other', '')
        }
        # Converte o dicionário para uma string JSON
        preferences_json = json.dumps(preferences_data)
        
        try:
            user_profile_repo.update_user_preferences(user_id, preferences_json)
            success_message = "Preferências salvas com sucesso!"
        except RuntimeError as e:
            print(e)
            pass 

    # Busca os dados atuais do usuário (para GET e para recarregar após POST)
    user_data = user_profile_repo.get_user_details_by_id(user_id)
    
    user_preferences = {'allergies': '', 'dietary_restrictions': '', 'other': ''}
    if user_data.get('preferencias'):
        user_preferences = json.loads(user_data['preferencias'])
    
    return render_template(
        'profile-page.html', 
        user=user_data, 
        user_preferences=user_preferences,
        success_message=success_message
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
