import customtkinter as ctk
from datetime import datetime
from pathlib import Path
import mysql.connector
from mysql.connector import Error
import google.generativeai as genai
import os
import re
from tkinter import messagebox

# --- Constantes e Configurações ---
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets" / "frame1"

# --- Variáveis Globais da UI ---
lista_compras_canvas = None
lista_compras_inner_frame = None
window = None
lista_compras_data = []

# --- SUAS CREDENCIAIS (CORRIGIDAS) ---
# Credenciais alinhadas com o arquivo gui3.py
db_host = "localhost"
db_name = "mygeli"
db_usuario = "foodyzeadm"
db_senha = "supfood0017admx"

# --- CONFIGURAÇÃO DA API GEMINI (Padrão gui3.py) ---
model = None # A instância do modelo da IA será armazenada aqui
try:
    # A chave é importada de gui0.py para manter a consistência com seu app
    from gui0 import GOOGLE_API_KEY
    if GOOGLE_API_KEY and GOOGLE_API_KEY != "SUA_CHAVE_API_AQUI":
        genai.configure(api_key=GOOGLE_API_KEY)
        # Usando o mesmo modelo do gui3.py para consistência
        model = genai.GenerativeModel('gemini-2.5-flash')
        print("Log: API do Gemini configurada com sucesso com o modelo 'gemini-2.5-flash'.")
    else:
        print("AVISO: GOOGLE_API_KEY não encontrada em gui0.py ou é um placeholder. Funções de IA usarão dados simulados.")
        messagebox.showwarning("Aviso de IA", "Chave da API não encontrada. Usando sugestões simuladas.")

except ImportError:
    print("AVISO: Arquivo gui0.py não encontrado. As sugestões de IA usarão dados simulados.")
    messagebox.showwarning("Aviso de IA", "Arquivo gui0.py não encontrado para carregar a chave da API.")
except Exception as e:
    print(f"AVISO: Não foi possível configurar a API do Gemini. Funções de IA estarão desabilitadas. Erro: {e}")
    messagebox.showerror("Erro de API", f"Não foi possível configurar a API do Gemini: {e}")


# --- Funções de Conexão e Lógica do Negócio ---

def conectar_mysql(host, database, user, password):
    """ Tenta conectar ao banco de dados MySQL (método do gui3.py). """
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
            print(f"Você está conectado ao banco de dados: {record[0]}")
            return conexao
    except Error as e:
        print(f"Log: Erro CRÍTICO ao conectar ao MySQL: {e}")
        messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao banco de dados:\n{e}\n\nVerifique suas credenciais e se o servidor MySQL está rodando.")
        return None

def buscar_inventario_usuario(conexao):
    """
    Busca o inventário atual do usuário no banco de dados.
    Esta função agora executa uma consulta SQL real.
    """
    if not conexao or not conexao.is_connected():
        print("Não foi possível buscar o inventário: sem conexão com o banco de dados.")
        return []

    inventario = []
    # CORREÇÃO FINAL: A condição "WHERE usuario_id" foi removida,
    # pois a tabela 'produtos' não possui essa coluna.
    query = "SELECT nome_produto, quantidade_produto AS quantidade, tipo_volume AS unidade FROM produtos"

    cursor = None # Inicializa o cursor
    try:
        # O 'with' foi removido, pois causava o TypeError.
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(query)
        resultados = cursor.fetchall()
        # O cursor com dictionary=True já retorna uma lista de dicionários
        inventario = resultados
        print(f"Inventário encontrado: {inventario}")

    except mysql.connector.Error as e:
        print(f"Erro ao executar a consulta de inventário: {e}")
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível buscar os dados do inventário:\n{e}")
        return []
    finally:
        # Garante que o cursor seja fechado
        if cursor:
            cursor.close()

    return inventario

def buscar_historico_uso(conexao):
    """
    Busca os ingredientes mais utilizados pelo usuário no histórico.
    """
    if not conexao or not conexao.is_connected():
        print("Não foi possível buscar o histórico: sem conexão com o banco de dados.")
        return []

    historico = []
    # Query para buscar os 10 ingredientes mais usados
    query = """
        SELECT nome_ingrediente, COUNT(*) as frequencia
        FROM historico_uso
        GROUP BY nome_ingrediente
        ORDER BY frequencia DESC
        LIMIT 10
    """

    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(query)
        resultados = cursor.fetchall()
        historico = [item['nome_ingrediente'] for item in resultados] # Extrai apenas os nomes
        print(f"Histórico de uso encontrado: {historico}")

    except Error as e:
        print(f"Erro ao executar a consulta de histórico de uso: {e}")
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível buscar o histórico de uso:\n{e}")
        return []
    finally:
        if cursor:
            cursor.close()

    return historico

def formatar_resposta_gemini(texto_gemini):
    """
    Analisa a saída de texto do Gemini e a formata em uma lista de dicionários.
    O formato esperado é: 'Nome do Produto - Quantidade Unidade'.
    """
    if not texto_gemini:
        print("A resposta da API Gemini estava vazia.")
        return []

    itens_formatados = []
    # Regex melhorado para mais flexibilidade com espaços e caracteres
    padrao = re.compile(
        r'^\s*[\*\-]?\s*(?P<nome>.+?)\s*-\s*(?P<quantidade>[\d.,]+)\s*(?P<unidade>[a-zA-ZáéíóúÁÉÍÓÚçÇ\s/]+)\s*$',
        re.IGNORECASE | re.MULTILINE
    )

    print("\n--- Resposta Bruta da API Gemini ---")
    print(texto_gemini)
    print("------------------------------------")

    for linha in texto_gemini.split('\n'):
        linha = linha.strip()
        if not linha:
            continue

        match = padrao.search(linha)
        if match:
            try:
                nome = match.group('nome').strip()
                quantidade_str = match.group('quantidade').replace(',', '.').strip()
                unidade = match.group('unidade').strip()

                # Tenta converter para float, e se for um número inteiro, converte para int
                quantidade = float(quantidade_str)
                if quantidade == int(quantidade):
                    quantidade = int(quantidade)

                item = {"nome": nome, "quantidade": quantidade, "unidade": unidade}
                itens_formatados.append(item)
                print(f"Item processado: {item}")

            except (ValueError, IndexError) as e:
                print(f"Erro ao processar a linha do Gemini: '{linha}'. Erro: {e}")
        else:
            print(f"Linha fora do padrão esperado, ignorada: '{linha}'")

    return itens_formatados

def recomendar_produtos_com_gemini(inventario, historico):
    """
    Usa a API do Google Gemini para sugerir ingredientes com base no inventário e no histórico de uso.
    """
    # Agora verifica se a instância global 'model' foi criada com sucesso.
    if not model:
        print("Modelo da IA não inicializado. Usando dados simulados.")
        return None

    try:
        # Formatar inventário para o prompt de forma mais legível
        if inventario:
            # Acessando as chaves corretas ('quantidade', 'unidade') que foram apelidadas na query SQL
            itens_inventario = "\n".join([f"- {item['nome_produto']} ({item['quantidade']} {item['unidade']})" for item in inventario])
            prompt_inventario = f"Atualmente, tenho os seguintes itens na minha cozinha:\n{itens_inventario}\n\n"
        else:
            prompt_inventario = "Meu inventário de cozinha está vazio.\n\n"

        # Formatar histórico de uso para o prompt
        if historico:
            itens_historico = ", ".join(historico)
            prompt_historico = f"Os ingredientes que eu mais uso em minhas receitas são: {itens_historico}.\n\n"
        else:
            prompt_historico = ""


        prompt = (
            f"{prompt_inventario}"
            f"{prompt_historico}"
            "Com base no que eu tenho no inventário e nos ingredientes que mais uso, "
            "gere uma lista de compras inteligente com 8 itens que provavelmente estão faltando para complementar minhas receitas habituais. "
            "A resposta deve conter APENAS a lista, com um item por linha. "
            "Siga ESTRITAMENTE o formato: 'Nome do Produto - Quantidade Unidade'.\n"
            "Exemplos:\n"
            "Farinha de Trigo - 1 Kg\n"
            "Açúcar - 500 g\n"
            "Óleo de Soja - 1 Litro\n"
            "Não inclua títulos, introduções, resumos ou qualquer outro texto."
        )

        print("Enviando prompt ao Gemini...")
        # Usa a instância global 'model' que já foi configurada.
        response = model.generate_content(prompt)

        return formatar_resposta_gemini(response.text)

    except Exception as e:
        print(f"Erro na chamada da API Gemini: {e}")
        messagebox.showerror("Erro de IA", f"Não foi possível obter sugestões da IA:\n{e}")
        return None


def buscar_produtos_sugeridos(conexao):
    """
    Orquestra a busca por produtos sugeridos usando uma conexão de BD existente.
    """
    produtos_sugeridos = []

    if conexao:
        inventario_atual = buscar_inventario_usuario(conexao)
        historico_uso = buscar_historico_uso(conexao)

        # Tenta gerar sugestões com a IA (verifica se 'model' foi inicializado)
        if model:
            produtos_sugeridos = recomendar_produtos_com_gemini(inventario_atual, historico_uso)

    # Fallback: Se a IA falhou, não retornou nada, ou não está configurada
    if not produtos_sugeridos:
        print("Usando sugestões simuladas (Fallback).")
        produtos_sugeridos = [
            {"nome": "Café", "quantidade": 500, "unidade": "g"},
            {"nome": "Manteiga", "quantidade": 1, "unidade": "Tablete"},
            {"nome": "Pão de Forma", "quantidade": 1, "unidade": "Pacote"},
            {"nome": "Tomate", "quantidade": 600, "unidade": "g"},
            {"nome": "Queijo Mussarela", "quantidade": 300, "unidade": "g"},
            {"nome": "Macarrão", "quantidade": 2, "unidade": "Pacotes"},
            {"nome": "Molho de Tomate", "quantidade": 1, "unidade": "Caixa"}
        ]

    return produtos_sugeridos

# --- Funções de UI (Mantidas com pequenas melhorias) ---

def criar_item_lista(parent, produto, index):
    """Cria um item da lista de compras na interface"""
    item_frame = ctk.CTkFrame(parent, height=60, fg_color="#3B82F6", corner_radius=10)
    item_frame.pack(fill="x", padx=10, pady=5)
    item_frame.pack_propagate(False)

    checkbox_var = ctk.BooleanVar()
    checkbox = ctk.CTkCheckBox(item_frame, text="", variable=checkbox_var, width=20)
    checkbox.pack(side="left", padx=(10, 15), pady=15)

    nome_label = ctk.CTkLabel(item_frame, text=produto["nome"], font=ctk.CTkFont(size=14, weight="bold"), width=200, anchor="w")
    nome_label.pack(side="left", padx=(0, 10), pady=15)

    # Formatação da quantidade para exibição
    try:
        qtd_str = f"{produto['quantidade']:.2f}".rstrip('0').rstrip('.') if isinstance(produto['quantidade'], float) else str(produto['quantidade'])
    except:
        qtd_str = str(produto['quantidade'])

    quantidade_label = ctk.CTkLabel(item_frame, text=f"{qtd_str} {produto['unidade']}", font=ctk.CTkFont(size=12), width=120, anchor="w")
    quantidade_label.pack(side="left", padx=(0, 10), pady=15)

    remover_btn = ctk.CTkButton(item_frame, text="Remover", width=80, height=30, font=ctk.CTkFont(size=11), fg_color="#d32f2f", hover_color="#b71c1c", command=lambda item=produto: remover_item(item))
    remover_btn.pack(side="right", padx=(10, 10), pady=15)

    produto["checkbox_var"] = checkbox_var
    produto["frame"] = item_frame

    return item_frame, checkbox_var

def carregar_lista_compras():
    """Carrega e exibe a lista de compras sugerida na UI"""
    global lista_compras_data, lista_compras_inner_frame
    if lista_compras_inner_frame:
        for widget in lista_compras_inner_frame.winfo_children():
            widget.destroy()

    if not lista_compras_data:
        info_label = ctk.CTkLabel(lista_compras_inner_frame, text="Nenhuma sugestão encontrada.", font=ctk.CTkFont(size=14), text_color="gray")
        info_label.pack(pady=20)
        return

    for index, produto in enumerate(lista_compras_data):
        criar_item_lista(lista_compras_inner_frame, produto, index)

def adicionar_item_manual():
    """Abre diálogo para adicionar item manualmente"""
    nome_dialog = ctk.CTkInputDialog(text="Digite o nome do produto:", title="Adicionar Item")
    nome = nome_dialog.get_input()
    if not nome: return

    qtd_dialog = ctk.CTkInputDialog(text="Digite a quantidade:", title="Quantidade")
    quantidade_str = qtd_dialog.get_input()
    if not quantidade_str: return

    unidade_dialog = ctk.CTkInputDialog(text="Digite a unidade (ex: Kg, g, Litros):", title="Unidade")
    unidade = unidade_dialog.get_input()
    if not unidade: return

    novo_item = {"nome": nome, "quantidade": quantidade_str, "unidade": unidade}
    lista_compras_data.append(novo_item)
    carregar_lista_compras()
    messagebox.showinfo("Sucesso", f"Item '{nome}' adicionado à lista!")

def remover_item(item_to_remove):
    """Remove um item da lista"""
    global lista_compras_data
    try:
        # Destruir o frame do item antes de remover da lista de dados
        if "frame" in item_to_remove and item_to_remove["frame"]:
            item_to_remove["frame"].destroy()
        lista_compras_data.remove(item_to_remove)
        messagebox.showinfo("Item Removido", f"'{item_to_remove['nome']}' foi removido da lista.")
    except ValueError:
        messagebox.showwarning("Erro", "Item não encontrado na lista.")
    # Atualiza a lista caso ela fique vazia
    if not lista_compras_data:
        carregar_lista_compras()


def remover_selecionados():
    """Remove todos os itens selecionados"""
    global lista_compras_data
    itens_para_remover = [p for p in lista_compras_data if "checkbox_var" in p and p["checkbox_var"].get()]

    if not itens_para_remover:
        messagebox.showwarning("Nenhum Item Selecionado", "Selecione pelo menos um item para remover.")
        return

    for item in itens_para_remover:
        remover_item(item) # Reutiliza a função de remover item individual

    messagebox.showinfo("Itens Removidos", f"{len(itens_para_remover)} item(s) removido(s) da lista.")

def salvar_lista():
    """Salva a lista de compras atual em um arquivo de texto"""
    if not lista_compras_data:
        messagebox.showwarning("Lista Vazia", "Não há itens na lista para salvar.")
        return

    try:
        lista_path = OUTPUT_PATH / "lista_de_compras.txt"
        with open(lista_path, "w", encoding="utf-8") as file:
            file.write("=== MINHA LISTA DE COMPRAS ===\n")
            file.write(f"Gerada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            for index, produto in enumerate(lista_compras_data, 1):
                file.write(f"{index}. {produto['nome']} - {produto['quantidade']} {produto['unidade']}\n")
            file.write(f"\nTotal de itens: {len(lista_compras_data)}")
        messagebox.showinfo("Lista Salva", f"Sua lista de compras foi salva em:\n{lista_path}")
    except Exception as e:
        messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro ao salvar a lista:\n{e}")

def abrir_gui4(db_connection):
    """Função principal para criar e rodar a GUI, usando uma conexão existente."""
    global window, lista_compras_canvas, lista_compras_inner_frame, lista_compras_data

    window = ctk.CTk()
    window.geometry("800x600")
    window.title("MyGeli - Lista de Compras Inteligente")
    window.configure(fg_color="#f0f0f0")

    # --- Gerenciamento de Conexão ---
    # Função para ser chamada quando a janela for fechada
    def on_closing():
        if db_connection and db_connection.is_connected():
            db_connection.close()
            print("Conexão com o banco de dados fechada ao sair.")
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", on_closing)


    ctk.CTkLabel(window, text="Lista de Compras Inteligente", font=ctk.CTkFont(size=24, weight="bold"), text_color="#2e7d32").pack(pady=(20, 10))
    ctk.CTkLabel(window, text="Sugestões baseadas no seu inventário e IA", font=ctk.CTkFont(size=14), text_color="#666666").pack(pady=(0, 20))

    main_frame = ctk.CTkFrame(window, fg_color="white")
    main_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    lista_compras_canvas = ctk.CTkScrollableFrame(main_frame, fg_color="white")
    lista_compras_canvas.pack(fill="both", expand=True, padx=10, pady=10)
    lista_compras_inner_frame = lista_compras_canvas

    botoes_frame = ctk.CTkFrame(window, fg_color="transparent")
    botoes_frame.pack(fill="x", padx=20, pady=(0, 20), anchor="center")

    btn_adicionar = ctk.CTkButton(botoes_frame, text="Adicionar Item", width=160, height=40, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#4caf50", hover_color="#45a049", command=adicionar_item_manual)
    btn_adicionar.pack(side="left", expand=True, padx=5)

    btn_remover = ctk.CTkButton(botoes_frame, text="Remover Selecionados", width=160, height=40, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#f44336", hover_color="#d32f2f", command=remover_selecionados)
    btn_remover.pack(side="left", expand=True, padx=5)

    btn_salvar = ctk.CTkButton(botoes_frame, text="Salvar Lista", width=160, height=40, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#2196f3", hover_color="#1976d2", command=salvar_lista)
    btn_salvar.pack(side="left", expand=True, padx=5)

    # Inicia com uma mensagem de carregamento
    loading_label = ctk.CTkLabel(lista_compras_inner_frame, text="Gerando sugestões...", font=ctk.CTkFont(size=14))
    loading_label.pack(pady=20)
    window.update() # Força a atualização da UI para mostrar a mensagem

    # Carrega os dados usando a conexão passada e depois atualiza a lista
    lista_compras_data = buscar_produtos_sugeridos(db_connection)
    loading_label.destroy() # Remove a mensagem de carregamento
    carregar_lista_compras()

    window.mainloop()

if __name__ == "__main__":
    # Estabelece a conexão ANTES de iniciar a interface gráfica
    conexao = conectar_mysql(db_host, db_name, db_usuario, db_senha)
    
    # Se a conexão for bem-sucedida, abre a janela
    if conexao:
        abrir_gui4(conexao)

