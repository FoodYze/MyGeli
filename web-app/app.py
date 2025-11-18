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
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# --- Configurações Comuns ---
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'foodyzeadm'),
    'password': os.getenv('DB_PASS', 'supfood0017admx'),
    'database': os.getenv('DB_NAME', 'mygeli'),
    'raise_on_warnings': True,
    'autocommit': False
}
REMEMBER_DAYS = 30

# --- Configuração API Gemini ---
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai_model = None
try:
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        genai_model = genai.GenerativeModel('gemini-2.5-flash')
        print("Log: API do Gemini configurada com sucesso.")
    else:
        print("AVISO: GOOGLE_API_KEY não encontrada no .env.")
except Exception as e:
    print(f"AVISO: Erro ao configurar Gemini: {e}")

# --- Inicialização do Flask ---
app = Flask(__name__, template_folder='templates', static_folder='static') 
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- Serviços e Helpers de Banco ---
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
        cnx = self.get_db_connection()
        cursor = cnx.cursor()
        try:
            cursor.execute("DELETE FROM login_tokens WHERE user_id = %s", (user_id,))
            cursor.execute(
                "INSERT INTO login_tokens (user_id, selector, hashed_token, expires) VALUES (%s, %s, %s, %s)",
                (user_id, selector, hashed_authenticator, expires_dt)
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

# --- Helpers de Lógica de Estoque ---

def get_nutritional_info_from_api(item_name):
    if not genai_model:
        return None
    try:
        prompt = (
             f"Forneça as informações nutricionais para 100g do alimento '{item_name}'.\n"
             f"Responda APENAS com um objeto JSON contendo as seguintes chaves: "
             f"'valor_energetico_kcal', 'acucares_totais_g', 'acucares_adicionados_g', 'carboidratos_g', "
             f"'proteinas_g', 'gorduras_totais_g', 'gorduras_saturadas_g', 'gorduras_trans_g', "
             f"'fibra_alimentar_g', 'sodio_g'.\n"
             f"Use 0 se não encontrado e null se desconhecido. Exemplo: {{\"valor_energetico_kcal\": 52, ...}}"
        )
        response = genai_model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"Log (Nutrição): Erro ao buscar dados para '{item_name}': {e}")
        return None

def converter_para_base(quantidade, unidade):
    """Converte para a unidade base (Gramas/Mililitros/Unidades)."""
    unidade_lower = unidade.lower()
    try:
        qtd = float(str(quantidade).replace(',', '.'))
    except ValueError:
        return 0, unidade

    if 'kg' in unidade_lower or 'quilos' in unidade_lower: return (qtd * 1000, 'Gramas')
    if 'g' in unidade_lower or 'gramas' in unidade_lower: return (qtd, 'Gramas')
    if 'ml' in unidade_lower or 'mililitros' in unidade_lower: return (qtd, 'Mililitros')
    if 'l' in unidade_lower or 'litros' in unidade_lower: return (qtd * 1000, 'Mililitros')
    if 'unidades' in unidade_lower: return (qtd, 'Unidades')
    return (qtd, unidade.capitalize())

def formatar_exibicao(quantidade, unidade):
    """Formata para exibição amigável (ex: 1500 Gramas -> 1.5 Kg)."""
    try:
        qtd_float = float(quantidade)
        if unidade == 'Gramas' and qtd_float >= 1000: 
            return (qtd_float / 1000, "Kg")
        if unidade == 'Mililitros' and qtd_float >= 1000: 
            return (qtd_float / 1000, "L")
        return (qtd_float, unidade)
    except:
        return (quantidade, unidade)

def _calculate_new_stock_quantity(qtd_estoque, unidade_estoque, qtd_receita, unidade_receita):
    """
    Calcula a nova quantidade e unidade para o estoque após o consumo.
    Lida com conversões inteligentes (Unidade <-> Massa).
    """
    u_est = unidade_estoque.lower()
    u_rec = unidade_receita.lower()
    
    # Fatores de conversão
    fator_estoque = 1
    tipo_estoque = 'unidade'
    if 'kg' in u_est or 'quilo' in u_est: fator_estoque = 1000; tipo_estoque = 'massa'
    elif 'g' in u_est or 'grama' in u_est: fator_estoque = 1; tipo_estoque = 'massa'
    elif 'l' in u_est or 'litro' in u_est: fator_estoque = 1000; tipo_estoque = 'volume'
    elif 'ml' in u_est or 'mililitro' in u_est: fator_estoque = 1; tipo_estoque = 'volume'
    
    fator_receita = 1
    tipo_receita = 'unidade'
    if 'kg' in u_rec or 'quilo' in u_rec: fator_receita = 1000; tipo_receita = 'massa'
    elif 'g' in u_rec or 'grama' in u_rec: fator_receita = 1; tipo_receita = 'massa'
    elif 'l' in u_rec or 'litro' in u_rec: fator_receita = 1000; tipo_receita = 'volume'
    elif 'ml' in u_rec or 'mililitro' in u_rec: fator_receita = 1; tipo_receita = 'volume'
    
    estoque_em_base = 0
    receita_em_base = 0
    
    # Caso 1: Tipos compatíveis
    if tipo_estoque == tipo_receita and tipo_estoque != 'unidade':
        estoque_em_base = float(qtd_estoque) * fator_estoque
        receita_em_base = float(qtd_receita) * fator_receita
    
    # Caso 2: Unidade vs Massa (Estimativa: 1 Unidade = 1000g)
    elif tipo_estoque == 'unidade' and tipo_receita == 'massa':
        peso_medio_unidade = 1000.0 
        estoque_em_base = float(qtd_estoque) * peso_medio_unidade
        receita_em_base = float(qtd_receita) * fator_receita
        tipo_estoque = 'massa' # Passa a tratar como massa
        
    # Caso 3: Unidade vs Unidade
    elif tipo_estoque == 'unidade' and tipo_receita == 'unidade':
        nova_qtd = float(qtd_estoque) - float(qtd_receita)
        if nova_qtd < 0: return None, None
        return nova_qtd, "Unidades"
    
    else:
        return None, None # Incompatível

    # Subtração na unidade base
    nova_qtd_base = estoque_em_base - receita_em_base
    
    if nova_qtd_base < 0: return None, None # Insuficiente
    
    # Decide unidade final
    if nova_qtd_base >= 1000:
        return nova_qtd_base / 1000, ("Quilos (Kg)" if tipo_estoque == 'massa' else "Litros (L)")
    else:
        return nova_qtd_base, ("Gramas (g)" if tipo_estoque == 'massa' else "Mililitros (ml)")

def _execute_stock_update_web(user_id, recipe_data):
    """Lógica para atualização em lote via chatbot."""
    if not recipe_data or not recipe_data.get("ingredientes"): raise ValueError("Dados inválidos.")
    cnx, cursor = None, None
    try:
        cnx = db_service.get_db_connection(); cursor = cnx.cursor(dictionary=True)
        for item in recipe_data.get("ingredientes", []):
            cursor.execute("SELECT * FROM produtos WHERE LOWER(nome_produto)=LOWER(%s) AND user_id=%s", (item['nome'], user_id))
            row = cursor.fetchone()
            if row:
                nq, nu = _calculate_new_stock_quantity(row['quantidade_produto'], row['tipo_volume'], item['quantidade'], item.get('unidade', 'Unidades'))
                if nq is not None:
                    if nq <= 0.001: cursor.execute("DELETE FROM produtos WHERE id_produto=%s", (row['id_produto'],))
                    else: cursor.execute("UPDATE produtos SET quantidade_produto=%s, tipo_volume=%s WHERE id_produto=%s", (nq, nu, row['id_produto']))
                    cursor.execute("INSERT INTO historico_uso (id_user, nome_receita, nome_ingrediente, quantidade_usada, unidade_medida) VALUES (%s,%s,%s,%s,%s)", (user_id, recipe_data.get("titulo"), item['nome'], item['quantidade'], item.get('unidade')))
        cnx.commit()
    except mysql.connector.Error as e:
        if cnx: cnx.rollback()
        raise RuntimeError(f"BD Error: {e}")
    finally:
        if cursor: cursor.close()
        if cnx: cnx.close()

# --- Rotas ---

@app.route('/')
def home():
    return redirect(url_for('general_page')) if 'user_id' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET': return render_template('login-page.html')
    try:
        email, senha = request.form.get('email', '').strip(), request.form.get('senha', '')
        cnx = db_service.get_db_connection(); cursor = cnx.cursor(dictionary=True)
        cursor.execute("SELECT id, email, senha FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close(); cnx.close()
        
        if not user or not check_password_hash(user['senha'], senha): raise ValueError("Credenciais inválidas.")
        session['user_id'] = user['id']
        resp = make_response(redirect(url_for('general_page')))
        if request.form.get('lembrar_de_mim'):
            sel, auth, h_auth = db_service.create_remember_token()
            db_service.save_remember_token(user['id'], sel, h_auth)
            resp.set_cookie('remember_me', f"{sel}:{auth}", expires=datetime.utcnow()+timedelta(days=REMEMBER_DAYS))
        return resp
    except Exception as e: return render_template('login-page.html', error=str(e)), 400

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET': return render_template('register-page.html')
    try:
        nome, email, senha, conf = request.form.get('nome'), request.form.get('email'), request.form.get('senha'), request.form.get('confirm-senha')
        if senha != conf or len(senha) < 6: raise ValueError("Senha inválida.")
        
        cnx = db_service.get_db_connection(); cursor = cnx.cursor()
        try:
            cursor.execute("INSERT INTO usuarios (nome, telefone, email, senha) VALUES (%s, %s, %s, %s)", 
                           (nome, request.form.get('telefone'), email, generate_password_hash(senha)))
            cnx.commit(); uid = cursor.lastrowid
        except IntegrityError: raise ValueError("E-mail já existe.")
        finally: cursor.close(); cnx.close()
        
        session['user_id'] = uid
        return redirect(url_for('general_page'))
    except Exception as e: return render_template('register-page.html', error=str(e)), 400

@app.route('/general-page')
def general_page():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    data = {"total_items": 0, "low_stock_count": 0, "total_recipes": 0, "highest_stock_item": "Nenhum", "user_name": ""}
    
    try:
        cnx = db_service.get_db_connection(); cursor = cnx.cursor(dictionary=True)
        cursor.execute("SELECT nome FROM usuarios WHERE id=%s", (uid,)); u = cursor.fetchone()
        if u: data["user_name"] = u['nome'].split()[0]
        
        cursor.execute("SELECT * FROM produtos WHERE user_id=%s", (uid,))
        prods = cursor.fetchall()
        data["total_items"] = len(prods)
        max_q = -1
        for p in prods:
            q, u = float(p['quantidade_produto']), p['tipo_volume']
            if (u=='Unidades' and q<=2) or (u in ['Gramas','Mililitros'] and q<=500): data["low_stock_count"] += 1
            if q > max_q: max_q = q; data["highest_stock_item"] = p['nome_produto']
            
        cursor.execute("SELECT COUNT(*) as t FROM receitas WHERE idusuario=%s", (uid,)); r = cursor.fetchone()
        if r: data["total_recipes"] = r['t']
    except Exception as e: print(e)
    finally: 
        if 'cursor' in locals() and cursor: cursor.close()
        if 'cnx' in locals() and cnx: cnx.close()
        
    return render_template('general-page.html', dashboard_json=json.dumps(data))

@app.route('/chatbot')
def chatbot_page():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    data = {"stock": {}, "preferences": "Nenhuma preferência."}
    try:
        cnx = db_service.get_db_connection(); cursor = cnx.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produtos WHERE user_id=%s", (uid,))
        for r in cursor.fetchall(): data["stock"][r['nome_produto']] = f"{r['quantidade_produto']} {r['tipo_volume']}"
        cursor.execute("SELECT preferencias FROM usuarios WHERE id=%s", (uid,)); p = cursor.fetchone()
        if p and p['preferencias']: data["preferences"] = p['preferencias']
    except Exception: pass
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'cnx' in locals() and cnx: cnx.close()
    return render_template('chatbot-page.html', page_data_json=json.dumps(data))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']; msg = None
    if request.method == 'POST':
        prefs = json.dumps({k: request.form.get(k,'') for k in ['allergies','dietary_restrictions','other']})
        try: user_profile_repo.update_user_preferences(uid, prefs); msg="Salvo!"
        except: pass
    
    udata = user_profile_repo.get_user_details_by_id(uid)
    uprefs = json.loads(udata.get('preferencias') or '{}') if udata.get('preferencias') else {'allergies':'','dietary_restrictions':'','other':''}
    return render_template('profile-page.html', user=udata, user_preferences=uprefs, success_message=msg)

@app.route('/recipes')
def recipes_page():
    if 'user_id' not in session: return redirect(url_for('login'))
    return chatbot_page()

# --- ROTAS DE ESTOQUE ---

@app.route('/estoque-page')
def estoque_page():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('estoque-page.html')

@app.route('/api/stock', methods=['GET'])
def get_stock_data():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    try:
        cnx = db_service.get_db_connection()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("SELECT id_produto, nome_produto, quantidade_produto, tipo_volume FROM produtos WHERE user_id=%s ORDER BY nome_produto", (session['user_id'],))
        items = []
        for row in cursor.fetchall():
            qtd_fmt, unit_fmt = formatar_exibicao(row['quantidade_produto'], row['tipo_volume'])
            items.append({
                "id": row['id_produto'],
                "name": row['nome_produto'],
                "quantity": qtd_fmt, 
                "unit": unit_fmt,
                "raw_quantity": float(row['quantidade_produto']),
                "raw_unit": row['tipo_volume']
            })
        return jsonify(items)
    except Exception as e: return jsonify({"error": str(e)}), 500
    finally: 
        if 'cursor' in locals() and cursor: cursor.close()
        if 'cnx' in locals() and cnx: cnx.close()

@app.route('/api/stock/manage', methods=['POST'])
def manage_stock():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    action = data.get('action')
    uid = session['user_id']
    
    cnx = None
    cursor = None
    try:
        cnx = db_service.get_db_connection()
        cursor = cnx.cursor(dictionary=True)
        
        if action == 'delete':
            item_id = data.get('id')
            cursor.execute("DELETE FROM produtos WHERE id_produto=%s AND user_id=%s", (item_id, uid))
            cnx.commit()
            return jsonify({"message": "Item excluído."})

        # AÇÃO CONSUMIR
        elif action == 'consumir':
            item_name = data.get('item').strip()
            qty_consumida = float(data.get('quantidade'))
            unit_consumida = data.get('unidade')

            cursor.execute("SELECT * FROM produtos WHERE nome_produto = %s AND user_id = %s", (item_name, uid))
            produto_estoque = cursor.fetchone()

            if not produto_estoque:
                return jsonify({"error": f"Item '{item_name}' não encontrado."}), 404
            
            qtd_atual = float(produto_estoque['quantidade_produto'])
            unidade_atual = produto_estoque['tipo_volume']

            nova_qtd, nova_unidade = _calculate_new_stock_quantity(qtd_atual, unidade_atual, qty_consumida, unit_consumida)

            if nova_qtd is None:
                return jsonify({"error": f"Quantidade insuficiente ou unidades incompatíveis."}), 400
            
            if nova_qtd <= 0.001:
                cursor.execute("DELETE FROM produtos WHERE id_produto = %s", (produto_estoque['id_produto'],))
                msg = "Item consumido totalmente."
            else:
                cursor.execute("UPDATE produtos SET quantidade_produto = %s, tipo_volume = %s WHERE id_produto = %s", 
                               (nova_qtd, nova_unidade, produto_estoque['id_produto']))
                msg = "Estoque atualizado."
            
            cursor.execute("INSERT INTO historico_uso (id_user, nome_receita, nome_ingrediente, quantidade_usada, unidade_medida) VALUES (%s, %s, %s, %s, %s)", 
                           (uid, "Consumo Manual", item_name, qty_consumida, unit_consumida))

            cnx.commit()
            return jsonify({"message": msg})

        # ADICIONAR / ATUALIZAR
        else:
            item_name = data.get('item').strip().capitalize()
            qty_input = data.get('quantidade')
            unit_input = data.get('unidade')
            qty_base, unit_base = converter_para_base(qty_input, unit_input)
            
            if action == 'atualizar' and data.get('id'):
                cursor.execute("UPDATE produtos SET nome_produto=%s, quantidade_produto=%s, tipo_volume=%s WHERE id_produto=%s AND user_id=%s", 
                               (item_name, qty_base, unit_base, data.get('id'), uid))
            else:
                cursor.execute("SELECT * FROM produtos WHERE nome_produto=%s AND user_id=%s", (item_name, uid))
                existing = cursor.fetchone()
                
                if existing:
                    if existing['tipo_volume'] == unit_base:
                        new_qty = float(existing['quantidade_produto']) + qty_base
                        cursor.execute("UPDATE produtos SET quantidade_produto=%s WHERE id_produto=%s", (new_qty, existing['id_produto']))
                    else:
                        return jsonify({"error": f"Unidade incompatível! O item já existe em '{existing['tipo_volume']}'."}), 400
                else:
                    nutri = get_nutritional_info_from_api(item_name) or {}
                    keys_nutri = ["valor_energetico_kcal", "acucares_totais_g", "acucares_adicionados_g", "carboidratos_g", "proteinas_g", "gorduras_totais_g", "gorduras_saturadas_g", "fibra_alimentar_g", "sodio_g"]
                    sql = f"""INSERT INTO produtos (user_id, nome_produto, quantidade_produto, tipo_volume, {', '.join(keys_nutri)}) VALUES (%s, %s, %s, %s, {', '.join(['%s']*len(keys_nutri))})"""
                    vals = [uid, item_name, qty_base, unit_base] + [nutri.get(k) for k in keys_nutri]
                    cursor.execute(sql, vals)
            
            cnx.commit()
            return jsonify({"message": "Estoque atualizado!"})

    except Exception as e:
        if cnx: cnx.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if cnx: cnx.close()

@app.route('/api/update_stock', methods=['POST'])
def update_stock_api():
    if 'user_id' not in session: return jsonify({"error": "Não autorizado"}), 401
    try:
        _execute_stock_update_web(session['user_id'], request.json)
        return jsonify({"message": "Estoque atualizado via receita!"})
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)