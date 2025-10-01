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

# --- Constantes e Configurações ---
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets" / "frame1"
SETA_IMAGE_PATH = OUTPUT_PATH / "seta.png"
UP_ARROW_IMAGE_PATH = OUTPUT_PATH / "up_arrow.png"
DOWN_ARROW_IMAGE_PATH = OUTPUT_PATH / "down_arrow.png"
DEFAULT_ITEM_IMAGE_PATH = OUTPUT_PATH / "default.png"

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

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

def criar_item_lista(parent, produto, index):
    """Cria um item da lista de compras na interface"""
    
    # Frame para cada item
    item_frame = ctk.CTkFrame(parent, height=60, fg_color="#3B82F6", corner_radius=10)
    item_frame.pack(fill="x", padx=10, pady=5)
    item_frame.pack_propagate(False)
    
    # Checkbox para seleção
    checkbox_var = ctk.BooleanVar()
    checkbox = ctk.CTkCheckBox(
        item_frame,
        text="",
        variable=checkbox_var,
        width=20
    )
    checkbox.pack(side="left", padx=(10, 15), pady=15)
    
    # Nome do produto
    nome_label = ctk.CTkLabel(
        item_frame,
        text=produto["nome"],
        font=ctk.CTkFont(size=14, weight="bold"),
        width=200,
        anchor="w"
    )
    nome_label.pack(side="left", padx=(0, 10), pady=15)
    
    # Quantidade
    quantidade_label = ctk.CTkLabel(
        item_frame,
        text=f"{produto['quantidade']} {produto['unidade']}",
        font=ctk.CTkFont(size=12),
        width=120,
        anchor="w"
    )
    quantidade_label.pack(side="left", padx=(0, 10), pady=15)
    
    # Botão remover
    remover_btn = ctk.CTkButton(
        item_frame,
        text="Remover",
        width=80,
        height=30,
        font=ctk.CTkFont(size=11),
        fg_color="#d32f2f",
        hover_color="#b71c1c",
        command=lambda item=produto: remover_item(item)
    )
    remover_btn.pack(side="right", padx=(10, 10), pady=15)
    
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
        # As referências checkbox_var e frame já são armazenadas dentro de criar_item_lista
        # Não é necessário reatribuir aqui, mas é importante que criar_item_lista as armazene corretamente.

def adicionar_item_manual():
    """Abre diálogo para adicionar item manualmente"""
    dialog = ctk.CTkInputDialog(
        text="Digite o nome do produto:",
        title="Adicionar Item"
    )
    nome = dialog.get_input()
    
    if nome:
        # Diálogo para quantidade
        dialog_qtd = ctk.CTkInputDialog(
            text="Digite a quantidade:",
            title="Quantidade"
        )
        quantidade = dialog_qtd.get_input()
        
        if quantidade:
            # Diálogo para unidade
            dialog_unidade = ctk.CTkInputDialog(
                text="Digite a unidade (ex: kg, litros, unidades):",
                title="Unidade"
            )
            unidade = dialog_unidade.get_input()
            
            if unidade:
                # Adicionar à lista
                novo_item = {
                    "nome": nome,
                    "quantidade": quantidade,
                    "unidade": unidade
                }
                lista_compras_data.append(novo_item)
                
                # Recarregar lista
                carregar_lista_compras()
                
                messagebox.showinfo("Sucesso", f"Item '{nome}' adicionado à lista!")

def remover_item(item_to_remove):
    """Remove um item da lista"""
    global lista_compras_data
    
    try:
        lista_compras_data.remove(item_to_remove)
        # Destruir o frame do item removido da UI
        if "frame" in item_to_remove and item_to_remove["frame"] is not None:
            item_to_remove["frame"].destroy()
        carregar_lista_compras()
        messagebox.showinfo("Item Removido", f"'{item_to_remove["nome"]}' foi removido da lista.")
    except ValueError:
        messagebox.showwarning("Erro", "Item não encontrado na lista.")

def remover_selecionados():
    """Remove todos os itens selecionados"""
    global lista_compras_data
    
    # Identificar itens selecionados
    itens_para_remover = []
    for produto in lista_compras_data:
        if "checkbox_var" in produto and produto["checkbox_var"].get():
            itens_para_remover.append(produto)
    
    # Remover itens
    for item_to_remove in itens_para_remover:
        if "frame" in item_to_remove and item_to_remove["frame"] is not None:
            item_to_remove["frame"].destroy()
        lista_compras_data.remove(item_to_remove)
    
    if itens_para_remover:
        carregar_lista_compras()
        messagebox.showinfo("Itens Removidos", f"{len(itens_para_remover)} item(s) removido(s) da lista.")
    else:
        messagebox.showwarning("Nenhum Item Selecionado", "Selecione pelo menos um item para remover.")

def salvar_lista():
    """Salva a lista de compras em arquivo"""
    try:
        # Criar arquivo de lista de compras
        lista_path = OUTPUT_PATH / "lista_compras.txt"
        
        with open(lista_path, "w", encoding="utf-8") as file:
            file.write("=== LISTA DE COMPRAS SUGERIDA ===\n")
            file.write(f"Gerada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            for index, produto in enumerate(lista_compras_data, 1):
                file.write(f"{index}. {produto['nome']} - {produto['quantidade']} {produto['unidade']}\n")
            
            file.write(f"\nTotal de itens: {len(lista_compras_data)}")
        
        messagebox.showinfo("Lista Salva", f"Lista de compras salva em:\n{lista_path}")
        
    except Exception as e:
        messagebox.showerror("Erro ao Salvar", f"Erro ao salvar lista:\n{e}")

def abrir_gui4():
    """Função principal para abrir a GUI4 - Lista de Compras"""
    global window, lista_compras_canvas, lista_compras_inner_frame
    
    # Configurar janela principal
    window = ctk.CTk()
    window.geometry("800x600")
    window.title("MyGeli - Lista de Compras Sugerida")
    window.configure(fg_color="#f0f0f0")
    
    # Título principal
    titulo = ctk.CTkLabel(
        window,
        text="Lista de Compras Sugerida",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color="#2e7d32"
    )
    titulo.pack(pady=(20, 10))
    
    # Subtítulo
    subtitulo = ctk.CTkLabel(
        window,
        text="Sugestões baseadas no seu consumo e utilização do app",
        font=ctk.CTkFont(size=14),
        text_color="#666666"
    )
    subtitulo.pack(pady=(0, 20))
    
    # Frame principal para a lista
    main_frame = ctk.CTkFrame(window, fg_color="white")
    main_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    # Canvas e scrollbar para lista rolável
    lista_compras_canvas = ctk.CTkScrollableFrame(
        main_frame,
        width=740,
        height=400,
        fg_color="white"
    )
    lista_compras_canvas.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Frame interno para os itens
    lista_compras_inner_frame = lista_compras_canvas
    
    # Frame para botões de ação
    botoes_frame = ctk.CTkFrame(window, fg_color="transparent")
    botoes_frame.pack(fill="x", padx=20, pady=(0, 20))
    
    # Botão Adicionar Manualmente
    btn_adicionar = ctk.CTkButton(
        botoes_frame,
        text="Adicionar Manualmente",
        width=150,
        height=40,
        font=ctk.CTkFont(size=12, weight="bold"),
        fg_color="#4caf50",
        hover_color="#45a049",
        command=adicionar_item_manual
    )
    btn_adicionar.pack(side="left", padx=(0, 10))
    
    # Botão Remover Selecionados
    btn_remover = ctk.CTkButton(
        botoes_frame,
        text="Remover Selecionados",
        width=150,
        height=40,
        font=ctk.CTkFont(size=12, weight="bold"),
        fg_color="#f44336",
        hover_color="#d32f2f",
        command=remover_selecionados
    )
    btn_remover.pack(side="left", padx=(0, 10))
    
    # Botão Salvar Lista
    btn_salvar = ctk.CTkButton(
        botoes_frame,
        text="Salvar Lista",
        width=150,
        height=40,
        font=ctk.CTkFont(size=12, weight="bold"),
        fg_color="#2196f3",
        hover_color="#1976d2",
        command=salvar_lista
    )
    btn_salvar.pack(side="right")
    
    # Carregar lista inicial de produtos sugeridos
    global lista_compras_data
    lista_compras_data = buscar_produtos_sugeridos()
    carregar_lista_compras()
    
    # Iniciar loop da interface
    window.mainloop()

if __name__ == "__main__":
    abrir_gui4()
