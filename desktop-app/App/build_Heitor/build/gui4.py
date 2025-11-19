import customtkinter as ctk
from datetime import datetime
from pathlib import Path
import mysql.connector
from mysql.connector import Error
import google.generativeai as genai
import os
import re
from tkinter import messagebox
from PIL import Image
from collections import defaultdict
import subprocess
import sys
import threading
import hashlib
from dotenv import load_dotenv

# Tenta importar o gerenciador de sessão
try:
    from session_manager import SessionManager
except ImportError:
    print("Erro: session_manager.py não encontrado.")
    SessionManager = None

import logging
logging.basicConfig(level=logging.ERROR)

load_dotenv()

OUTPUT_PATH = Path(__file__).parent
ASSETS_GERAL_PATH = OUTPUT_PATH / "assets" / "geral"
SETA_IMAGE_PATH = ASSETS_GERAL_PATH / "seta.png"

lista_compras_data = None
CATEGORIAS_COMPRA = [
    "Hortifruti", "Mercearia", "Proteínas", "Laticínios", 
    "Padaria", "Bebidas", "Congelados", "Outros"
]
UNIDADES_ESTOQUE = ["Unidades", "Quilos (Kg)", "Gramas (g)", "Litros (L)", "Mililitros (ml)"]

lista_compras_inner_frame = None
window = None

# Credenciais do Banco
db_host = os.getenv('DB_HOST', "localhost")
db_name = os.getenv('DB_NAME', "mygeli")
db_usuario = os.getenv('DB_USER', "foodyzeadm")
db_senha = os.getenv('DB_PASS', "supfood0017admx")

ID_USUARIO_ATUAL = None
model = None

# Configuração Gemini
try:
    try:
        from gui0 import GOOGLE_API_KEY
    except ImportError:
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    if GOOGLE_API_KEY and GOOGLE_API_KEY != "SUA_CHAVE_API_AQUI":
        genai.configure(api_key=GOOGLE_API_KEY)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        model = genai.GenerativeModel('gemini-2.5-flash', safety_settings=safety_settings)
        print("Log: API do Gemini configurada.")
    else:
        print("AVISO: GOOGLE_API_KEY não encontrada.")
except Exception as e:
    print(f"AVISO: Erro ao configurar Gemini: {e}")

# --- Funções de Banco de Dados ---

def conectar_mysql():
    try:
        return mysql.connector.connect(host=db_host, database=db_name, user=db_usuario, password=db_senha)
    except Error as e:
        messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao banco de dados:\n{e}")
        return None

def obter_usuario_logado():
    if not SessionManager:
        return None

    manager = SessionManager()
    token_data = manager.get_token()
    if not token_data: 
        return None

    selector = token_data.get("selector")
    authenticator = token_data.get("authenticator")
    if not selector or not authenticator: 
        return None

    conexao = conectar_mysql()
    if not conexao: return None

    user_id_encontrado = None
    try:
        cursor = conexao.cursor(dictionary=True)
        query = """
            SELECT t.user_id, t.hashed_token, t.expires
            FROM login_tokens t
            WHERE t.selector = %s
        """
        cursor.execute(query, (selector,))
        record = cursor.fetchone()
        
        if record:
            if record['expires'] >= datetime.now():
                hashed_auth_check = hashlib.sha256(authenticator.encode()).hexdigest()
                if hashed_auth_check == record['hashed_token']:
                    user_id_encontrado = record['user_id']
                    print(f"Log: Usuário autenticado via token. ID: {user_id_encontrado}")
                else:
                    print("Log: Token inválido.")
            else:
                print("Log: Token expirado.")
    except Error as e:
        print(f"Erro ao verificar sessão: {e}")
    finally:
        if conexao.is_connected():
            conexao.close()
            
    return user_id_encontrado

def buscar_inventario_usuario(conexao, id_usuario):
    # Busca INVENTARIO (Tabela 'produtos' usa 'user_id')
    if not conexao or not conexao.is_connected(): return []
    try:
        cursor = conexao.cursor(dictionary=True)
        query = """
            SELECT nome_produto AS nome, quantidade_produto AS quantidade, tipo_volume AS unidade 
            FROM produtos 
            WHERE user_id = %s
        """
        cursor.execute(query, (id_usuario,))
        return cursor.fetchall()
    except Error as e:
        messagebox.showerror("Erro de BD", f"Não foi possível buscar inventário:\n{e}")
        return []

def buscar_historico_uso(conexao, id_usuario):
    # Busca HISTORICO (Tabela 'historico_uso' usa 'id_user')
    if not conexao or not conexao.is_connected(): return []
    try:
        cursor = conexao.cursor(dictionary=True)
        query = """
            SELECT nome_ingrediente, COUNT(*) as frequencia 
            FROM historico_uso 
            WHERE id_user = %s
            GROUP BY nome_ingrediente 
            ORDER BY frequencia DESC 
            LIMIT 15
        """
        cursor.execute(query, (id_usuario,))
        resultados = cursor.fetchall()
        print(f"Log: Itens encontrados no histórico para ID {id_usuario}: {len(resultados)}")
        return [item['nome_ingrediente'] for item in resultados]
    except Error as e:
        print(f"Log: Erro ao buscar histórico com id_user: {e}")
        return []

# --- Navegação ---

def go_to_gui1():
    if window: window.destroy()
    try:
        subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui1.py")])
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao abrir tela inicial: {e}")

# --- Lógica da IA ---

def formatar_resposta_gemini(texto_gemini):
    if not texto_gemini: return []
    itens_formatados = []
    padrao = re.compile(
        r'^\s*[\*\-]?\s*'
        r'(?P<nome>.+?)\s*-\s*'
        r'(?P<quantidade>[\d.,]+)\s*'
        r'(?P<unidade>[a-zA-ZáéíóúÁÉÍÓÚçÇ\s/]+)\s*-\s*'
        r'(?P<categoria>.+?)\s*-\s*'
        r'(?P<preco>R\$\s*[\d.,]+)\s*$', re.IGNORECASE | re.MULTILINE
    )
    for linha in texto_gemini.split('\n'):
        match = padrao.search(linha.strip())
        if match:
            try:
                nome = match.group('nome').strip(); quantidade_str = match.group('quantidade').replace(',', '.').strip()
                unidade = match.group('unidade').strip(); categoria = match.group('categoria').strip()
                preco = match.group('preco').strip(); quantidade = float(quantidade_str)
                if quantidade.is_integer(): quantidade = int(quantidade)
                if categoria not in CATEGORIAS_COMPRA: categoria = "Outros"
                itens_formatados.append({"nome": nome, "quantidade": quantidade, "unidade": unidade, "categoria": categoria, "preco": preco})
            except (ValueError, IndexError): pass
    return itens_formatados

def recomendar_produtos_com_gemini(inventario, historico, categorias_validas):
    if not model: return []
    
    try:
        inventario_str = ", ".join([f"{item['nome']} ({item['quantidade']} {item['unidade']})" for item in inventario]) if inventario else "Nenhum"
        historico_str = ", ".join(historico) if historico else "Nenhum"
        categorias_str = ", ".join(categorias_validas)
        
        print(f"Log IA -> Inventário: {inventario_str}")
        print(f"Log IA -> Histórico: {historico_str}")

        # --- PROMPT ATUALIZADO E MAIS AGRESSIVO ---
        prompt = f"""
        Você é um assistente de gestão de estoque doméstico.
        
        Dados do Usuário:
        - Inventário Atual: {inventario_str}
        - Histórico de Consumo (Itens Favoritos): {historico_str}

        Sua tarefa: Criar uma lista de compras para repor o estoque.

        REGRAS DE OURO (IMPORTANTE):
        1. **Prioridade Máxima ao Histórico:** Se um item aparece no 'Histórico de Consumo', o usuário usa muito. Você DEVE sugerir a compra dele para garantir um estoque seguro, a menos que a quantidade atual já seja exagerada (ex: acima de 5kg ou 20 unidades).
           - Exemplo: Se tem 10 Maracujás e está no histórico, sugira comprar mais 6. O usuário quer estocar.
           - Exemplo: Se tem 500g de Frango e está no histórico, isso é pouco. Sugira comprar mais 1kg.
        
        2. **Limites de Estoque Baixo (Geral):** Para itens que NÃO estão no histórico, sugira compra se tiver:
           - Menos de 5 Unidades.
           - Menos de 1 Kg (1000g).
           - Menos de 1 Litro.

        3. **Não Alucine:** Não invente produtos que não estão nem no inventário nem no histórico. Trabalhe apenas com os dados fornecidos.

        Formatação Obrigatória:
        - Formate CADA item EXATAMENTE assim: Nome do Produto - Quantidade Sugerida Unidade - Categoria - R$ Preço Médio
        - Exemplo: * Frango - 1 Kg - Proteínas - R$ 20,00
        - Exemplo: * Maracuja - 6 Unidades - Hortifruti - R$ 8,00
        
        Se tudo estiver com estoque EXTREMAMENTE alto (ex: 50kg de tudo), retorne vazio.
        """
        response = model.generate_content(prompt)
        return formatar_resposta_gemini(response.text)

    except Exception as e:
        messagebox.showerror("Erro de IA", f"Não foi possível gerar sugestões.\n\nDetalhe: {e}")
        return []

def buscar_produtos_sugeridos():
    if ID_USUARIO_ATUAL is None:
        print("Log: ID do usuário não identificado. Impossível gerar sugestões personalizadas.")
        return []

    conexao = conectar_mysql()
    if not conexao: return []
    
    try:
        # Passa o ID logado para as funções
        inventario_atual = buscar_inventario_usuario(conexao, ID_USUARIO_ATUAL)
        historico_uso = buscar_historico_uso(conexao, ID_USUARIO_ATUAL)

        if (inventario_atual or historico_uso) and model:
            print(f"Log: Dados encontrados para usuário {ID_USUARIO_ATUAL}. Gerando sugestões...")
            return recomendar_produtos_com_gemini(inventario_atual, historico_uso, CATEGORIAS_COMPRA)
        else:
            print("Log: Nenhum dado de inventário ou histórico para gerar sugestões.")
            return []
    finally:
        if conexao.is_connected():
            conexao.close()

# --- Interface Gráfica ---

def carregar_sugestoes_em_background():
    global lista_compras_data
    sugestoes = buscar_produtos_sugeridos()
    lista_compras_data = sugestoes
    window.after(0, carregar_lista_compras)

def criar_item_lista(parent, produto):
    item_frame = ctk.CTkFrame(parent, height=55, fg_color="#3B82F6", corner_radius=10); item_frame.pack(fill="x", padx=5, pady=(0, 5))
    remover_btn = ctk.CTkButton(item_frame, text="X", width=28, height=28, font=ctk.CTkFont(size=11, weight="bold"), fg_color="#d32f2f", hover_color="#b71c1c", command=lambda item=produto: remover_item(item)); remover_btn.pack(side="right", padx=(5, 10), pady=10)
    preco_label = ctk.CTkLabel(item_frame, text=produto.get("preco", "N/D"), font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFFFFF", anchor="e", width=80); preco_label.pack(side="right", padx=(5, 5))
    quantidade_label = ctk.CTkLabel(item_frame, text=f"{produto['quantidade']} {produto['unidade']}", font=ctk.CTkFont(size=12), anchor="e"); quantidade_label.pack(side="right", padx=(0, 5), pady=10)
    checkbox_var = ctk.BooleanVar(); checkbox = ctk.CTkCheckBox(item_frame, text="", variable=checkbox_var, width=20); checkbox.pack(side="left", padx=(10, 5), pady=10)
    nome_label = ctk.CTkLabel(item_frame, text=produto["nome"], font=ctk.CTkFont(size=14, weight="bold"), anchor="w"); nome_label.pack(side="left", padx=(0, 10), pady=10, fill="x", expand=True)
    produto["checkbox_var"] = checkbox_var; produto["frame"] = item_frame

def carregar_lista_compras():
    global lista_compras_data, lista_compras_inner_frame
    if lista_compras_inner_frame:
        for widget in lista_compras_inner_frame.winfo_children():
            widget.destroy()
            
    if ID_USUARIO_ATUAL is None:
        ctk.CTkLabel(lista_compras_inner_frame, text="Erro: Usuário não logado.", font=ctk.CTkFont(size=20), text_color="red").pack(pady=20)
        return

    if lista_compras_data is None:
        ctk.CTkLabel(lista_compras_inner_frame, text="Analisando seu estoque e histórico...", font=ctk.CTkFont(size=20), text_color="gray").pack(pady=20, padx=10)
        return
        
    if not lista_compras_data:
         ctk.CTkLabel(lista_compras_inner_frame, text="Seu estoque está ótimo! Nenhuma sugestão necessária.", font=ctk.CTkFont(size=16), text_color="gray").pack(pady=20, padx=10)
         return

    produtos_por_categoria = defaultdict(list)
    for produto in lista_compras_data:
        produtos_por_categoria[produto.get("categoria", "Outros")].append(produto)
    for categoria in sorted(produtos_por_categoria.keys()):
        header = ctk.CTkFrame(lista_compras_inner_frame, fg_color="transparent"); header.pack(fill="x", padx=5, pady=(10, 5))
        ctk.CTkLabel(header, text=categoria.upper(), font=ctk.CTkFont(size=12, weight="bold"), text_color="#00529B").pack(side="left")
        for produto in produtos_por_categoria[categoria]:
            criar_item_lista(lista_compras_inner_frame, produto)

def adicionar_item_manual():
    dialog = ctk.CTkToplevel(window); dialog.title("Adicionar Novo Item"); dialog.geometry("350x380"); dialog.transient(window); dialog.grab_set()
    main_frame = ctk.CTkFrame(dialog, fg_color="transparent"); main_frame.pack(padx=20, pady=20, fill="both", expand=True)
    ctk.CTkLabel(main_frame, text="Nome do Produto:").pack(anchor="w"); nome_entry = ctk.CTkEntry(main_frame); nome_entry.pack(fill="x", pady=(0, 10)); nome_entry.focus()
    ctk.CTkLabel(main_frame, text="Quantidade:").pack(anchor="w"); qtd_entry = ctk.CTkEntry(main_frame); qtd_entry.pack(fill="x", pady=(0, 10))
    ctk.CTkLabel(main_frame, text="Unidade:").pack(anchor="w"); unidade_menu = ctk.CTkComboBox(main_frame, values=UNIDADES_ESTOQUE, state="readonly"); unidade_menu.pack(fill="x", pady=(0, 10)); unidade_menu.set(UNIDADES_ESTOQUE[0])
    ctk.CTkLabel(main_frame, text="Categoria:").pack(anchor="w"); categoria_menu = ctk.CTkComboBox(main_frame, values=CATEGORIAS_COMPRA, state="readonly"); categoria_menu.pack(fill="x", pady=(0, 10)); categoria_menu.set(CATEGORIAS_COMPRA[0])
    def adicionar_e_fechar():
        nome = nome_entry.get().strip(); quant = qtd_entry.get().strip()
        if not nome or not quant: return
        novo_item = {"nome": nome.capitalize(), "quantidade": quant, "unidade": unidade_menu.get(), "categoria": categoria_menu.get(), "preco": "N/A"}
        if lista_compras_data is None: lista_compras_data = []
        lista_compras_data.append(novo_item); carregar_lista_compras(); dialog.destroy()
    ctk.CTkButton(main_frame, text="Adicionar Item", command=adicionar_e_fechar).pack(fill="x", pady=(10,0))

def remover_item(item_to_remove):
    try: lista_compras_data.remove(item_to_remove)
    except (ValueError, KeyError): pass
    carregar_lista_compras()

def remover_selecionados():
    if not lista_compras_data: return
    itens_para_remover = [p for p in lista_compras_data if p.get("checkbox_var") and p["checkbox_var"].get()]
    if not itens_para_remover: return
    for item in itens_para_remover: lista_compras_data.remove(item)
    carregar_lista_compras()

def salvar_lista():
    if not lista_compras_data: return
    try:
        lista_path = OUTPUT_PATH / "lista_compras.txt"
        with open(lista_path, "w", encoding="utf-8") as f:
            f.write(f"Lista de Compras - Gerada em: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            produtos_por_categoria = defaultdict(list)
            for p in lista_compras_data: produtos_por_categoria[p.get("categoria", "Outros")].append(p)
            for cat in sorted(produtos_por_categoria.keys()):
                f.write(f"--- {cat.upper()} ---\n");
                for prod in produtos_por_categoria[cat]: f.write(f"[ ] {prod['nome']} ({prod['quantidade']} {prod['unidade']}) - Preço Est.: {prod.get('preco', 'N/A')}\n"); f.write("\n")
        messagebox.showinfo("Lista Salva", f"Sua lista foi salva em:\n{lista_path}")
    except Exception as e: messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}")

# --- Main ---
if __name__ == "__main__":
    window = ctk.CTk(); window.title("MyGeli - Lista de Compras"); window.configure(fg_color="#F5F5F5")
    window_width, window_height = 500, 700
    screen_width = window.winfo_screenwidth(); screen_height = window.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2); center_y = int(screen_height/2 - window_height/2)
    window.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
    window.grid_rowconfigure(1, weight=1); window.grid_columnconfigure(0, weight=1)
    
    ID_USUARIO_ATUAL = obter_usuario_logado()
    if not ID_USUARIO_ATUAL:
        messagebox.showwarning("Acesso Limitado", "Não foi possível identificar o usuário logado. Algumas funções podem não funcionar corretamente.")

    header_frame = ctk.CTkFrame(window, height=80, corner_radius=0, fg_color="#0084FF"); header_frame.grid(row=0, column=0, sticky="new")
    header_frame.grid_propagate(False); header_frame.grid_columnconfigure(1, weight=1)
    
    try:
        seta_image = ctk.CTkImage(light_image=Image.open(SETA_IMAGE_PATH).resize((30, 30)), size=(30, 30))
        back_btn = ctk.CTkButton(header_frame, text="", image=seta_image, width=40, height=40, fg_color="transparent", hover_color="#0066CC", command=go_to_gui1)
    except Exception as e:
        print(f"Log: Imagem da seta não encontrada ({e}). Usando botão de texto.")
        back_btn = ctk.CTkButton(header_frame, text="< Voltar", width=60, fg_color="transparent", hover_color="#0066CC", text_color="white", command=go_to_gui1)
    back_btn.grid(row=0, column=0, padx=10, pady=20, sticky="w")
    
    ctk.CTkLabel(header_frame, text="Lista de Compras", font=ctk.CTkFont(size=22, weight="bold"), text_color="white").grid(row=0, column=1, sticky="ew", padx=(0,70))

    content_frame = ctk.CTkFrame(window, fg_color="transparent"); content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
    content_frame.grid_rowconfigure(1, weight=1); content_frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(content_frame, text="Sugestões baseadas apenas no seu estoque e histórico.\nPreços estimados (média Brasil).", font=ctk.CTkFont(size=12), text_color="#CE5959").grid(row=0, column=0, pady=(0, 15))

    
    lista_frame = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=10); lista_frame.grid(row=1, column=0, sticky="nsew")
    scrollable_frame = ctk.CTkScrollableFrame(lista_frame, fg_color="white"); scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)
    lista_compras_inner_frame = scrollable_frame
    
    botoes_frame = ctk.CTkFrame(content_frame, fg_color="transparent"); botoes_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
    botoes_frame.grid_columnconfigure(0, weight=1)
    ctk.CTkButton(botoes_frame, text="Adicionar Item", command=adicionar_item_manual, fg_color="#4caf50", hover_color="#45a049").grid(row=0, column=0, sticky="ew", pady=2)
    ctk.CTkButton(botoes_frame, text="Remover Selecionados", command=remover_selecionados, fg_color="#f44336", hover_color="#d32f2f").grid(row=1, column=0, sticky="ew", pady=2)
    ctk.CTkButton(botoes_frame, text="Salvar Lista (.txt)", command=salvar_lista, fg_color="#2196f3", hover_color="#1976d2").grid(row=2, column=0, sticky="ew", pady=2)

    carregar_lista_compras()
    if ID_USUARIO_ATUAL:
        background_thread = threading.Thread(target=carregar_sugestoes_em_background)
        background_thread.daemon = True
        background_thread.start()
    
    window.mainloop()