from flask import Flask, request, redirect, session, make_response, abort, render_template, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import errorcode, IntegrityError
import os
import hashlib
from datetime import datetime, timedelta

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

app = Flask(__name__) # O static_folder aponta para o diretório raiz para arquivos estáticos como CSS/JS dentro das subpastas

app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- Serviços (Podem ser movidos para arquivos separados para modularidade) ---

class UserDBService: # Um serviço mais geral para interações com o DB
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
        expires_str = expires_dt.strftime('%Y-%m-%d %H:%M:%S')

        cnx = self.get_db_connection()
        cursor = cnx.cursor()
        try:
            cursor.execute(
                "INSERT INTO login_tokens (user_id, selector, hashed_token, expires) VALUES (%s, %s, %s, %s)",
                (user_id, selector, hashed_authenticator, expires_str)
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

# --- Rotas ---

@app.route('/')
def home():
    # Se você quiser uma página inicial diferente, pode renderizar outro template
    # Por agora, redireciona para o login
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login-page.html')

    if 'login' not in request.form:
        abort(400, "Requisição inválida.")

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

        response = make_response(redirect(url_for('general_page'))) # Altere para sua página geral após o login

        if lembrar:
            selector, authenticator, hashed_authenticator = db_service.create_remember_token()
            db_service.save_remember_token(user['id'], selector, hashed_authenticator) # Note que 'save_remember_token' já tem a lógica de expiração

            cookie_expires = datetime.utcnow() + timedelta(days=REMEMBER_DAYS)
            cookie_value = f"{selector}:{authenticator}" # O authenticator NÃO HASHED é usado no cookie

            response.set_cookie(
                'remember_me',
                cookie_value,
                expires=cookie_expires,
                path='/',
                httponly=True,
                secure=False, # Mude para True em produção com HTTPS
                samesite='Lax'
            )
        return response

    except ValueError as ve:
        return render_template('login_page/index.html', error=str(ve)), 400
    except RuntimeError as re:
        return render_template('login_page/index.html', error=str(re)), 500
    except Exception as e:
        return render_template('login_page/index.html', error=f"Erro inesperado: {e}"), 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register-page.html')

    if 'cadastrar' not in request.form:
        abort(400, "Requisição inválida.")

    try:
        nome = request.form.get('nome', '').strip()
        telefone = request.form.get('telefone', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        confirm_senha = request.form.get('confirm-senha', '')
        remember = request.form.get('remember') is not None # Renomeei para evitar conflito com 'lembrar'

        if not nome or not email or not senha:
            raise ValueError("Campos obrigatórios ausentes.")

        if senha != confirm_senha:
            raise ValueError("As senhas não coincidem.")

        if len(senha) < 6:
            raise ValueError("A senha deve ter no mínimo 6 caracteres.")

        senha_hash = generate_password_hash(senha)

        cnx = db_service.get_db_connection()
        cursor = cnx.cursor(buffered=True)
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

        response = make_response(redirect(url_for('general_page'))) # Redirecionar para a página geral após o cadastro

        if remember:
            selector, authenticator, hashed_authenticator = db_service.create_remember_token()
            db_service.save_remember_token(user_id, selector, hashed_authenticator)

            cookie_expires = datetime.utcnow() + timedelta(days=REMEMBER_DAYS)
            cookie_value = f"{selector}:{authenticator}"

            response.set_cookie(
                'remember_me',
                cookie_value,
                expires=cookie_expires,
                path='/',
                httponly=True,
                secure=False, # Mude para True em produção com HTTPS
                samesite='Lax'
            )
        return response

    except ValueError as ve:
        return render_template('register_page/index.html', error=str(ve)), 400
    except RuntimeError as re:
        return render_template('register_page/index.html', error=str(re)), 500
    except Exception as e:
        return render_template('register_page/index.html', error=f"Erro inesperado: {e}"), 500


@app.route('/general-page/index') # Exemplo de rota para a página após o login
def general_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return "Bem-vindo à página geral! (Conteúdo protegido)"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)