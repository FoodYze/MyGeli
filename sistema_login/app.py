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

# --- Funções auxiliares ---

def get_client_ip():
    """ Tentar obter o endereço IP do cliente de forma robusta, considerando proxies """
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def hash_data(data):
    """ Criptografa uma string usando SHA256 """
    return hashlib.sha256(data.encode()).hexdigest()

class DBService:
    def __init__(self, db_config):
        self.db_config = db_config

    def get_user_preferences(self, user_id):
        cnx = self.get_db_connection()
        cursor = cnx.cursor()
        try:
            query = "SELECT preferencias FROM usuarios WHERE id = %s"
            cursor.execute(query, (user_id,))
            resultado = cursor.fetchone()
            if resultado and resultado[0]:
                return resultado[0]
            return None
        except mysql.connector.Error as e:
            print(f"Erro ao buscar preferências do usuário: {e}")
            return None
        finally:
            cursor.close()
            cnx.close()

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

class LogDBService:
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
            
    def log_action(self, user_id, action, status, ip_address):
        """
        Registra uma ação do usuário na tabela 'log'.
        :param user_id: ID do usuário que realizou a ação (ou NONE se não estiver logado).
        :param action: Descrição da ação (e.g., "Login", "Register").
        :param status: Status da ação ("Success" ou "Failed").
        :param ip_address: endereço IP do cliente. Será armazenado criptografado.
        """

        cnx = self.get_db_connection()
        cursor = cnx.cursor()
        try:
            # Garantir que user_id seja None se não houver usuário logado
            user_id_to_log = user_id if user_id is not None else None
            hashed_ip = hash_data(ip_address) # Criptografa o IP
            current_datetime = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute(
                "INSERT INTO log (id_user, action, status, date_time, ip_address) VALUES (%s, %s, %s, %s, %s)",
                (user_id_to_log, action, status, current_datetime, hashed_ip)
            )
            cnx.commit()
        except mysql.connector.Error as e:
            cnx.rollback()
            print(f"ERRO AO REGISTRAR LOG: {e}") # Considerar usar um sistema de logging real (ex: logging)
        finally:
            cursor.close()
            cnx.close()


db_service = DBService(DB_CONFIG)
log_service = LogDBService(DB_CONFIG)

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

    ip_address = get_client_ip()
    user_id_logged = None # Para registrar o log, inicializamos como None

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

        if not user:
            log_service.log_action(None, "Login", "Failed", ip_address) # Não encontrou o user, IP é None
            raise ValueError("E-mail ou senha inválidos.")
        
        user_id_logged = user['id'] # Se o user foi encontrado, definir o IP

        if not check_password_hash(user['senha'], senha):
            log_service.log_action(user_id_logged, "Login", "Failed", ip_address)
            raise ValueError("E-mail ou senha inválidos.")
        
        session.clear()
        session['user_id'] = user_id_logged
        log_service.log_action(user_id_logged, "Login", "Success", ip_address) # Login bem sucedido

        response = make_response(redirect(url_for('general_page')))

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
        # Erro de validação já tratado, o log já foi feito ou não havia user_id
        return render_template('login_page/index.html', error=str(ve)), 400
    except RuntimeError as re:
        log_service.log_action(user_id_logged, "Login", "Failed", ip_address) # Em caso de erro no BD
        return render_template('login_page/index.html', error=str(re)), 500
    except Exception as e:
        log_service.log_action(user_id_logged, "Login", "Failed", ip_address) # Para erros inesperados
        return render_template('login_page/index.html', error=f"Erro inesperado: {e}"), 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register-page.html')

    if 'cadastrar' not in request.form:
        abort(400, "Requisição inválida.")

    ip_address = get_client_ip()
    new_user_id = None # Para registrar o log, inicializamos como None

    try:
        nome = request.form.get('nome', '').strip()
        telefone = request.form.get('telefone', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        confirm_senha = request.form.get('confirm-senha', '')
        preferencias = request.form.get('preferencias', '').strip()

        remember = request.form.get('remember') is not None # Renomeei para evitar conflito com 'lembrar'

        if not nome or not email or not senha:
            log_service.log_action(None, "Register", "Failed", ip_address)
            raise ValueError("Campos obrigatórios ausentes.")

        if senha != confirm_senha:
            log_service.log_action(None, "Register", "Failed", ip_address)
            raise ValueError("As senhas não coincidem.")

        if len(senha) < 6:
            log_service.log_action(None, "Register", "Failed", ip_address)
            raise ValueError("A senha deve ter no mínimo 6 caracteres.")

        senha_hash = generate_password_hash(senha)

        cnx = db_service.get_db_connection()
        cursor = cnx.cursor(buffered=True)
        try:
            cursor.execute(
                "INSERT INTO usuarios (nome, telefone, email, senha, preferencias) VALUES (%s, %s, %s, %s, %s)",
                (nome, telefone, email, senha_hash, preferencias) # A variável 'preferencias' foi adicionada no final.
            )
            cnx.commit()
            new_user_id = cursor.lastrowid
            log_service.log_action(new_user_id, "Register", "Success", ip_address) # Cadastro bem-sucedido
        except IntegrityError:
            cnx.rollback()
            log_service.log_action(None, "Register", "Failed", ip_address) # Falha por e-mail duplicado
            raise ValueError("Já existe um usuário com esse e-mail.")
        except mysql.connector.Error as e:
            cnx.rollback()
            log_service.log_action(None, "Register", "Failed", ip_address) # Falha genérica do DB
            raise RuntimeError(f"Erro ao inserir usuário: {e}")
        finally:
            cursor.close()
            cnx.close()

        session.clear()
        session['user_id'] = new_user_id

        response = make_response(redirect(url_for('general_page'))) # Redirecionar para a página geral após o cadastro

        if remember:
            selector, authenticator, hashed_authenticator = db_service.create_remember_token()
            db_service.save_remember_token(new_user_id, selector, hashed_authenticator)

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
        # Erro de validação já tratado, o log já foi feito ou não havia new_user_id
        return render_template('register_page/index.html', error=str(ve)), 400
    except RuntimeError as re:
        log_service.log_action(new_user_id, "Register", "Failed", ip_address) # Em caso de erro no BD
        return render_template('register_page/index.html', error=str(re)), 500
    except Exception as e:
        log_service.log_action(new_user_id, "Register", "Failed", ip_address) # Para erros inesperados
        return render_template('register_page/index.html', error=f"Erro inesperado: {e}"), 500


@app.route('/general-page/index') # Exemplo de rota para a página após o login
def general_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return "Bem-vindo à página geral! (Conteúdo protegido)"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)