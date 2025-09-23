# Importe 'render_template' e 'send_from_directory'
from flask import Flask, request, redirect, session, make_response, abort, render_template, send_from_directory
from werkzeug.security import generate_password_hash
import mysql.connector
from mysql.connector import errorcode, IntegrityError # Importe IntegrityError
import os
import hashlib
from datetime import datetime, timedelta

# Configurações
DB_CONFIG = {
    'host': 'localhost',
    'user': 'foodyzeadm',
    'password': 'supfood0017admx',
    'database': 'mygeli',
    'raise_on_warnings': True,
    'autocommit': False
}

REMEMBER_DAYS = 30

class UserRegistrationService:
    def __init__(self, db_config):
        self.db_config = db_config

    def get_db_connection(self):
        try:
            return mysql.connector.connect(**self.db_config)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                raise RuntimeError("Erro de autenticação no banco de dados")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                raise RuntimeError("Banco de dados não existe")
            else:
                raise RuntimeError(f"Erro inesperado de banco: {err}")
            
    def hash_password(self, password: str) -> str:
        try:
            return generate_password_hash(password)
        except Exception as e:
            raise RuntimeError(f"Erro ao gerar hash da senha: {e}")
        
    def create_remember_token(self):
        try:
            selector = os.urandom(16).hex()
            authenticator = os.urandom(32).hex()
            hashed_authenticator = hashlib.sha256(authenticator.encode()).hexdigest()
            return selector, authenticator, hashed_authenticator
        except Exception as e:
            raise RuntimeError(f"Erro ao criar token: {e}")
        
    def register_user(self, nome, telefone, email, senha, confirm_senha, lembrar=False):
        if not nome or not email or not senha:
            raise ValueError("Campos obrigatórios ausentes")
        
        if senha != confirm_senha:
            raise ValueError("As senhas não coincidem")
        
        if len(senha) < 6:
            raise ValueError("A senha deve ter no mínimo 6 caracteres")
        
        senha_hash = self.hash_password(senha)

        cnx = self.get_db_connection()
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
            raise ValueError("Já existe um usuário com esse e-mail")
        except mysql.connector.Error as e:
            cnx.rollback()
            raise RuntimeError(f"Erro ao inserir usuário: {e}")
        finally:
            cursor.close()
            cnx.close()

        result = {"user_id": user_id}

        if lembrar:
            selector, authenticator, hashed_authenticator = self.create_remember_token()
            expires_dt = datetime.utcnow() + timedelta(days=REMEMBER_DAYS)
            expires_str = expires_dt.strftime('%Y-%m-%d %H:%M:%S')

            cnx = self.get_db_connection()
            cursor = cnx.cursor(buffered=True)
            try:
                cursor.execute(
                    "INSERT INTO login_tokens (user_id, selector, hashed_token, expires) VALUES (%s, %s, %s, %s)",
                    (user_id, selector, hashed_authenticator, expires_str)
                )
                cnx.commit()
            except mysql.connector.Error as e:
                cnx.rollback()
                raise RuntimeError(f"Erro ao salvar token de login: {e}")
            finally:
                cursor.close()
                cnx.close()

            result.update({
                "remember_selector": selector,
                "remember_authenticator": authenticator,
                "remember_expires": expires_dt
            })
        
        return result

app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
service = UserRegistrationService(DB_CONFIG)

# NOVA ROTA: Para servir a página principal (index.html)
@app.route('/')
def index():
    return render_template('index.html')

# NOVA ROTA: Para servir arquivos como script.js e style.css
@app.route('/<path:filename>')
def serve_files(filename):
    return send_from_directory('.', filename)

@app.route('/register', methods=['POST'])
def register():
    if 'cadastrar' not in request.form:
        abort(400, "Requisição inválida")

    try:
        nome = request.form.get('nome', '').strip()
        telefone = request.form.get('telefone', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        confirm_senha = request.form.get('confirm-senha', '') 
        lembrar = request.form.get('remember') is not None

        result = service.register_user(nome, telefone, email, senha, confirm_senha, lembrar)

        session.clear()
        session['user_id'] = result["user_id"]

        # Criar uma rota para '/general-page/index' em outro momento
        response = make_response(redirect('/')) # Redirecionando para a home
        if lembrar:
            cookie_value = f"{result['remember_selector']}:{result['remember_authenticator']}"
            response.set_cookie(
                'remember_me',
                cookie_value,
                expires=result["remember_expires"],
                path='/',
                httponly=True,
                secure=False, 
                samesite='Lax'
            )
        return response
    
    except ValueError as ve:
        # Futuramente, passar o erro para o template para exibi-lo na página
        return str(ve), 400
    except RuntimeError as re:
        return str(re), 500
    except Exception as e:
        return f"Erro inesperado: {e}", 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
