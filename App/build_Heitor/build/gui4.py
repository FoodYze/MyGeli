# CÓDIGO APENAS DA BRANCH "improvement(gui4)-padronização-layout"

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
import subprocess # Adicionado para go_to_gui1
import sys # Adicionado para go_to_gui1

# --- Constantes e Configurações ---
OUTPUT_PATH = Path(__file__).parent
ASSETS_GERAL_PATH = OUTPUT_PATH / "assets" / "geral"
SETA_IMAGE_PATH = ASSETS_GERAL_PATH / "seta.png"

# --- Variáveis Globais da UI ---
lista_compras_canvas = None
lista_compras_inner_frame = None
window = None
lista_compras_data = []

# --- SUAS CREDENCIAIS ---
db_host = "localhost"
db_name = "mygeli"
db_usuario = "foodyzeadm"
db_senha = "supfood0017admx"

# --- CONFIGURAÇÃO DA API GEMINI ---
model = None
try:
    from gui0 import GOOGLE_API_KEY
    if GOOGLE_API_KEY and GOOGLE_API_KEY != "SUA_CHAVE_API_AQUI":
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        print("Log: API do Gemini configurada com sucesso com o modelo 'gemini-2.5-flash'.")
    else:
        print("AVISO: GOOGLE_API_KEY não encontrada. Funções de IA usarão dados simulados.")
        messagebox.showwarning("Aviso de IA", "Chave da API não encontrada. Usando sugestões simuladas.")
except ImportError:
    print("AVISO: Arquivo gui0.py não encontrado. As sugestões de IA usarão dados simulados.")
    messagebox.showwarning("Aviso de IA", "Arquivo gui0.py não encontrado para carregar a chave da API.")
except Exception as e:
    print(f"AVISO: Não foi possível configurar a API do Gemini. Funções de IA estarão desabilitadas. Erro: {e}")
    messagebox.showerror("Erro de API", f"Não foi possível configurar a API do Gemini: {e}")

# --- Funções ---

def conectar_mysql(host, database, user, password):
    try:
        conexao = mysql.connector.connect(host=host, database=database, user=user, password=password)
        if conexao.is_connected():
            return conexao
    except Error as e:
        messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao banco de dados:\n{e}")
        return None

def buscar_inventario_usuario(conexao):
    if not conexao or not conexao.is_connected():
        return []
    inventario = []
    query = "SELECT nome_produto, quantidade_produto AS quantidade, tipo_volume AS unidade FROM produtos"
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(query)
        inventario = cursor.fetchall()
    except Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível buscar os dados do inventário:\n{e}")
    finally:
        if cursor:
            cursor.close()
    return inventario

def buscar_historico_uso(conexao):
    if not conexao or not conexao.is_connected():
        return []
    historico = []
    query = """
        SELECT nome_ingrediente, COUNT(*) as frequencia FROM historico_uso
        GROUP BY nome_ingrediente ORDER BY frequencia DESC LIMIT 10
    """
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(query)
        resultados = cursor.fetchall()
        historico = [item['nome_ingrediente'] for item in resultados]
    except Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível buscar o histórico de uso:\n{e}")
    finally:
        if cursor:
            cursor.close()
    return historico

def formatar_resposta_gemini(texto_gemini):
    if not texto_gemini:
        return []
    itens_formatados = []
    padrao = re.compile(
        r'^\s*[\*\-]?\s*(?P<nome>.+?)\s*-\s*(?P<quantidade>[\d.,]+)\s*(?P<unidade>[a-zA-ZáéíóúÁÉÍÓÚçÇ\s/]+)\s*$',
        re.IGNORECASE | re.MULTILINE
    )
    for linha in texto_gemini.split('\n'):
        match = padrao.search(linha.strip())
        if match:
            try:
                nome = match.group('nome').strip()
                quantidade_str = match.group('quantidade').replace(',', '.').strip()
                unidade = match.group('unidade').strip()
                quantidade = float(quantidade_str)
                if quantidade.is_integer():
                    quantidade = int(quantidade)
                itens_formatados.append({"nome": nome, "quantidade": quantidade, "unidade": unidade})
            except (ValueError, IndexError):
                pass
    return itens_formatados

def recomendar_produtos_com_gemini(inventario, historico):
    if not model:
        return None
    # Esta função está faltando na branch 'improvement', então ela retornaria None e usaria o fallback.
    # Para fazê-la funcionar, seria necessário copiar a lógica da 'main'.
    return None # Simula a falta da lógica de prompt

def go_to_gui1():
    if window:
        window.destroy()
    try:
        subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui1.py")])
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao tentar abrir a tela inicial: {e}")

def buscar_produtos_sugeridos():
    produtos_sugeridos = []
    conexao = conectar_mysql(db_host, db_name, db_usuario, db_senha)
    if conexao:
        inventario_atual = buscar_inventario_usuario(conexao)
        historico_uso = buscar_historico_uso(conexao)
        if model:
            produtos_sugeridos = recomendar_produtos_com_gemini(inventario_atual, historico_uso)
        conexao.close()

    if not produtos_sugeridos:
        return [
            {"nome": "Café", "quantidade": 500, "unidade": "g"},
            {"nome": "Manteiga", "quantidade": 1, "unidade": "Tablete"},
            {"nome": "Pão de Forma", "quantidade": 1, "unidade": "Pacote"},
            {"nome": "Tomate", "quantidade": 600, "unidade": "g"},
            {"nome": "Queijo Mussarela", "quantidade": 300, "unidade": "g"},
        ]
    return produtos_sugeridos

def criar_item_lista(parent, produto, index):
    item_frame = ctk.CTkFrame(parent, height=55, fg_color="#3B82F6", corner_radius=10)
    item_frame.pack(fill="x", padx=5, pady=5)
    
    remover_btn = ctk.CTkButton(item_frame, text="Remover", width=70, height=28, font=ctk.CTkFont(size=11), fg_color="#d32f2f", hover_color="#b71c1c", command=lambda item=produto: remover_item(item))
    remover_btn.pack(side="right", padx=(5, 10), pady=10)

    quantidade_label = ctk.CTkLabel(item_frame, text=f"{produto['quantidade']} {produto['unidade']}", font=ctk.CTkFont(size=12), anchor="e")
    quantidade_label.pack(side="right", padx=(0, 5), pady=10)
    
    checkbox_var = ctk.BooleanVar()
    checkbox = ctk.CTkCheckBox(item_frame, text="", variable=checkbox_var, width=20)
    checkbox.pack(side="left", padx=(10, 5), pady=10)
    
    nome_label = ctk.CTkLabel(item_frame, text=produto["nome"], font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
    nome_label.pack(side="left", padx=(0, 10), pady=10, fill="x", expand=True)
    
    produto["checkbox_var"] = checkbox_var
    produto["frame"] = item_frame

def carregar_lista_compras():
    if lista_compras_inner_frame:
        for widget in lista_compras_inner_frame.winfo_children():
            widget.destroy()
    if not lista_compras_data:
        ctk.CTkLabel(lista_compras_inner_frame, text="Nenhuma sugestão encontrada.", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=20)
        return
    for index, produto in enumerate(lista_compras_data):
        criar_item_lista(lista_compras_inner_frame, produto, index)

def adicionar_item_manual():
    dialog = ctk.CTkInputDialog(text="Digite o nome do produto:", title="Adicionar Item")
    nome = dialog.get_input()
    if nome:
        dialog_qtd = ctk.CTkInputDialog(text="Digite a quantidade:", title="Quantidade")
        quantidade = dialog_qtd.get_input()
        if quantidade:
            dialog_unidade = ctk.CTkInputDialog(text="Digite a unidade (ex: kg, L, un):", title="Unidade")
            unidade = dialog_unidade.get_input()
            if unidade:
                novo_item = {"nome": nome, "quantidade": quantidade, "unidade": unidade}
                lista_compras_data.append(novo_item)
                carregar_lista_compras()
                messagebox.showinfo("Sucesso", f"Item '{nome}' adicionado à lista!")

def remover_item(item_to_remove):
    global lista_compras_data
    try:
        lista_compras_data.remove(item_to_remove)
        if "frame" in item_to_remove and item_to_remove["frame"].winfo_exists():
            item_to_remove["frame"].destroy()
        messagebox.showinfo("Item Removido", f"'{item_to_remove['nome']}' foi removido da lista.")
    except (ValueError, KeyError):
        messagebox.showwarning("Erro", "Item não encontrado ou já removido.")
    carregar_lista_compras()

def remover_selecionados():
    global lista_compras_data
    itens_para_remover = [p for p in lista_compras_data if "checkbox_var" in p and p["checkbox_var"].get()]
    if not itens_para_remover:
        messagebox.showwarning("Nenhum Item Selecionado", "Selecione pelo menos um item para remover.")
        return
    for item in itens_para_remover:
        if "frame" in item and item["frame"].winfo_exists():
            item["frame"].destroy()
        lista_compras_data.remove(item)
    messagebox.showinfo("Itens Removidos", f"{len(itens_para_remover)} item(s) removido(s) da lista.")

def salvar_lista():
    if not lista_compras_data:
        messagebox.showwarning("Lista Vazia", "Não há itens na lista para salvar.")
        return
    try:
        lista_path = OUTPUT_PATH / "lista_compras.txt"
        with open(lista_path, "w", encoding="utf-8") as file:
            file.write("=== MINHA LISTA DE COMPRAS ===\n")
            file.write(f"Gerada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            for produto in lista_compras_data:
                file.write(f"[ ] {produto['nome']} - {produto['quantidade']} {produto['unidade']}\n")
            file.write(f"\nTotal de itens: {len(lista_compras_data)}")
        messagebox.showinfo("Lista Salva", f"Sua lista de compras foi salva em:\n{lista_path}")
    except Exception as e:
        messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro ao salvar a lista:\n{e}")

if __name__ == "__main__":
    window = ctk.CTk()
    window.title("MyGeli - Lista de Compras")
    window.configure(fg_color="#F5F5F5")
    
    window_width, window_height = 400, 650
    center_x = int(window.winfo_screenwidth() / 2 - window_width / 2)
    center_y = int(window.winfo_screenheight() / 2 - window_height / 2)
    window.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
    window.minsize(window_width, window_height)

    window.grid_rowconfigure(1, weight=1)
    window.grid_columnconfigure(0, weight=1)

    header_frame = ctk.CTkFrame(window, height=80, corner_radius=0, fg_color="#0084FF")
    header_frame.grid(row=0, column=0, sticky="new")
    header_frame.grid_propagate(False)
    header_frame.grid_columnconfigure(1, weight=1)
    
    try:
        seta_image = ctk.CTkImage(light_image=Image.open(SETA_IMAGE_PATH).resize((30, 30)), size=(30, 30))
        back_btn = ctk.CTkButton(header_frame, text="", image=seta_image, width=40, height=40, fg_color="transparent", hover_color="#0066CC", command=go_to_gui1)
    except Exception as e:
        back_btn = ctk.CTkButton(header_frame, text="Voltar", fg_color="transparent", hover_color="#0066CC", text_color="white", command=go_to_gui1)
    back_btn.grid(row=0, column=0, padx=10, pady=20, sticky="w")

    ctk.CTkLabel(header_frame, text="Lista de Compras", font=ctk.CTkFont(size=22, weight="bold"), text_color="white").grid(row=0, column=1, pady=20, sticky="ew")

    content_frame = ctk.CTkFrame(window, fg_color="transparent")
    content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
    content_frame.grid_rowconfigure(1, weight=1)
    content_frame.grid_columnconfigure(0, weight=1)
    
    ctk.CTkLabel(content_frame, text="Sugestões baseadas no seu consumo", font=ctk.CTkFont(size=14), text_color="#666666").grid(row=0, column=0, pady=(0, 15))
    
    lista_frame = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=10)
    lista_frame.grid(row=1, column=0, sticky="nsew")
    
    lista_compras_canvas = ctk.CTkScrollableFrame(lista_frame, fg_color="white")
    lista_compras_canvas.pack(fill="both", expand=True, padx=5, pady=5)
    
    lista_compras_inner_frame = lista_compras_canvas
    
    botoes_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    botoes_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
    botoes_frame.grid_columnconfigure(0, weight=1)
    
    btn_adicionar = ctk.CTkButton(botoes_frame, text="Adicionar Item", height=40, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#4caf50", hover_color="#45a049", command=adicionar_item_manual)
    btn_adicionar.grid(row=0, column=0, sticky="ew", pady=(0,5))
    
    btn_remover = ctk.CTkButton(botoes_frame, text="Remover Selecionados", height=40, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#f44336", hover_color="#d32f2f", command=remover_selecionados)
    btn_remover.grid(row=1, column=0, sticky="ew", pady=(0,5))
    
    btn_salvar = ctk.CTkButton(botoes_frame, text="Salvar Lista (.txt)", height=40, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#2196f3", hover_color="#1976d2", command=salvar_lista)
    btn_salvar.grid(row=2, column=0, sticky="ew")
    
    lista_compras_data = buscar_produtos_sugeridos()
    carregar_lista_compras()

    window.mainloop()