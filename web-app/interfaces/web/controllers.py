# Substitua o conteúdo de interfaces/web/controllers.py por este

from flask import request, redirect, session, make_response, render_template, url_for
from application.auth_service import AuthService
# Importações corrigidas e completas
from infrastructure.database_repository import MySQLConnection, AuthRepository
from infrastructure.auth_token_repository import RememberMeTokenRepository
from config.settings import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, REMEMBER_DAYS
from datetime import datetime, timedelta

# Configuração da camada de Infraestrutura
# Agora a conexão é instanciada corretamente, passando os parâmetros
db_connection = MySQLConnection(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
auth_repo = AuthRepository(db_connection)
token_repo = RememberMeTokenRepository(db_connection)

# Configuração da camada de aplicação
auth_service = AuthService(auth_repo, token_repo)

def init_app_routes(app):
    @app.route('/')
    def index():
        # Verifica se o usuário já tem uma sessão ativa
        if 'user_id' in session:
            # Se estiver logado, vai para a página geral
            return redirect(url_for('general_page'))
        else:
            # Se não estiver logado, vai para a página de login
            return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('login-page.html')
        
        try:
            email = request.form.get('email', '').strip()
            senha = request.form.get('senha', '')
            lembrar = request.form.get('lembrar_de_mim') is not None

            user_id = auth_service.login_user(email, senha)

            session.clear()
            session['user_id'] = user_id

            # O redirect correto é para a função que renderiza a página
            response = make_response(redirect(url_for('general_page')))

            if lembrar:
                selector, authenticator = auth_service.create_and_save_remember_token(user_id)
                cookie_expires = datetime.utcnow() + timedelta(days=REMEMBER_DAYS)
                cookie_value = f"{selector}:{authenticator}"
                response.set_cookie('remember_me', cookie_value, expires=cookie_expires, httponly=True)

            return response
        
        except ValueError as ve:
            return render_template('login-page.html', error=str(ve)), 400
        except RuntimeError as re:
            return render_template('login-page.html', error=str(re)), 500
        except Exception as e:
            # É bom logar o erro 'e' aqui para depuração
            return render_template('login-page.html', error="Ocorreu um erro inesperado. Tente novamente."), 500
            
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'GET':
            return render_template('register-page.html')
        
        try:
            name = request.form.get('nome', '').strip()
            phone = request.form.get('telefone', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('senha', '')
            confirm_password = request.form.get('confirm-senha', '')

            user_id = auth_service.register_user(name, phone, email, password, confirm_password)

            session.clear()
            session['user_id'] = user_id
            
            # O redirect correto é para a função que renderiza a página
            response = make_response(redirect(url_for('general_page')))

            if request.form.get('remember') is not None:
                selector, authenticator = auth_service.create_and_save_remember_token(user_id)
                cookie_expires = datetime.utcnow() + timedelta(days=REMEMBER_DAYS)
                cookie_value = f"{selector}:{authenticator}"
                response.set_cookie('remember_me', cookie_value, expires=cookie_expires, httponly=True)
                
            return response

        except ValueError as ve:
            return render_template('register-page.html', error=str(ve)), 400
        except RuntimeError as re:
            return render_template('register-page.html', error=str(re)), 500
        except Exception as e:
            # É bom logar o erro 'e' aqui para depuração
            return render_template('register-page.html', error="Ocorreu um erro inesperado. Tente novamente."), 500
            
    # Rota corrigida para a página geral
    @app.route('/general-page')
    def general_page():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Aqui você pode carregar dados do usuário se necessário
        # e passar para o template.
        return render_template('general-page.html')