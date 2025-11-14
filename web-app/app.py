from flask import Flask, request, redirect, session, make_response, abort, render_template, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import errorcode, IntegrityError
import os
import traceback
import re
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

# --- Inicialização do Flask ---
app = Flask(__name__, template_folder='templates', static_folder='static') 
# Define explicitamente as pastas

app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- Serviços ---
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
            # Remove tokens antigos do mesmo usuário para evitar acúmulo
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
        return render_template('register-page.html')

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

    # --- Caminhos nos Erros ---
    except ValueError as ve:
        return render_template('register-page.html', error=str(ve)), 400 # Caminho correto
    except RuntimeError as re:
        return render_template('register-page.html', error=str(re)), 500 # Caminho correto
    except Exception as e:
        print(f"Erro inesperado no registro: {e}") 
        return render_template('register-page.html', error="Erro inesperado. Tente novamente."), 500 # Caminho correto


# --- Renderizar Template na Página Geral ---
@app.route('/general-page')
def general_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    dashboard_data = {
        "total_items": 0,
        "low_stock_count": 0,
        "total_recipes": 0,
        "highest_stock_item": "Nenhum",
        "user_name": "" # Vamos adicionar o nome do usuário
    }
    
    cnx = None
    cursor = None
    
    try:
        cnx = db_service.get_db_connection()
        cursor = cnx.cursor(dictionary=True)

        # 1. Buscar dados do usuário (Nome)
        cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            # Pega o primeiro nome
            dashboard_data["user_name"] = user['nome'].split(' ')[0]

        # 2. Buscar dados de Produtos (para 3 métricas)
        query_produtos = "SELECT nome_produto, quantidade_produto, tipo_volume FROM produtos WHERE user_id = %s"
        cursor.execute(query_produtos, (user_id,))
        produtos = cursor.fetchall()
        
        dashboard_data["total_items"] = len(produtos)
        
        if produtos:
            low_stock_count = 0
            max_qty = -1
            highest_item = "Nenhum"
            
            for item in produtos:
                qty = float(item['quantidade_produto'])
                unit = item['tipo_volume']
                
                # Lógica de estoque baixo (baseada no seu gui3.py)
                if (unit == 'Unidades' and qty <= 2) or (unit in ['Gramas', 'Mililitros'] and qty <= 500):
                    low_stock_count += 1
                
                # Lógica de item com maior quantidade (ignora unidades por simplicidade)
                if qty > max_qty:
                    max_qty = qty
                    highest_item = item['nome_produto']
                    
            dashboard_data["low_stock_count"] = low_stock_count
            dashboard_data["highest_stock_item"] = highest_item

        # 3. Buscar dados de Receitas
        query_receitas = "SELECT COUNT(*) as total FROM receitas WHERE idusuario = %s"
        cursor.execute(query_receitas, (user_id,))
        receitas = cursor.fetchone()
        if receitas:
            dashboard_data["total_recipes"] = receitas['total']
            
    except mysql.connector.Error as err:
        print(f"Erro ao buscar dados do dashboard: {err}")
        # A página carrega, mas com dados zerados
    finally:
        if cursor:
            cursor.close()
        if cnx:
            cnx.close()
            
    # Converte o dicionário para uma string JSON
    dashboard_json = json.dumps(dashboard_data)

    return render_template('general-page.html', dashboard_json=dashboard_json)

@app.route('/chatbot') # Defines the URL, e.g., http://127.0.0.1:5000/chatbot
def chatbot_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']

    stock_dict = {}
    user_prefs_string = "Nenhuma preferência informada."
    
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

        query_prefs = "SELECT preferencias FROM usuarios WHERE id = %s"
        cursor.execute(query_prefs, (user_id,))
        prefs_row = cursor.fetchone()
        
        if prefs_row and prefs_row['preferencias']:
            user_prefs_string = prefs_row['preferencias']
            
    except mysql.connector.Error as err:
        print(f"Erro ao buscar estoque do usuário {user_id}: {err}")
    finally:
        if cursor:
            cursor.close()
        if cnx:
            cnx.close()
            
    page_data = {
        "stock": stock_dict,
        "preferences": user_prefs_string
    }
    page_data_json = json.dumps(page_data)
    
    return render_template('chatbot-page.html', page_data_json=page_data_json)

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
        # Tenta carregar o JSON, se falhar, usa o padrão
        try:
            user_preferences = json.loads(user_data['preferencias'])
        except json.JSONDecodeError:
            pass # Mantém o padrão
    
    return render_template(
        'profile-page.html', 
        user=user_data, 
        user_preferences=user_preferences,
        success_message=success_message
    )

# --- NOVA ROTA ADICIONADA ---
@app.route('/recipes')
def recipes_page():
    # 1. Verificação de Autenticação (padrão)
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # 2. Buscar Estoque e Preferências
    stock_dict = {}
    user_preferences_json = '{}' # Padrão é um JSON vazio
    cnx = None
    cursor = None
    
    try:
        # Pega a conexão do serviço
        cnx = db_service.get_db_connection()
        cursor = cnx.cursor(dictionary=True)
        
        # --- Lógica do Estoque (copiada de /chatbot) ---
        query_stock = "SELECT nome_produto, quantidade_produto, tipo_volume from produtos WHERE user_id = %s"
        cursor.execute(query_stock, (user_id,))
        
        for row in cursor.fetchall():
            item_name = row['nome_produto']
            item_qty = row['quantidade_produto']
            item_unit = row['tipo_volume']
            stock_dict[item_name] = f"{item_qty} {item_unit}"
        
        # --- Lógica das Preferências (baseada em /profile) ---
        query_prefs = "SELECT preferencias FROM usuarios WHERE id = %s"
        cursor.execute(query_prefs, (user_id,))
        user_prefs_row = cursor.fetchone()
        
        if user_prefs_row and user_prefs_row['preferencias']:
            user_preferences_json = user_prefs_row['preferencias']
            
    except mysql.connector.Error as err:
        print(f"Erro ao buscar dados para receitas (usuário {user_id}): {err}")
        # A página ainda deve carregar, mas com dados vazios
        stock_dict = {}
        user_preferences_json = '{}'
    except Exception as e:
        print(f"Erro inesperado ao buscar dados para receitas: {e}")
        stock_dict = {}
        user_preferences_json = '{}'
    finally:
        if cursor:
            cursor.close()
        if cnx:
            cnx.close()
            
    # 4. Preparar dados para o template
    stock_json = json.dumps(stock_dict)
    
    # 5. Renderizar o template
    return render_template(
        'recipes.html', 
        user_stock_json=stock_json,
        user_preferences_json=user_preferences_json
    )
# --- FIM DA NOVA ROTA ---

def _parse_ingredients_from_recipe_web(recipe_text):
    """Extrai ingredientes marcados com '(do estoque)'."""
    # Padrão para encontrar QUALQUER linha que termine com "(do estoque)"
    pattern_linha_estoque = re.compile(r"^\s*(.*?)\s+\(do estoque\)", re.MULTILINE | re.IGNORECASE)
    matches = pattern_linha_estoque.findall(recipe_text)
    
    parsed_ingredients = []
    for item_str in matches:
        # Padrão para separar número, unidade (opcional) e o resto que é o nome
        match_componentes = re.match(r"^\s*([\d\.,]+)\s*(\w*)\s*(?:de\s)?(.*)", item_str.strip(), re.IGNORECASE)
        
        if match_componentes:
            try:
                quantidade_str = match_componentes.group(1).replace(',', '.')
                quantidade = float(quantidade_str)
                unidade = match_componentes.group(2).strip()
                nome = match_componentes.group(3).strip()

                if not nome:
                    nome = unidade
                    unidade = 'unidade(s)'

                if nome.lower().startswith('de '):
                    nome = nome[3:]

                parsed_ingredients.append({"nome": nome, "quantidade": quantidade, "unidade": unidade})

            except (ValueError, IndexError):
                print(f"AVISO (Web): Não foi possível extrair a quantidade da linha: '{item_str}'")
                continue

    print(f"DEBUG (Web): Ingredientes para baixa extraídos: {parsed_ingredients}")
    return parsed_ingredients

def _execute_stock_update_web(user_id, recipe_data):
    """Dá baixa no estoque e salva no histórico."""
    if not recipe_data:
        raise ValueError("Dados da receita estão vazios.")
        
    recipe_title = recipe_data.get("titulo", "Receita não identificada")
    ingredients_to_update = recipe_data.get("ingredientes", [])
    
    if not ingredients_to_update:
         raise ValueError("Nenhum ingrediente '(do estoque)' foi encontrado na receita.")

    cnx, cursor = None, None
    try:
        cnx = db_service.get_db_connection() # Pega uma nova conexão
        cursor = cnx.cursor()
        
        for item in ingredients_to_update:
            nome = item['nome']
            quantidade_a_remover = item['quantidade']
            unidade = item.get('unidade', '')
            
            # 1. ATUALIZA O ESTOQUE
            sql_update_stock = """
                UPDATE produtos 
                SET quantidade_produto = quantidade_produto - %s 
                WHERE LOWER(nome_produto) = LOWER(%s) AND user_id = %s AND quantidade_produto >= %s
            """
            cursor.execute(sql_update_stock, (quantidade_a_remover, nome, user_id, quantidade_a_remover))
            
            # 2. REGISTRA NO HISTÓRICO
            sql_insert_history = """
                INSERT INTO historico_uso (id_user, nome_receita, nome_ingrediente, quantidade_usada, unidade_medida)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql_insert_history, (user_id, recipe_title, nome, quantidade_a_remover, unidade))
        
        # 3. LIMPA ITENS ZERADOS
        sql_delete_zeros = "DELETE FROM produtos WHERE user_id = %s AND quantidade_produto <= 0"
        cursor.execute(sql_delete_zeros, (user_id,))
        
        cnx.commit()
        print(f"Log (Web): Estoque atualizado para user_id {user_id}.")
        
    except mysql.connector.Error as e:
        print(f"ERRO SQL (Web) ao atualizar estoque: {e}")
        if cnx: cnx.rollback()
        raise RuntimeError(f"Erro de Banco de Dados: {e}") # Re-levanta o erro
    finally:
        if cursor: cursor.close()
        if cnx: cnx.close()
        
@app.route('/api/update_stock', methods=['POST'])
def update_stock_route():
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    user_id = session['user_id']
    recipe_data = request.json
    
    if not recipe_data or 'ingredientes' not in recipe_data:
        return jsonify({"error": "Dados da receita inválidos."}), 400
        
    try:
        _execute_stock_update_web(user_id, recipe_data)
        # Se chegou aqui, deu certo
        return jsonify({"message": "Perfeito! Já dei baixa dos ingredientes no seu estoque e registrei no seu histórico. Bom apetite!"})
        
    except Exception as e:
        print(f"ERRO CRÍTICO na rota /api/update_stock: {e}")
        traceback.print_exc()
        # Envia o erro exato para o frontend
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
