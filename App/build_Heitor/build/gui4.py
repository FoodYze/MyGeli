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
from collections import defaultdict

# --- Constantes e Configurações ---
OUTPUT_PATH = Path(__file__).parent
ASSETS_GERAL_PATH = OUTPUT_PATH / "assets" / "geral"
SETA_IMAGE_PATH = ASSETS_GERAL_PATH / "seta.png"

# --- Variáveis Globais ---
lista_compras_data = []
CATEGORIAS_COMPRA = [
    "Hortifruti", "Mercearia", "Proteínas", "Laticínios", 
    "Padaria", "Bebidas", "Congelados", "Outros"
]
UNIDADES_ESTOQUE = ["Unidades", "Quilos (Kg)", "Gramas (g)", "Litros (L)", "Mililitros (ml)"]

# --- Variáveis Globais da UI ---
lista_compras_inner_frame = None
window = None


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
    Busca produtos sugeridos no BD e retorna uma lista simulada com categorias.
    """
    produtos_sugeridos = [
        {"nome": "Leite", "quantidade": 2, "unidade": "Litros", "categoria": "Laticínios"},
        {"nome": "Ovos", "quantidade": 12, "unidade": "Unidades", "categoria": "Proteínas"},
        {"nome": "Farinha de Trigo", "quantidade": 1, "unidade": "Kg", "categoria": "Mercearia"},
        {"nome": "Açúcar", "quantidade": 500, "unidade": "g", "categoria": "Mercearia"},
        {"nome": "Frango", "quantidade": 1, "unidade": "Kg", "categoria": "Proteínas"},
        {"nome": "Cenoura", "quantidade": 500, "unidade": "g", "categoria": "Hortifruti"},
        {"nome": "Macarrão", "quantidade": 2, "unidade": "Pacotes", "categoria": "Mercearia"},
        {"nome": "Maçã", "quantidade": 6, "unidade": "Unidades", "categoria": "Hortifruti"},
        {"nome": "Pão de Forma", "quantidade": 1, "unidade": "Pacote", "categoria": "Padaria"}
    ]
    
    return produtos_sugeridos

def criar_item_lista(parent, produto):
    """Cria um item da lista de compras na interface"""
    
    item_frame = ctk.CTkFrame(parent, height=55, fg_color="#3B82F6", corner_radius=10)
    item_frame.pack(fill="x", padx=5, pady=(0, 5))
    
    remover_btn = ctk.CTkButton(
        item_frame, text="Remover", width=70, height=28, font=ctk.CTkFont(size=11),
        fg_color="#d32f2f", hover_color="#b71c1c", command=lambda item=produto: remover_item(item)
    )
    remover_btn.pack(side="right", padx=(5, 10), pady=10)

    quantidade_label = ctk.CTkLabel(
        item_frame, text=f"{produto['quantidade']} {produto['unidade']}", 
        font=ctk.CTkFont(size=12), anchor="e"
    )
    quantidade_label.pack(side="right", padx=(0, 5), pady=10)
    
    checkbox_var = ctk.BooleanVar()
    checkbox = ctk.CTkCheckBox(item_frame, text="", variable=checkbox_var, width=20)
    checkbox.pack(side="left", padx=(10, 5), pady=10)
    
    nome_label = ctk.CTkLabel(
        item_frame, text=produto["nome"], font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
    )
    nome_label.pack(side="left", padx=(0, 10), pady=10, fill="x", expand=True)
    
    produto["checkbox_var"] = checkbox_var
    produto["frame"] = item_frame

def carregar_lista_compras():
    """Carrega a lista de compras, agrupando por categoria."""
    global lista_compras_data, lista_compras_inner_frame
    
    if lista_compras_inner_frame:
        for widget in lista_compras_inner_frame.winfo_children():
            widget.destroy()
    
    # Agrupa produtos por categoria
    produtos_por_categoria = defaultdict(list)
    for produto in lista_compras_data:
        produtos_por_categoria[produto.get("categoria", "Outros")].append(produto)
        
    # Ordena as categorias
    categorias_ordenadas = sorted(produtos_por_categoria.keys())

    # Cria os itens na UI
    for categoria in categorias_ordenadas:
        # Cabeçalho da Categoria
        header = ctk.CTkFrame(lista_compras_inner_frame, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=(10, 5))
        ctk.CTkLabel(
            header, text=categoria.upper(),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00529B"
        ).pack(side="left")
        ctk.CTkFrame(header, fg_color="#D0D0D0", height=1).pack(fill="x", padx=(10, 0), expand=True)

        # Itens da categoria
        for produto in produtos_por_categoria[categoria]:
            criar_item_lista(lista_compras_inner_frame, produto)

def adicionar_item_manual():
    """Abre um diálogo customizado para adicionar um item manualmente, permitindo múltiplas inserções."""
    dialog = ctk.CTkToplevel(window)
    dialog.title("Adicionar Novo Item")
    dialog.geometry("350x380")
    dialog.transient(window)
    dialog.grab_set()
    
    main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    main_frame.pack(padx=20, pady=20, fill="both", expand=True)
    
    ctk.CTkLabel(main_frame, text="Nome do Produto:").pack(anchor="w")
    nome_entry = ctk.CTkEntry(main_frame)
    nome_entry.pack(fill="x", pady=(0, 10))
    nome_entry.focus()
    
    ctk.CTkLabel(main_frame, text="Quantidade:").pack(anchor="w")
    qtd_entry = ctk.CTkEntry(main_frame)
    qtd_entry.pack(fill="x", pady=(0, 10))
    
    ctk.CTkLabel(main_frame, text="Unidade:").pack(anchor="w")
    unidade_var = ctk.StringVar(value=UNIDADES_ESTOQUE[0])
    unidade_menu = ctk.CTkComboBox(main_frame, values=UNIDADES_ESTOQUE, variable=unidade_var, state="readonly")
    unidade_menu.pack(fill="x", pady=(0, 10))
    
    ctk.CTkLabel(main_frame, text="Categoria:").pack(anchor="w")
    categoria_var = ctk.StringVar(value=CATEGORIAS_COMPRA[0])
    categoria_menu = ctk.CTkComboBox(main_frame, values=CATEGORIAS_COMPRA, variable=categoria_var, state="readonly")
    categoria_menu.pack(fill="x", pady=(0, 10))

    # Label para feedback não obstrutivo
    feedback_label = ctk.CTkLabel(main_frame, text="", text_color="green")
    feedback_label.pack(anchor="w", pady=(5,0))
    
    def adicionar_e_continuar():
        """Adiciona o item à lista e limpa os campos para a próxima inserção."""
        nome = nome_entry.get().strip()
        quantidade = qtd_entry.get().strip()
        
        if not nome or not quantidade:
            messagebox.showerror("Erro", "Nome e quantidade são obrigatórios.", parent=dialog)
            return
            
        novo_item = {
            "nome": nome.capitalize(),
            "quantidade": quantidade,
            "unidade": unidade_var.get(),
            "categoria": categoria_var.get()
        }
        lista_compras_data.append(novo_item)
        carregar_lista_compras()
        
        # Limpa os campos para o próximo item e dá feedback
        nome_entry.delete(0, "end")
        qtd_entry.delete(0, "end")
        nome_entry.focus()
        feedback_label.configure(text=f"'{novo_item['nome']}' adicionado!")
        # Apaga o feedback após 2 segundos
        dialog.after(2000, lambda: feedback_label.configure(text=""))

    # Frame de botões na parte inferior
    button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    button_frame.pack(side="bottom", pady=(10,0), fill="x")
    ctk.CTkButton(button_frame, text="Fechar", command=dialog.destroy).pack(side="right")
    ctk.CTkButton(button_frame, text="Adicionar", command=adicionar_e_continuar).pack(side="right", padx=10)


def remover_item(item_to_remove):
    """Remove um item da lista"""
    global lista_compras_data
    try:
        lista_compras_data.remove(item_to_remove)
        carregar_lista_compras() # Recarrega a lista para remover o item e possíveis cabeçalhos vazios
        messagebox.showinfo("Item Removido", f"'{item_to_remove['nome']}' foi removido da lista.")
    except (ValueError, KeyError):
        messagebox.showwarning("Erro", "Item não encontrado ou já removido.")
        carregar_lista_compras()

def remover_selecionados():
    """Remove todos os itens selecionados"""
    global lista_compras_data
    
    itens_para_remover = [p for p in lista_compras_data if p.get("checkbox_var") and p["checkbox_var"].get()]
    
    if not itens_para_remover:
        messagebox.showwarning("Nenhum Item Selecionado", "Selecione pelo menos um item para remover.")
        return

    for item in itens_para_remover:
        lista_compras_data.remove(item)

    carregar_lista_compras()
    messagebox.showinfo("Itens Removidos", f"{len(itens_para_remover)} item(s) removido(s) da lista.")

def salvar_lista():
    """Salva a lista de compras em arquivo, organizada por categoria."""
    try:
        lista_path = OUTPUT_PATH / "lista_compras.txt"
        
        produtos_por_categoria = defaultdict(list)
        for produto in lista_compras_data:
            produtos_por_categoria[produto.get("categoria", "Outros")].append(produto)
        
        with open(lista_path, "w", encoding="utf-8") as file:
            file.write("=== MINHA LISTA DE COMPRAS ===\n")
            file.write(f"Gerada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            for categoria in sorted(produtos_por_categoria.keys()):
                file.write(f"--- {categoria.upper()} ---\n")
                for produto in produtos_por_categoria[categoria]:
                    file.write(f"[ ] {produto['nome']} - {produto['quantidade']} {produto['unidade']}\n")
                file.write("\n")
            
            file.write(f"Total de itens: {len(lista_compras_data)}")
        
        messagebox.showinfo("Lista Salva", f"Sua lista de compras foi salva em:\n{lista_path}")
        
    except Exception as e:
        messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro ao salvar a lista:\n{e}")

def abrir_gui4():
    """Função principal para abrir a GUI4 - Lista de Compras"""
    global window, lista_compras_inner_frame
    
    window = ctk.CTk()
    window.title("MyGeli - Lista de Compras")
    window.configure(fg_color="#F5F5F5")
    
    window_width, window_height = 400, 650
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    center_x = int(screen_width/2 - window_width / 2)
    center_y = int(screen_height/2 - window_height / 2)
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
        print(f"Erro ao carregar imagem da seta: {e}")
        back_btn = ctk.CTkButton(header_frame, text="Voltar", fg_color="transparent", hover_color="#0066CC", text_color="white", command=go_to_gui1)
    back_btn.grid(row=0, column=0, padx=10, pady=20, sticky="w")

    ctk.CTkLabel(header_frame, text="Lista de Compras", font=ctk.CTkFont(size=22, weight="bold"), text_color="white").grid(row=0, column=1, pady=20, sticky="ew")

    content_frame = ctk.CTkFrame(window, fg_color="transparent")
    content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
    content_frame.grid_rowconfigure(1, weight=1)
    content_frame.grid_columnconfigure(0, weight=1)
    
    subtitulo = ctk.CTkLabel(
        content_frame, text="Sugestões baseadas no seu consumo",
        font=ctk.CTkFont(size=14), text_color="#666666"
    )
    subtitulo.grid(row=0, column=0, pady=(0, 15))
    
    lista_frame = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=10)
    lista_frame.grid(row=1, column=0, sticky="nsew")
    
    scrollable_frame = ctk.CTkScrollableFrame(lista_frame, fg_color="white")
    scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    lista_compras_inner_frame = scrollable_frame
    
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
    
    global lista_compras_data
    lista_compras_data = buscar_produtos_sugeridos()
    carregar_lista_compras()
    
    window.mainloop()

if __name__ == "__main__":
    abrir_gui4()
