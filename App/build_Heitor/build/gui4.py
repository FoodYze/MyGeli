import customtkinter as ctk
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import mysql.connector
import google.generativeai as genai
import os
import traceback
import re
from tkinter import messagebox
from PIL import Image

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
db_name = "foodyze"
db_usuario = "foodyzesda"
db_senha = "supfood0017admx"

def conectar_mysql(host, database, user, password):
    """ Tenta conectar ao banco de dados MySQL e imprime o status da conexão.
    Retorna o objeto de conexão bem sucedido, None no caso contrário.
    """
    conexao = None
    try:
        conexao = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        if conexao.is_connected():
            db_info = conexao.get_server_info()
            print(f"Conectado ao MySQL versão {db_info}")
            cursor = conexao.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()
            print(f"Conectado ao banco de dados: {record}")
            return conexao
    except mysql.connector.Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao banco de dados:\n{e}\n\nVerifique suas credenciais.")
        return None

def go_to_gui1():
    """Fecha a janela atual e abre a gui1.py."""
    if window:
        window.destroy()
    try:
        subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui1.py")])
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao tentar abrir a tela inicial: {e}")

def buscar_produtos_sugeridos():
    """
    Busca produtos sugeridos no BD e retorna uma lista simulada.
    Em uma implementação real, aqui seria feita a consulta com IA.
    """
    # Simulação de dados para a interface
    produtos_sugeridos = [
        {"nome": "Leite", "quantidade": 2, "unidade": "Litros"},
        {"nome": "Ovos", "quantidade": 12, "unidade": "Unidades"},
        {"nome": "Farinha de Trigo", "quantidade": 1, "unidade": "Kg"},
        {"nome": "Açúcar", "quantidade": 500, "unidade": "g"},
        {"nome": "Frango", "quantidade": 1, "unidade": "Kg"},
        {"nome": "Cenoura", "quantidade": 500, "unidade": "g"},
        {"nome": "Macarrão", "quantidade": 2, "unidade": "Pacotes"},
        {"nome": "Fermento", "quantidade": 1, "unidade": "Pacote"}
    ]
    
    return produtos_sugeridos

def criar_item_lista(parent, produto, index):
    """Cria um item da lista de compras na interface"""
    
    # Frame para cada item
    item_frame = ctk.CTkFrame(parent, height=55, fg_color="#3B82F6", corner_radius=10)
    item_frame.pack(fill="x", padx=5, pady=5)
    
    # Botão remover (empacotado primeiro para ficar à direita)
    remover_btn = ctk.CTkButton(
        item_frame,
        text="Remover",
        width=70,
        height=28,
        font=ctk.CTkFont(size=11),
        fg_color="#d32f2f",
        hover_color="#b71c1c",
        command=lambda item=produto: remover_item(item)
    )
    remover_btn.pack(side="right", padx=(5, 10), pady=10)

    # Quantidade (empacotada antes do nome para ficar à direita do nome)
    quantidade_label = ctk.CTkLabel(
        item_frame,
        text=f"{produto['quantidade']} {produto['unidade']}",
        font=ctk.CTkFont(size=12),
        anchor="e"
    )
    quantidade_label.pack(side="right", padx=(0, 5), pady=10)
    
    # Checkbox para seleção
    checkbox_var = ctk.BooleanVar()
    checkbox = ctk.CTkCheckBox(
        item_frame,
        text="",
        variable=checkbox_var,
        width=20
    )
    checkbox.pack(side="left", padx=(10, 5), pady=10)
    
    # Nome do produto (expande para preencher o espaço restante)
    nome_label = ctk.CTkLabel(
        item_frame,
        text=produto["nome"],
        font=ctk.CTkFont(size=14, weight="bold"),
        anchor="w"
    )
    nome_label.pack(side="left", padx=(0, 10), pady=10, fill="x", expand=True)
    
    # Armazenar a checkbox_var e o item_frame no dicionário do produto
    produto["checkbox_var"] = checkbox_var
    produto["frame"] = item_frame
    
    return item_frame, checkbox_var

def carregar_lista_compras():
    """Carrega e exibe a lista de compras sugerida"""
    global lista_compras_data, lista_compras_inner_frame
    
    # Limpar frame existente
    if lista_compras_inner_frame:
        for widget in lista_compras_inner_frame.winfo_children():
            widget.destroy()
    
    # Criar itens da lista
    for index, produto in enumerate(lista_compras_data):
        item_frame, checkbox_var = criar_item_lista(lista_compras_inner_frame, produto, index)

def adicionar_item_manual():
    """Abre diálogo para adicionar item manualmente"""
    dialog = ctk.CTkInputDialog(
        text="Digite o nome do produto:",
        title="Adicionar Item"
    )
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
    """Remove um item da lista"""
    global lista_compras_data
    
    try:
        lista_compras_data.remove(item_to_remove)
        if "frame" in item_to_remove and item_to_remove["frame"].winfo_exists():
            item_to_remove["frame"].destroy()
        messagebox.showinfo("Item Removido", f"'{item_to_remove['nome']}' foi removido da lista.")
    except (ValueError, KeyError):
        messagebox.showwarning("Erro", "Item não encontrado ou já removido.")
        # Recarrega a lista para garantir a consistência da UI
        carregar_lista_compras()


def remover_selecionados():
    """Remove todos os itens selecionados"""
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
    """Salva a lista de compras em arquivo"""
    try:
        lista_path = OUTPUT_PATH / "lista_compras.txt"
        
        with open(lista_path, "w", encoding="utf-8") as file:
            file.write("=== MINHA LISTA DE COMPRAS ===\n")
            file.write(f"Gerada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            for index, produto in enumerate(lista_compras_data, 1):
                file.write(f"[ ] {produto['nome']} - {produto['quantidade']} {produto['unidade']}\n")
            
            file.write(f"\nTotal de itens: {len(lista_compras_data)}")
        
        messagebox.showinfo("Lista Salva", f"Sua lista de compras foi salva em:\n{lista_path}")
        
    except Exception as e:
        messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro ao salvar a lista:\n{e}")

def abrir_gui4():
    """Função principal para abrir a GUI4 - Lista de Compras"""
    global window, lista_compras_canvas, lista_compras_inner_frame
    
    # Configurar janela principal
    window = ctk.CTk()
    window.title("MyGeli - Lista de Compras")
    window.configure(fg_color="#F5F5F5")
    
    # Padronização do tamanho e centralização da janela
    window_width = 400
    window_height = 650
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    center_x = int(screen_width/2 - window_width / 2)
    center_y = int(screen_height/2 - window_height / 2)
    window.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
    window.minsize(window_width, window_height)

    # Layout com Grid
    window.grid_rowconfigure(1, weight=1)
    window.grid_columnconfigure(0, weight=1)

    # --- Cabeçalho Padrão ---
    header_frame = ctk.CTkFrame(window, height=80, corner_radius=0, fg_color="#0084FF")
    header_frame.grid(row=0, column=0, sticky="new")
    header_frame.grid_propagate(False)
    header_frame.grid_columnconfigure(1, weight=1)
    
    try:
        seta_image = ctk.CTkImage(light_image=Image.open(SETA_IMAGE_PATH).resize((30, 30)), size=(30, 30))
        back_btn = ctk.CTkButton(header_frame, text="", image=seta_image, width=40, height=40, fg_color="transparent", hover_color="#0066CC", command=go_to_gui1)
    except Exception as e:
        print(f"Erro ao carregar imagem da seta: {e}")
        back_btn = ctk.CTkButton(header_frame, text="Voltar", fg_color="transparent", hover_color="#0066CC", text_color="white", command=go_to_gui1)
    back_btn.grid(row=0, column=0, padx=10, pady=20, sticky="w")

    ctk.CTkLabel(header_frame, text="Lista de Compras", font=ctk.CTkFont(size=22, weight="bold"), text_color="white").grid(row=0, column=1, pady=20, sticky="ew")

    # Frame de conteúdo principal
    content_frame = ctk.CTkFrame(window, fg_color="transparent")
    content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
    content_frame.grid_rowconfigure(1, weight=1)
    content_frame.grid_columnconfigure(0, weight=1)
    
    # Subtítulo
    subtitulo = ctk.CTkLabel(
        content_frame,
        text="Sugestões baseadas no seu consumo",
        font=ctk.CTkFont(size=14),
        text_color="#666666"
    )
    subtitulo.grid(row=0, column=0, pady=(0, 15))
    
    # Frame com a lista rolável
    lista_frame = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=10)
    lista_frame.grid(row=1, column=0, sticky="nsew")
    
    lista_compras_canvas = ctk.CTkScrollableFrame(
        lista_frame,
        fg_color="white"
    )
    lista_compras_canvas.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Frame interno para os itens
    lista_compras_inner_frame = lista_compras_canvas
    
    # Frame para botões de ação na parte inferior
    botoes_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    botoes_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
    botoes_frame.grid_columnconfigure(0, weight=1)
    
    btn_adicionar = ctk.CTkButton(
        botoes_frame, text="Adicionar Item", height=40, font=ctk.CTkFont(size=12, weight="bold"),
        fg_color="#4caf50", hover_color="#45a049", command=adicionar_item_manual
    )
    btn_adicionar.grid(row=0, column=0, sticky="ew", pady=(0,5))
    
    btn_remover = ctk.CTkButton(
        botoes_frame, text="Remover Selecionados", height=40, font=ctk.CTkFont(size=12, weight="bold"),
        fg_color="#f44336", hover_color="#d32f2f", command=remover_selecionados
    )
    btn_remover.grid(row=1, column=0, sticky="ew", pady=(0,5))
    
    btn_salvar = ctk.CTkButton(
        botoes_frame, text="Salvar Lista (.txt)", height=40, font=ctk.CTkFont(size=12, weight="bold"),
        fg_color="#2196f3", hover_color="#1976d2", command=salvar_lista
    )
    btn_salvar.grid(row=2, column=0, sticky="ew")
    
    # Carregar lista inicial de produtos sugeridos
    global lista_compras_data
    lista_compras_data = buscar_produtos_sugeridos()
    carregar_lista_compras()
    
    # Iniciar loop da interface
    window.mainloop()

if __name__ == "__main__":
    abrir_gui4()
