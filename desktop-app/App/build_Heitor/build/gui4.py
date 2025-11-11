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

import logging
logging.basicConfig(level=logging.ERROR)

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
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        model = genai.GenerativeModel('gemini-2.5-flash', safety_settings=safety_settings)
        print("Log: API do Gemini configurada com o modelo 'gemini-2.5-flash'.")
    else:
        print("AVISO: GOOGLE_API_KEY não encontrada.")
except Exception as e:
    print(f"AVISO: Não foi possível configurar a API do Gemini. Erro: {e}")

# --- Funções do Banco de Dados e Utilitários ---

def conectar_mysql(host, database, user, password):
    try:
        return mysql.connector.connect(host=host, database=database, user=user, password=password)
    except Error as e:
        messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao banco de dados:\n{e}")
        return None

def buscar_inventario_usuario(conexao):
    if not conexao or not conexao.is_connected(): return []
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT nome_produto AS nome, quantidade_produto AS quantidade, tipo_volume AS unidade FROM produtos")
        return cursor.fetchall()
    except Error as e:
        messagebox.showerror("Erro de BD", f"Não foi possível buscar inventário:\n{e}")
        return []

def buscar_historico_uso(conexao):
    if not conexao or not conexao.is_connected(): return []
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("""
            SELECT nome_ingrediente, COUNT(*) as frequencia FROM historico_uso
            GROUP BY nome_ingrediente ORDER BY frequencia DESC LIMIT 15
        """)
        return [item['nome_ingrediente'] for item in cursor.fetchall()]
    except Error as e:
        messagebox.showerror("Erro de BD", f"Não foi possível buscar histórico:\n{e}")
        return []

def go_to_gui1():
    if window: window.destroy()
    try:
        subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui1.py")])
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao abrir tela inicial: {e}")

# --- Funções Principais de Geração e Exibição da Lista ---

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
        
        # <--- PROMPT REFINADO COM LÓGICA DE PRIORIDADE CORRETA ---
        prompt = f"""
        Você é um assistente de gestão de estoque. Sua tarefa é criar uma lista de compras inteligente baseada nos dados do usuário.

        Dados do Usuário:
        - Inventário Atual: {inventario_str}
        - Histórico de Produtos Mais Usados: {historico_str}

        Sua lógica de recomendação DEVE seguir estas duas prioridades, em ordem:

        1.  **PRIORIDADE 1: Itens em Baixo Estoque (Análise Obrigatória):**
            Primeiro, analise o 'Inventário Atual'. Sugira a compra de qualquer item que esteja acabando.
            Considere 'baixo estoque':
            - Menos de 3 Unidades.
            - Menos de 500 Gramas (para itens medidos em g).
            - Menos de 500 Mililitros (para itens medidos em ml).
            Para estes itens, sugira uma quantidade de compra para reabastecer (ex: se tem 300g de Açúcar, sugira comprar 1 Kg).

        2.  **PRIORIDADE 2: Itens Frequentes e Ausentes (Análise Secundária):**
            Depois de verificar o estoque, analise o 'Histórico de Produtos'. Se houver algum item de alta frequência no histórico que NÃO ESTÁ no inventário atual, sugira sua compra.

        REGRAS DE FORMATAÇÃO (OBRIGATÓRIAS):
        - Para CADA item sugerido, forneça um PREÇO ESTIMADO realista(media) para supermercados no BRASIL(NADA IMPORTADO).
        - Atribua a CADA item UMA das seguintes categorias: {categorias_str}.
        - Formate CADA item EXATAMENTE assim: Nome do Produto - Quantidade Unidade - Categoria - R$ Preço
        - Se, após analisar o estoque baixo e o histórico, não houver NADA a recomendar, retorne uma resposta VAZIA.
        
        Exemplo:
        * Açúcar - 1 Kg - Mercearia - R$ 5,50
        * Abacaxi - 1 Unidade - Hortifruti - R$ 7,00
        * Frango (Peito) - 1 Kg - Proteínas - R$ 22,00
        """
        response = model.generate_content(prompt)
        return formatar_resposta_gemini(response.text)

    except Exception as e:
        messagebox.showerror("Erro de IA", f"Não foi possível gerar sugestões.\n\nDetalhe: {e}")
        return []

def buscar_produtos_sugeridos():
    conexao = conectar_mysql(db_host, db_name, db_usuario, db_senha)
    if not conexao: return []
    
    try:
        inventario_atual = buscar_inventario_usuario(conexao)
        historico_uso = buscar_historico_uso(conexao)

        # <--- LÓGICA DE CHAMADA CORRIGIDA: SÓ CHAMA A IA SE HOUVER DADOS ---
        if (inventario_atual or historico_uso) and model:
            print("Log: Encontrados dados de inventário/histórico. Gerando sugestões...")
            return recomendar_produtos_com_gemini(inventario_atual, historico_uso, CATEGORIAS_COMPRA)
        else:
            print("Log: Nenhum dado de inventário ou histórico para gerar sugestões.")
            return [] # Retorna lista vazia, como solicitado.
    finally:
        if conexao.is_connected():
            conexao.close()

# --- Funções de Manipulação da UI ---

def carregar_sugestoes_em_background():
    global lista_compras_data
    # A chamada de longa duração (que busca dados e chama a IA) acontece aqui
    sugestoes = buscar_produtos_sugeridos()
    lista_compras_data = sugestoes
    # Quando a busca termina, ela agenda a atualização da interface para
    # acontecer de forma segura na thread principal
    window.after(0, carregar_lista_compras)

def criar_item_lista(parent, produto):
    # (Esta função permanece sem alterações)
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
    if lista_compras_data is None:
        ctk.CTkLabel(lista_compras_inner_frame, text="Gerando sugestões com base na média...", font=ctk.CTkFont(size=20), text_color="gray").pack(pady=20, padx=10)
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
    # (Esta função permanece sem alterações)
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
        lista_compras_data.append(novo_item); carregar_lista_compras(); dialog.destroy()
    ctk.CTkButton(main_frame, text="Adicionar Item", command=adicionar_e_fechar).pack(fill="x", pady=(10,0))

def remover_item(item_to_remove):
    # (Esta função permanece sem alterações)
    try: lista_compras_data.remove(item_to_remove)
    except (ValueError, KeyError): pass
    carregar_lista_compras()

def remover_selecionados():
    # (Esta função permanece sem alterações)
    itens_para_remover = [p for p in lista_compras_data if p.get("checkbox_var") and p["checkbox_var"].get()]
    if not itens_para_remover: return
    for item in itens_para_remover: lista_compras_data.remove(item)
    carregar_lista_compras()

def salvar_lista():
    # (Esta função permanece sem alterações)
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

# --- Execução Principal da Aplicação ---
if __name__ == "__main__":
    window = ctk.CTk(); window.title("MyGeli - Lista de Compras"); window.configure(fg_color="#F5F5F5")
    window_width, window_height = 500, 700
    screen_width = window.winfo_screenwidth(); screen_height = window.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2); center_y = int(screen_height/2 - window_height/2)
    window.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
    window.grid_rowconfigure(1, weight=1); window.grid_columnconfigure(0, weight=1)
    
    header_frame = ctk.CTkFrame(window, height=80, corner_radius=0, fg_color="#0084FF"); header_frame.grid(row=0, column=0, sticky="new")
    header_frame.grid_propagate(False); header_frame.grid_columnconfigure(1, weight=1)
    
    # <--- BOTÃO DE VOLTAR ADICIONADO E FUNCIONAL ---
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
    ctk.CTkLabel(content_frame, text="As sugestões baseadas no seu consumo!\nOs preços são apenas médias de vários produtos!", font=ctk.CTkFont(size=12), text_color="#CE5959").grid(row=0, column=0, pady=(0, 15))

    
    lista_frame = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=10); lista_frame.grid(row=1, column=0, sticky="nsew")
    scrollable_frame = ctk.CTkScrollableFrame(lista_frame, fg_color="white"); scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)
    lista_compras_inner_frame = scrollable_frame
    
    botoes_frame = ctk.CTkFrame(content_frame, fg_color="transparent"); botoes_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
    botoes_frame.grid_columnconfigure(0, weight=1)
    ctk.CTkButton(botoes_frame, text="Adicionar Item", command=adicionar_item_manual, fg_color="#4caf50", hover_color="#45a049").grid(row=0, column=0, sticky="ew", pady=2)
    ctk.CTkButton(botoes_frame, text="Remover Selecionados", command=remover_selecionados, fg_color="#f44336", hover_color="#d32f2f").grid(row=1, column=0, sticky="ew", pady=2)
    ctk.CTkButton(botoes_frame, text="Salvar Lista (.txt)", command=salvar_lista, fg_color="#2196f3", hover_color="#1976d2").grid(row=2, column=0, sticky="ew", pady=2)

    # --- Inicialização ---
    carregar_lista_compras() 
    
    background_thread = threading.Thread(target=carregar_sugestoes_em_background)
    background_thread.daemon = True
    background_thread.start()
    
    window.mainloop()