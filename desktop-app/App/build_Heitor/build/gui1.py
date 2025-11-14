import customtkinter as ctk
import subprocess
import sys
import mysql.connector
from mysql.connector import Error, IntegrityError # Importa IntegrityError
from pathlib import Path
from PIL import Image, ImageSequence

from werkzeug.security import check_password_hash, generate_password_hash
from session_manager import SessionManager
from tkinter import messagebox
import re # Para validação Regex de email e nome

import socket
import hashlib

# --- Conexão com Banco de Dados ---
def conectar_mysql(host, database, user, password):
    """
    Tenta conectar ao banco de dados MySQL. Retorna a conexão ou None.
    """
    try:
        conexao = mysql.connector.connect(host=host, database=database, user=user, password=password)
        if conexao.is_connected():
            print("Log: Conexão ao MySQL bem-sucedida!")
            return conexao
    except Error as e:
        print(f"Log: Erro ao conectar ao MySQL: {e}")
        return None

# --- Navegação entre Telas ---
def abrir_gui(nome_arquivo):
    """Fecha a janela atual e abre um novo script de GUI."""
    if app:
        app.destroy()
    try:
        caminho_script = str(Path(__file__).parent / nome_arquivo)
        subprocess.Popen([sys.executable, caminho_script])
    except Exception as e:
        print(f"Erro ao tentar abrir {nome_arquivo}: {e}")
        
def _get_hashed_ip():
    """Obtém o IP local e o criptografa (hash SHA-256) como no Flask."""
    try:
        # Tenta pegar o IP local da máquina
        ip_address = socket.gethostbyname(socket.gethostname())
    except Exception:
        # Fallback se não conseguir (ex: sem rede)
        ip_address = '127.0.0.1'
    
    # Criptografa (hash) o IP
    hashed_ip = hashlib.sha256(ip_address.encode('utf-8')).hexdigest()
    return hashed_ip

# --- Classe Principal da Aplicação ---
class App(ctk.CTk):
    """
    A tela principal (menu) do aplicativo MyGeli.
    """
    # --- Constantes de Estilo para Padronização ---
    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 650
    BG_COLOR = "#F5F5F5"
    HEADER_COLOR = "#0084FF"
    BUTTON_COLOR = "#0084FF"
    BUTTON_HOVER_COLOR = "#0066CC"
    BUTTON_TEXT_COLOR = "white"
    CARD_COLOR = "#FFFFFF"
    CARD_BORDER_COLOR = "#E0E0E0"
    BUTTON_DISABLED_COLOR = "#B0B0B0" # Um tom de cinza
    BUTTON_DANGER_COLOR = "#D32F2F" # Vermelho
    BUTTON_DANGER_HOVER_COLOR = "#B71C1C" # Vermelho escuro

    def __init__(self, db_connection):
        super().__init__()
        
        self.db_connection = db_connection
        self.gif_frames = []
        self.current_frame_index = 0
        
        self.session_manager = SessionManager()
        session_data = self.session_manager.get_session()
        
        self.user_id = session_data.get("user_id")
        self.user_first_name = session_data.get("first_name")
        
        self._validar_sessao_no_db()

        self._configurar_janela()
        self._criar_fontes()
        self._criar_widgets()
        
        self._atualizar_estado_login()

    def _configurar_janela(self):
        # (Função idêntica, sem mudanças)
        self.title("MyGeli")
        ctk.set_appearance_mode("light")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int(screen_width / 2 - self.WINDOW_WIDTH / 2)
        center_y = int(screen_height / 2 - self.WINDOW_HEIGHT / 2)
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{center_x}+{center_y}")
        self.minsize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.maxsize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.configure(fg_color=self.BG_COLOR)

    def _criar_fontes(self):
        # --- VERSÃO CORRIGIDA (todas as fontes) ---
        self.large_font = ctk.CTkFont("Poppins Bold", 28)
        self.medium_font = ctk.CTkFont("Poppins Medium", 18)
        self.small_font = ctk.CTkFont("Poppins Light", 14)
        self.button_font = ctk.CTkFont("Poppins SemiBold", 18)
        self.link_font = ctk.CTkFont("Poppins Light", 12, underline=True)
        self.small_light_font = ctk.CTkFont("Poppins Light", 12)
        self.header_name_font = ctk.CTkFont("Poppins SemiBold", 16)


    def _criar_widgets(self):
        # (Função idêntica, sem mudanças)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        header_frame = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color=self.HEADER_COLOR)
        header_frame.grid(row=0, column=0, sticky="new")
        header_frame.grid_propagate(False)
        assets_path = Path(__file__).parent / "assets" / "frame1"
        user_icon_image = ctk.CTkImage(Image.open(assets_path / "user_icon.png").resize((32, 32), Image.LANCZOS), size=(40, 40))
        user_button = ctk.CTkButton(header_frame, text="", image=user_icon_image, width=45, height=45, fg_color="transparent", hover_color=self.BUTTON_HOVER_COLOR, command=self._acao_usuario)
        user_button.pack(side="left", padx=10, pady=10)
        self.user_name_label = ctk.CTkLabel(header_frame, text="", font=self.header_name_font, text_color=self.BUTTON_TEXT_COLOR)
        options_image = ctk.CTkImage(Image.open(assets_path / "options.png").resize((32, 32), Image.LANCZOS), size=(30, 30))
        options_button = ctk.CTkButton(header_frame, text="", image=options_image, width=40, height=40, fg_color="transparent", hover_color=self.BUTTON_HOVER_COLOR, command=None)
        options_button.pack(side="right", padx=5, pady=5)
        calendario_image = ctk.CTkImage(Image.open(assets_path / "calendario.png").resize((32, 32), Image.LANCZOS), size=(30, 30))
        calendario_button = ctk.CTkButton(header_frame, text="", image=calendario_image, width=40, height=40, fg_color="transparent", hover_color=self.BUTTON_HOVER_COLOR, command=lambda: self._abrir_gui_com_verificacao("gui5_planejamento.py"))
        calendario_button.pack(side="right", padx=5, pady=5)
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew")
        content_block_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_block_frame.pack(side="top", fill="x", pady=(50, 0))
        logo_completo_path = assets_path / "MyGeli.png"
        original_logo_image = Image.open(logo_completo_path)
        original_width, original_height = original_logo_image.size
        target_width = 280
        aspect_ratio = original_height / original_width
        target_height = int(target_width * aspect_ratio)
        resized_logo = original_logo_image.resize((target_width, target_height), Image.LANCZOS)
        logo_image = ctk.CTkImage(light_image=resized_logo, size=(target_width, target_height))
        ctk.CTkLabel(content_block_frame, image=logo_image, text="").pack(pady=(0, 30))
        buttons_frame = ctk.CTkFrame(content_block_frame, fg_color=self.CARD_COLOR, corner_radius=12, border_color=self.CARD_BORDER_COLOR, border_width=1)
        buttons_frame.pack(padx=30, fill="x")
        buttons_frame.grid_columnconfigure(0, weight=1)
        self.btn_geli = ctk.CTkButton(buttons_frame, text="FALAR COM GELI", command=lambda: self._abrir_gui_com_verificacao("gui0.py"), 
                                        height=55, font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
        self.btn_geli.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.btn_receitas = ctk.CTkButton(buttons_frame, text="VER RECEITAS", command=lambda: self._abrir_gui_com_verificacao("gui2.py"), 
                                        height=55, font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
        self.btn_receitas.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.btn_estoque = ctk.CTkButton(buttons_frame, text="GERENCIAR ESTOQUE", command=lambda: self._abrir_gui_com_verificacao("gui3.py"), 
                                        height=55, font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
        self.btn_estoque.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.btn_compras = ctk.CTkButton(buttons_frame, text="LISTA DE COMPRAS", command=lambda: self._abrir_gui_com_verificacao("gui4.py"), 
                                        height=55, font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
        self.btn_compras.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")

    def _abrir_gui_com_verificacao(self, nome_arquivo):
        # (Função idêntica, sem mudanças)
        if self.user_id:
            abrir_gui(nome_arquivo)
        else:
            messagebox.showwarning("Acesso Restrito", 
                                   "Entre em uma conta para utilizar a ferramenta!")
    
    # --- MODIFICADO: Esta função agora abre a janela de OPÇÕES ---
    def _acao_usuario(self):
        """
        Verifica se o usuário está logado.
        Se sim, abre a janela de opções. Se não, abre a tela de login.
        """
        if self.user_id:
            # --- ABRE A NOVA JANELA DE OPÇÕES ---
            if hasattr(self, 'opcoes_window') and self.opcoes_window.winfo_exists():
                self.opcoes_window.focus()
                return

            self.opcoes_window = ctk.CTkToplevel(self)
            self.opcoes_window.title("Opções da Conta")
            self.opcoes_window.geometry("300x200") # Tamanho da nova janela
            self.opcoes_window.transient(self)
            self.opcoes_window.grab_set()
            self.opcoes_window.resizable(False, False)
            
            # Centralizar
            x_app = self.winfo_x()
            y_app = self.winfo_y()
            w_app = self.winfo_width()
            h_app = self.winfo_height()
            x_opcoes = x_app + (w_app // 2) - (300 // 2)
            y_opcoes = y_app + (h_app // 2) - (200 // 2)
            self.opcoes_window.geometry(f"300x200+{x_opcoes}+{y_opcoes}")

            ctk.CTkLabel(self.opcoes_window, text=f"Opções para {self.user_first_name}", font=self.medium_font).pack(pady=(20, 15))

            # Botão Sair
            btn_sair = ctk.CTkButton(self.opcoes_window, text="Sair da Conta",
                                     command=self._confirmar_logout, 
                                     font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
            btn_sair.pack(pady=10, padx=20, fill="x")

            # Botão Excluir
            btn_excluir = ctk.CTkButton(self.opcoes_window, text="Excluir Conta",
                                        command=self._confirmar_exclusao, 
                                        font=self.button_font, fg_color=self.BUTTON_DANGER_COLOR, hover_color=self.BUTTON_DANGER_HOVER_COLOR) # Cor de perigo
            btn_excluir.pack(pady=10, padx=20, fill="x")
            
        else:
            # Usuário não está logado, abrir tela de login
            self._abrir_tela_login()

    # --- ADICIONADO: Funções de Logout e Exclusão ---
    
    def _validar_sessao_no_db(self):
        """
        Verifica se o user_id da sessão ainda existe no banco de dados.
        Se não existir (ex: usuário foi excluído), limpa a sessão.
        """
        if not self.user_id:
            return  # Nenhuma sessão para validar

        # Se não há conexão no início, não é possível validar.
        # É mais seguro deslogar o usuário.
        if not self.db_connection or not self.db_connection.is_connected():
            print("Log: Sessão não pode ser validada (BD offline). Limpando.")
            self.user_id = None
            self.user_first_name = None
            self.session_manager.clear_session()
            return

        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("SELECT id, nome FROM usuarios WHERE id = %s", (self.user_id,))
            user = cursor.fetchone()
            cursor.close()

            if not user:
                # O usuário NÃO existe mais no DB (o seu caso do user 5!)
                print(f"Log: Usuário da sessão (ID: {self.user_id}) não encontrado no DB. Limpando sessão.")
                self.user_id = None
                self.user_first_name = None
                self.session_manager.clear_session()
            else:
                # O usuário existe. Apenas confirma os dados.
                # Atualiza o nome caso tenha mudado no banco
                self.user_first_name = user['nome'].split(' ')[0]
                print(f"Log: Sessão (ID: {self.user_id}) validada com sucesso no DB.")

        except Error as e:
            print(f"Log: Erro de MySQL ao validar sessão: {e}")
            # Em caso de erro de DB, é mais seguro deslogar.
            self.user_id = None
            self.user_first_name = None
            self.session_manager.clear_session()
            
    def _registrar_log(self, user_id, action, status):
        """
        Registra uma ação na tabela 'log' do banco de dados.
        """
        if not self.db_connection or not self.db_connection.is_connected():
            print(f"Log: Conexão de BD ausente. Log de '{action}' não registrado.")
            return

        cursor = None
        try:
            hashed_ip = _get_hashed_ip() # Chama a função global
            
            cursor = self.db_connection.cursor()
            query = """
                INSERT INTO log (id_user, action, status, ip_address) 
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (user_id, action, status, hashed_ip))
            self.db_connection.commit()
            print(f"Log: Ação '{action}' registrada para user_id {user_id}.")

        except Error as e:
            print(f"Log: ERRO ao registrar log: {e}")
            if self.db_connection:
                self.db_connection.rollback()
        finally:
            if cursor:
                cursor.close()

    def _confirmar_logout(self):
        """Pede confirmação para sair."""
        # Tira o foco da janela de opções para o messagebox aparecer na frente
        self.opcoes_window.grab_release() 
        resposta = messagebox.askyesno("Sair", "Tem certeza que deseja sair da sua conta?", parent=self.opcoes_window)
        if resposta: # "Sim"
            self._executar_logout()
        else:
            # Devolve o foco para a janela de opções
            self.opcoes_window.grab_set() 
            self.opcoes_window.focus()

    def _executar_logout(self):
        """Limpa a sessão e atualiza a GUI."""
        if self.user_id:
            self._registrar_log(self.user_id, 'Logout', 'Success')
        
        if hasattr(self, 'opcoes_window') and self.opcoes_window.winfo_exists():
            self.opcoes_window.destroy()
            
        self.session_manager.clear_session()
        self.user_id = None
        self.user_first_name = None
        self._atualizar_estado_login()

    def _confirmar_exclusao(self):
        """Pede a confirmação final antes de excluir a conta."""
        self.opcoes_window.grab_release()
        resposta = messagebox.askyesno("EXCLUIR CONTA", 
                                       f"ATENÇÃO, {self.user_first_name}!\n\nVocê tem CERTEZA?\n\nEsta ação é IRREVERSÍVEL e apagará TODOS os seus dados (estoque, receitas, etc.) permanentemente.", 
                                       icon="warning", parent=self.opcoes_window)
        if resposta:
            self._executar_exclusao_conta()
        else:
            self.opcoes_window.grab_set()
            self.opcoes_window.focus()
            
    def _executar_exclusao_conta(self):
        """Executa os comandos SQL para apagar todos os dados do usuário."""
        if not self.user_id:
            messagebox.showerror("Erro de Sessão", "Sessão não encontrada. Não é possível excluir a conta.", parent=self)
            return

        if not self.db_connection or not self.db_connection.is_connected():
            messagebox.showerror("Erro de Conexão", "Erro de conexão com o banco. Tente novamente.", parent=self)
            self.db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)
            if not self.db_connection: return

        cursor = None # Define o cursor como None fora do try
        try:
            print(f"Log: EXCLUINDO todos os dados do usuário {self.user_id}...")
            cursor = self.db_connection.cursor()
            
            # 1. Excluir dados dependentes (FK)
            # (Adicione outras tabelas aqui se elas dependerem do user_id)
            cursor.execute("DELETE FROM produtos WHERE user_id = %s", (self.user_id,))
            print(f"Log: {cursor.rowcount} produtos excluídos.")
            
            cursor.execute("DELETE FROM receitas WHERE idusuario = %s", (self.user_id,))
            print(f"Log: {cursor.rowcount} receitas excluídas.")
            
            cursor.execute("DELETE FROM login_tokens WHERE user_id = %s", (self.user_id,))
            print(f"Log: {cursor.rowcount} tokens de login excluídos.")

            # 2. Finalmente, excluir o usuário
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (self.user_id,))
            print(f"Log: {cursor.rowcount} usuário excluído.")

            self.db_connection.commit()
            
            messagebox.showinfo("Conta Excluída", "Sua conta foi excluída permanentemente.")
            
            # Faz o logout para limpar a UI
            self._executar_logout()

        except Error as e:
            self.db_connection.rollback()
            messagebox.showerror("Erro no Banco de Dados", f"Não foi possível excluir sua conta:\n{e}", parent=self)
            print(f"Log: Erro de MySQL ao excluir conta: {e}")
        finally:
            # --- CORREÇÃO DO ERRO ---
            # Apenas fechamos o cursor se ele foi criado com sucesso
            if cursor:
                cursor.close()
    
    # --- FIM DAS NOVAS FUNÇÕES ---

    def _abrir_tela_login(self):
        # --- VERSÃO CORRIGIDA (altura da janela e pady) ---
        if hasattr(self, 'login_window') and self.login_window.winfo_exists():
            self.login_window.focus()
            return
            
        self.login_window = ctk.CTkToplevel(self)
        self.login_window.title("Login MyGeli")
        self.login_window.geometry("350x350") # <-- CORRIGIDO
        self.login_window.transient(self)
        self.login_window.grab_set()
        self.login_window.resizable(False, False)
        
        x_app = self.winfo_x()
        y_app = self.winfo_y()
        w_app = self.winfo_width()
        h_app = self.winfo_height()
        x_login = x_app + (w_app // 2) - (350 // 2)
        y_login = y_app + (h_app // 2) - (350 // 2) # <-- CORRIGIDO
        self.login_window.geometry(f"350x350+{x_login}+{y_login}") # <-- CORRIGIDO
        
        ctk.CTkLabel(self.login_window, text="Login", font=self.large_font).pack(pady=(20, 10))
        ctk.CTkLabel(self.login_window, text="E-mail:", font=self.small_font, anchor="w").pack(fill="x", padx=40)
        email_entry = ctk.CTkEntry(self.login_window, width=270, height=35)
        email_entry.pack(pady=(0, 10))
        ctk.CTkLabel(self.login_window, text="Senha:", font=self.small_font, anchor="w").pack(fill="x", padx=40)
        senha_entry = ctk.CTkEntry(self.login_window, width=270, height=35, show="*")
        senha_entry.pack(pady=(0, 10))
        error_label = ctk.CTkLabel(self.login_window, text="", text_color="red", font=self.small_font)
        error_label.pack()
        
        ctk.CTkButton(self.login_window, text="Entrar", width=270, height=40, font=self.button_font,
                      command=lambda: self._executar_login(email_entry, senha_entry, error_label)
                      ).pack(pady=(10, 5)) # <-- CORRIGIDO
                      
        link_cadastro = ctk.CTkLabel(self.login_window, text="Não tem uma conta? Crie uma.", text_color="#0066CC",
                                       font=self.link_font, cursor="hand2")
        link_cadastro.pack(pady=(5, 10)) # <-- CORRIGIDO
        link_cadastro.bind("<Button-1>", lambda e: self._abrir_tela_cadastro())

    def _executar_login(self, email_entry, senha_entry, error_label):
        # (Função idêntica, sem mudanças)
        email = email_entry.get().strip()
        senha = senha_entry.get()
        if not email or not senha:
            error_label.configure(text="Preencha todos os campos.")
            return
        if not self.db_connection or not self.db_connection.is_connected():
            error_label.configure(text="Erro de conexão com o banco.")
            self.db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)
            return
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            query = "SELECT id, nome, email, senha FROM usuarios WHERE email = %s"
            cursor.execute(query, (email,))
            user = cursor.fetchone()
            cursor.close()
            if not user:
                error_label.configure(text="E-mail incorreto! Tente novamente.")
                return
            if not check_password_hash(user['senha'], senha):
                error_label.configure(text="Senha incorreta! Tente novamente.")
                self._registrar_log(user['id'], 'Login', 'Failure')
                return
            
            self._registrar_log(user['id'], 'Login', 'Success')
            
            self.user_id = user['id']
            full_name = user['nome']
            self.user_first_name = full_name.split(' ')[0]
            self.session_manager.save_session(self.user_id, self.user_first_name)
            self._atualizar_estado_login()
            self.login_window.destroy()
        except Error as e:
            error_label.configure(text=f"Erro de banco: {e}")
            print(f"Log: Erro de MySQL em _executar_login: {e}")

    def _atualizar_estado_login(self):
        # (Função idêntica, sem mudanças)
        if self.user_id and self.user_first_name:
            print(f"Log: Usuário {self.user_id} ({self.user_first_name}) está logado.")
            self.user_name_label.configure(text=f"Olá, {self.user_first_name}!")
            self.user_name_label.pack(side="left", padx=(0, 10), pady=10)
            self.btn_geli.configure(fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
            self.btn_receitas.configure(fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
            self.btn_estoque.configure(fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
            self.btn_compras.configure(fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
        else:
            print("Log: Nenhum usuário logado.")
            self.user_name_label.configure(text="")
            self.user_name_label.pack_forget()
            self.btn_geli.configure(fg_color=self.BUTTON_DISABLED_COLOR, hover_color=self.BUTTON_DISABLED_COLOR)
            self.btn_receitas.configure(fg_color=self.BUTTON_DISABLED_COLOR, hover_color=self.BUTTON_DISABLED_COLOR)
            self.btn_estoque.configure(fg_color=self.BUTTON_DISABLED_COLOR, hover_color=self.BUTTON_DISABLED_COLOR)
            self.btn_compras.configure(fg_color=self.BUTTON_DISABLED_COLOR, hover_color=self.BUTTON_DISABLED_COLOR)

    def _abrir_tela_cadastro(self):
        # (Função idêntica, sem mudanças)
        if hasattr(self, 'login_window') and self.login_window.winfo_exists():
            self.login_window.withdraw()
        if hasattr(self, 'register_window') and self.register_window.winfo_exists():
            self.register_window.focus()
            return
        self.register_window = ctk.CTkToplevel(self)
        self.register_window.title("Criar Conta")
        self.register_window.geometry("400x550")
        self.register_window.transient(self)
        self.register_window.grab_set()
        self.register_window.resizable(False, False)
        x_app = self.winfo_x()
        y_app = self.winfo_y()
        w_app = self.winfo_width()
        h_app = self.winfo_height()
        x_reg = x_app + (w_app // 2) - (400 // 2)
        y_reg = y_app + (h_app // 2) - (550 // 2)
        self.register_window.geometry(f"400x550+{x_reg}+{y_reg}")
        ctk.CTkLabel(self.register_window, text="Criar Conta", font=self.large_font).pack(pady=(20, 10))
        self.var_nome = ctk.StringVar()
        self.var_telefone = ctk.StringVar()
        self.var_email = ctk.StringVar()
        self.var_senha = ctk.StringVar()
        self.var_conf_senha = ctk.StringVar()
        self.var_termos = ctk.IntVar()
        ctk.CTkLabel(self.register_window, text="Nome Completo:", font=self.small_font, anchor="w").pack(fill="x", padx=50)
        nome_entry = ctk.CTkEntry(self.register_window, width=300, height=35, textvariable=self.var_nome)
        nome_entry.pack(pady=(0, 10))
        ctk.CTkLabel(self.register_window, text="Telefone (opcional):", font=self.small_font, anchor="w").pack(fill="x", padx=50)
        telefone_entry = ctk.CTkEntry(self.register_window, width=300, height=35, textvariable=self.var_telefone)
        telefone_entry.pack(pady=(0, 10))
        ctk.CTkLabel(self.register_window, text="E-mail:", font=self.small_font, anchor="w").pack(fill="x", padx=50)
        email_entry = ctk.CTkEntry(self.register_window, width=300, height=35, textvariable=self.var_email)
        email_entry.pack(pady=(0, 10))
        ctk.CTkLabel(self.register_window, text="Senha (mín. 6 caracteres):", font=self.small_font, anchor="w").pack(fill="x", padx=50)
        senha_entry = ctk.CTkEntry(self.register_window, width=300, height=35, show="*", textvariable=self.var_senha)
        senha_entry.pack(pady=(0, 10))
        ctk.CTkLabel(self.register_window, text="Confirmar Senha:", font=self.small_font, anchor="w").pack(fill="x", padx=50)
        conf_senha_entry = ctk.CTkEntry(self.register_window, width=300, height=35, show="*", textvariable=self.var_conf_senha)
        conf_senha_entry.pack(pady=(0, 10))
        termos_frame = ctk.CTkFrame(self.register_window, fg_color="transparent")
        termos_frame.pack(pady=10)
        termos_check = ctk.CTkCheckBox(termos_frame, text="Li e concordo com os ", variable=self.var_termos,
                                       font=self.small_light_font, command=self._validar_campos_cadastro)
        termos_check.pack(side="left")
        termos_link = ctk.CTkLabel(termos_frame, text="Termos de Uso", text_color="#0066CC",
                                     font=self.link_font, cursor="hand2")
        termos_link.pack(side="left")
        termos_link.bind("<Button-1>", lambda e: self._abrir_janela_termos())
        self.btn_cadastrar = ctk.CTkButton(self.register_window, text="Cadastrar", width=300, height=40,
                                           font=self.button_font, state="disabled",
                                           command=self._executar_cadastro)
        self.btn_cadastrar.pack(pady=10)
        self.register_error_label = ctk.CTkLabel(self.register_window, text="", text_color="red", font=self.small_font)
        self.register_error_label.pack()
        self.var_nome.trace_add("write", self._validar_campos_cadastro)
        self.var_email.trace_add("write", self._validar_campos_cadastro)
        self.var_senha.trace_add("write", self._validar_campos_cadastro)
        self.var_conf_senha.trace_add("write", self._validar_campos_cadastro)
        
        self.register_window.protocol("WM_DELETE_WINDOW", lambda: self._fechar_tela_cadastro(close_login=False))

    def _fechar_tela_cadastro(self, close_login=False):
        # (Função idêntica, sem mudanças)
        if hasattr(self, 'register_window') and self.register_window.winfo_exists():
            self.register_window.destroy()
        if close_login:
            if hasattr(self, 'login_window') and self.login_window.winfo_exists():
                self.login_window.destroy()
        else:
            if hasattr(self, 'login_window') and not self.login_window.winfo_exists():
                self.login_window.deiconify()
            elif hasattr(self, 'login_window'):
                self.login_window.focus()

    def _validar_campos_cadastro(self, *args):
        # (Função idêntica, sem mudanças)
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        nome_regex = r"^[a-zA-ZÀ-ÿ\s']+$"
        nome = self.var_nome.get()
        email = self.var_email.get()
        senha = self.var_senha.get()
        conf_senha = self.var_conf_senha.get()
        termos_aceitos = self.var_termos.get() == 1
        is_nome_valido = bool(re.match(nome_regex, nome) and len(nome) > 2)
        is_email_valido = bool(re.match(email_regex, email))
        is_senha_valida = bool(len(senha) >= 6)
        is_senha_confirmada = bool(senha == conf_senha and is_senha_valida)
        if is_nome_valido and is_email_valido and is_senha_valida and is_senha_confirmada and termos_aceitos:
            self.btn_cadastrar.configure(state="normal")
        else:
            self.btn_cadastrar.configure(state="disabled")

    def _executar_cadastro(self):
        # (Função idêntica, sem mudanças)
        nome = self.var_nome.get().strip()
        telefone = self.var_telefone.get().strip() or None
        email = self.var_email.get().strip()
        senha = self.var_senha.get()
        senha_hash = generate_password_hash(senha)
        if not self.db_connection or not self.db_connection.is_connected():
            self.register_error_label.configure(text="Erro de conexão com o banco.")
            self.db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)
            return
        try:
            cursor = self.db_connection.cursor()
            query = "INSERT INTO usuarios (nome, telefone, email, senha) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (nome, telefone, email, senha_hash))
            new_user_id = cursor.lastrowid
            self.db_connection.commit()
            cursor.close()
            
            self._registrar_log(new_user_id, 'Register', 'Success')
            
            self.user_id = new_user_id
            self.user_first_name = nome.split(' ')[0]
            self.session_manager.save_session(self.user_id, self.user_first_name)
            self._atualizar_estado_login()
            messagebox.showinfo("Sucesso!", f"Bem-vindo, {self.user_first_name}! Cadastro realizado com sucesso.")
            self._fechar_tela_cadastro(close_login=True)
        except IntegrityError as e:
            if e.errno == 1062:
                self.register_error_label.configure(text="Este e-mail já está cadastrado.")
            else:
                self.register_error_label.configure(text=f"Erro de banco: {e}")
            print(f"Log: Erro de MySQL em _executar_cadastro: {e}")
        except Error as e:
            self.register_error_label.configure(text=f"Erro de banco: {e}")
            print(f"Log: Erro de MySQL em _executar_cadastro: {e}")

    def _abrir_janela_termos(self):
        # (Função idêntica, sem mudanças)
        if hasattr(self, 'termos_window') and self.termos_window.winfo_exists():
            self.termos_window.focus()
            return
        self.termos_window = ctk.CTkToplevel(self)
        self.termos_window.title("Termos de Uso e Política de Privacidade")
        self.termos_window.geometry("700x500")
        
        # Pega a posição da janela de registro para centralizar em relação a ELA
        # (Verifica se a register_window existe antes de tentar ler sua posição)
        if hasattr(self, 'register_window') and self.register_window.winfo_exists():
             self.termos_window.transient(self.register_window)
             x_reg = self.register_window.winfo_x()
             y_reg = self.register_window.winfo_y()
             w_reg = self.register_window.winfo_width()
             h_reg = self.register_window.winfo_height()
             x_termos = x_reg + (w_reg // 2) - (700 // 2)
             y_termos = y_reg + (h_reg // 2) - (500 // 2)
             self.termos_window.geometry(f"700x500+{x_termos}+{y_termos}")
        else:
            # Fallback se a janela de registro não existir (centraliza na tela)
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            center_x = int(screen_width / 2 - 700 / 2)
            center_y = int(screen_height / 2 - 500 / 2)
            self.termos_window.geometry(f"700x500+{center_x}+{center_y}")

        self.termos_window.grab_set()
        self.termos_window.resizable(True, True)
        
        textbox = ctk.CTkTextbox(self.termos_window, wrap="word", font=self.small_light_font, spacing2=5)
        textbox.pack(fill="both", expand=True, padx=20, pady=(20, 10))
        textbox.tag_config("h1", font=ctk.CTkFont("Poppins Bold", 18), spacing1=(15, 5))
        textbox.tag_config("b", font=ctk.CTkFont("Poppins SemiBold", 12))
        textbox.tag_config("i", font=ctk.CTkFont("Poppins Light Italic", 12))
        textbox.tag_config("li", spacing1=(0, 2))
        
        termos_html = """
<h1>Termos e Condições de Uso da Plataforma MyGeli</h1>
<b>Data de Efetivação:</b> 09 de setembro de 2025
<br><br>
<b>Por favor, leia estes termos de uso com atenção antes de utilizar a nossa plataforma.</b>
<br><br>
<p>Bem vindo(a) à MyGeli! Estes Termos e Condições de Uso ("termos") regem o seu acesso e uso da aplicação web MyGeli ("Plataforma"), incluindo todo o conteúdo, funcionalidades e serviços oferecidos.</p>
<br>
<p>
  <b>1. ACEITAÇÃO DOS TERMOS</b>
  <br><br>
  Ao se cadastrar, acessar ou utilizar a Plataforma MyGeli de qualquer forma, você, doravante denominado <b>"Usuário"</b>, expressa sua concordância plena e sem ressalvas com todos os termos e condições aqui estabelecidos. Caso não concorde com qualquer um dos termos, você não deve utilizar a plataforma.
</p>
<p>
  <b>2. DESCRIÇÃO DO SERVIÇO</b>
  <br><br>
  A MyGeli é uma plataforma de assistência culinária que permite ao Usuário gerenciar um inventário de alimentos ("Estoque"), obter sugestões de receitas através de uma interface de Inteligência Artificial ("Geli") e arquivar suas receitas. A plataforma visa otimizar o uso de ingredientes e auxiliar no planejamento de refeições.
</p>
<p>
  <b>3. CADASTRO E CONTA DO USUÁRIO</b>
  <br><br>
  <b>3.1. Elegibilidade</b>
  <br><br>
  Para utilizar a Plataforma, o Usuário declara ser maior de 18 (dezoito) anos e possuir plena capacidade legal. A MyGeli não coleta intencionalmente dados de menores de 18 anos, a MyGeli se reserva o direito de encerrar a conta imediatamente e excluir todos os dados pessoais e de uso associado a ela, sem aviso prévio.
  <br><br>
  <b>3.2. Veracidade das informações</b>
  <br><br>
  O Usuário se compromete a fornecer informações verdadeiras, exatas e atualizadas durante o cadastro, responsabilizando-se por elas.
  <br><br>
  <b>3.3. Segurança da Conta</b>
  <br><br>
  O Usuário é o único responsável por manter a confidencialidade de sua senha e por todas as atividades que ocorrerem em sua conta. A MyGeli não será responsável por perdas ou danos decorrentes do uso não autorizado de sua conta.
</p>
<p>
  <b>4. POLÍTICA DE PRIVACIDADE E PROTEÇÃO DE DADOS</b>
  <br><br>
  A MyGeli respeita sua privacidade e está em conformidade com a Lei Geral de Proteção de Dados Pessoais (Lei n° 13.709/2018). <br>
  Para mais detalhes sobre como coletamos, usamos, armazenamos e protegemos seus dados pessoais, por favor leia nossa Política de Privacidade, que é parte integrante destes Termos.
</p>
<p>
  <b>5. RESPONSABILIDADES, DIREITOS E RESTRIÇÕES</b>
  <br><br>
  <b>5.1. Conteúdo Gerado pela IA (Geli)</b>
  <br><br>
  As receitas, dicas e informações culinárias fornecidas pela Geli são geradas por inteligência artificial e oferecidas exclusivamente como sugestões. Elas não são, e não devem ser interpretadas como orientação profissional de qualquer tipo. <br>
  A <i>MyGeli NÃO SE RESPONSABILIZA, em hipótese alguma</i>, por quaisquer danos, perdas ou prejuízos decorrentes do uso, preparo ou consumo das receitas sugeridas. <i>É de total e inteira responsabilidade do Usuário verificar e assegurar a adequação de todos os ingredientes</i> em relação a alergias, intolerância, restrições alimentares ou condições de saúde. Da mesma forma, cabe ao Usuário garantir a segurança e a higiene no preparo dos alimentos. <br>
  As informações nutricionais, quando fornecidas, são estimativas e <i>não substituem</i> a orientação de um profissional de saúde, como médico ou nutricionista. <i>Ao utilizar a Geli, você assume todos os riscos associados ao uso e preparo de qualquer receita sugerida.</i>
  <br><br>
  <b>5.2. Uso do Estoque</b>
  <br><br>
  O Usuário é o único responsável por manter seu Estoque atualizado e por verificar a validade e condição dos alimentos reais em sua despensa. A plataforma é uma ferramenta de organização e não possui responsabilidade sobre o consumo de alimentos impróprios.
  <br><br>
  <b>5.3. Conduta do Usuário</b>
  <br><br>
  É vedado ao Usuário utilizar a Plataforma para:
  <ul>
  <li>Transmitir conteúdo ilegal, ofensivo, ameaçador ou que viole a privacidade de terceiros.</li>
  <li>Tentar obter acesso não autorizado à Plataforma ou a sistemas de terceiros.</li>
  <li>Interferir no funcionamento normal da Plataforma através de vírus, sobrecarga ou técnicas maliciosas.</li>
  </ul>
</p>
<p>
  <b>6. PROPRIEDADE INTELECTUAL E MARCAS</b>
  <br><br>
  <b>6.1. Plataforma MyGeli</b>
  <br><br>
  Todos os direitos de propriedade intelectual sobre o software, o design, os logotipos e a marca "MyGeli" pertencem aos seus criadores. Estes Termos concedem ao Usuário uma licença limitada, não exclusiva e revogável para usar a Plataforma para fins pessoais e não comerciais.
  <br><br>
  <b>6.2. Marcas de Terceiros</b>
  <br><br>
  A menção a nomes de marcas de produtos alimentícios no Estoque ou em receitas é puramente descritiva. A MyGeli não possui afiliação, patrocínio ou endosso por parte dos detentores dessas marcas.
</p>
<p>
  <b>7. LIMITAÇÃO DE RESPONSABILIDADE</b>
  <br><br>
  A Plataforma MyGeli é fornecida "no estado em que se encontra" ("as is"), sem garantias de qualquer tipo. Em nenhuma hipótese os criadores da MyGeli serão responsáveis por quaisquer danos diretos ou indiretos (incluindo, mas não se limitando a, danos à saúde, perdas financeiras ou desperdício de alimentos) decorrentes do uso da incapacidade de usar a Plataforma.
</p>
<p>
  <b>8. MODIFICAÇÃO DOS TERMOS</b>
  <br><br>
  Reservamo-nos o direito de modificar estes Termos a qualquer momento. Notificaremos o Usuário sobre alterações significativas. A continuidade do uso da Plataforma após tais modificações constituirá sua concordância com os novos Termos.
</p>
<p>
  <b>9. LEGISLAÇÃO APLICÁVEL E FORO</b>
  <br><br>
  Estes Termos serão regidos e interpretados de acordo com as leis da República Federativa do Brasil. Fica eleito o foro do domicílio do Usuário para dirimir quaisquer controvérsias oriundas deste documento.
</p>
<p>
  <b>10. CONTATO</b>
  <br><br>
  Em caso de dúvidas sobre estes Termos de Uso, entre em contato conosco pelo e-mail: foodyzeof@gmail.com.
</p>
<h1>Política de Privacidade</h1>
<br><br>
<b>Data de Efetivação:</b> 09 de Setembro de 2025
<br><br>
<b>Informações do Controlador de Dados</b>
<br><br>
<p>
  A MyGeli é uma plataforma de tecnologia desenvolvida e operada por uma equipe de pessoas físicas. Como não conseguimos uma pessoa jurídica (CNPJ) ou endereço físico, a responsabilidade pelo tratamento dos dados pessoais coletados é de nossa equipe de desenvolvimento, representada pelo e-mail foodyzeof@gmail.com. Qualquer comunicação sobre seus dados, ou sobre esta política de privacidade, deve ser direcionada a este endereço de e-mail, que é o nosso principal canal de contato.
</p>
<p>
  <b>1. DADOS PESSOAIS COLETADOS</b>
  <br><br>
  Para a criação e manutenção de sua conta, coletamos os seguintes dados pessoais:
  <br>
  <ul>
  <li>Nome de usuário;</li>
  <li>Endereço de e-mail;</li>
  <li>Senha (de forma criptografada).</li>
  </ul>
</p>
<p>
  <b>2. FINALIDADE DA COLETA</b>
  <br><br>
  Os dados pessoais são coletados com a finalidade exclusiva de:
  <br>
  <ul>
  <li>Identificar o Usuário e gerenciar sua conta;</li>
  <li>Permitir o acesso à Plataforma;</li>
  <li>Enviar comunicações essenciais sobre o serviço (ex: redefinição de senha).</li>
  </ul>
</p>
<p>
  <b>3. DADOS DE USO E CONTEÚDO</b>
  <br><br>
  A Plataforma também processará dados inseridos por você, como:
  <br>
  <ul>
  <li>Itens, quantidades e categorias do seu Estoque;</li>
  <li>Receitas salvas;</li>
  <li>Histórico de conversas com a Geli.</li>
  </ul>
  <br>
  Estes dados são essenciais para a prestação do serviço principal da Plataforma e não serão compartilhados ou vendidos.
</p>
<p>
  <b>4. BASES LEGAIS PARA O TRATAMENTO DE DADOS</b>
  <br><br>
  A Lei Geral de Proteção de Dados Pessoais (LGPD) exige que o tratamento dos seus dados pessoais tenha uma "base legal", ou seja, uma justificativa válida para que os dados possam ser processados. Na MyGeli, utilizamos as seguintes bases legais:
  <br>
  <ul>
  <li><b>Execução de Contrato: </b>Seus dados de cadastro (e-mail, nome de usuário) são processados para que possamos cumprir com os Termos de Uso, permitindo o acesso e a utilização da plataforma.</li>
  <li><b>Consentimento: </b>Ao utilizar as funcionalidades do chat com a Geli, você nos dá seu consentimento para que o conteúdo de suas mensagens e a lista de itens do seu Estoque sejam enviados para a tecnologia de inteligência artificial do Google, com a finalidade exclusiva de gerar uma resposta para você.</li>
  <li><b>Cumprimento de Obrigação Legal: </b>De acordo com o Marco Civil da Internet (Lei n 12.965/2014), somos obrigados a manter os registros de acesso à nossa plataforma por 6 (seis) meses para cumprir com a legislação brasileira.</li>
  </ul>
</p>
<p>
  <b>5. COMPARTILHAMENTO COM TERCEIROS (INTELIGÊNCIA ARTIFICIAL)</b>
  <br><br>
  Para fornecer as sugestões de receitas, o conteúdo de suas mensagens no chat e a lista de itens do seu Estoque são enviados para processamento pela API do Google Gemini, que é a tecnologia por trás da Geli. A MyGeli não envia dados pessoais como e-mail ou o nome do usuário para o Google. Ao utilizar o chat, você concorda com este compartilhamento de dados não-pessoais com a finalidade exclusiva de gerar a resposta da IA.
</p>
<p>
  <b>6. TRANSFERÊNCIA INTERNACIONAL DE DADOS</b>
  <br><br>
  Para a prestação do serviço de inteligência artificial, seus dados de uso (histórico de conversas com a Geli e a lista de itens do Estoque) podem ser transferidos para e processados em servidores localizados fora do Brasil, em países como os Estados Unidos, onde o Google opera. <br>
  Essa transferência de dados é realizada em total conformidade com a LGPD. Adotamos medidas de segurança e garantias contratuais, como as Cláusulas Contratuais Padrão (Standard Contractual Clauses), para assegurar que seus dados recebam um nível de proteção de dados adequado e compatível com a legislação brasileira, garantindo que os terceiros envolvidos cumpram com as mesmas obrigações de segurança e privacidade.
</p>
<p>
  <b>7. DIREITOS DO TITULAR</b>
  <br><br>
  Em conformidade com a LGPD, o Usuário (titular dos dados) tem o direito de solicitar, a qualquer momento, o acesso, a correção, a anonimização ou a eliminação de seus dados pessoais. Para exercer seus direitos, entre em contato conosco através do e-mail: foodyzeof@gmail.com.
</p>
<p>
  <b>8.SEGURANÇA E ARMAZENAMENTO</b>
  <br><br>
  Adotamos medidas de segurança técnicas e administrativas para proteger seus dados. Os registros de acesso à aplicação serão mantidos sob sigilo, em ambiente controlado e de segurança, pelo prazo de 6 (seis) meses, conforme determina o Marco Civil da Internet (Lei n° 12.965/2014).
</p>
<p>
  <b>9. ATUALIZAÇÕES DA POLÍTICA DE PRIVACIDADE</b>
  <br><br>
  A MyGeli se reserva o direito de modificar esta Política de Privacidade a qualquer momento, para adaptá-la a novas leis, tecnologias ou mudanças em nossos serviços. Quando fizermos alterações significativas, nós o notificaremos por e-mail ou por meio de um aviso claro na própria plataforma, para que você possa revisar as mudanças e decidir se continua a utilizar nossos serviços. A continuidade do uso da plataforma após a comunicação das alterações significará sua total concordância com os novos termos.
</p>
"""
        textbox.configure(state="normal")
        lines = termos_html.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                textbox.insert("end", "\n")
                continue
            line = line.replace("<p>", "").replace("</p>", "").replace("<br>", "\n")
            line = line.replace("<ul>", "").replace("</ul>", "")
            if line.startswith("<h1>"):
                line = line.replace("<h1>", "").replace("</h1>", "")
                textbox.insert("end", line + "\n", "h1")
            elif line.startswith("<li>"):
                line = line.replace("<li>", "  • ").replace("</li>", "")
                textbox.insert("end", line + "\n", "li")
            else:
                parts = re.split(r'(<b>.*?</b>|<i>.*?</i>)', line)
                for part in parts:
                    if part.startswith("<b>"):
                        textbox.insert("end", part.replace("<b>", "").replace("</b>", ""), "b")
                    elif part.startswith("<i>"):
                        textbox.insert("end", part.replace("<i>", "").replace("</i>", ""), "i")
                    else:
                        textbox.insert("end", part)
                textbox.insert("end", "\n")
        textbox.configure(state="disabled")
        ctk.CTkButton(self.termos_window, text="Fechar", width=100,
                      command=self.termos_window.destroy).pack(pady=10)

# --- Execução da Aplicação ---
if __name__ == "__main__":
    # Credenciais e conexão
    db_host = "localhost"
    db_name = "mygeli"
    db_usuario = "foodyzeadm"
    db_senha = "supfood0017admx"
    
    conexao_ativa = conectar_mysql(db_host, db_name, db_usuario, db_senha)

    app = App(db_connection=conexao_ativa)
    app.mainloop()

    # Fecha a conexão ao sair da aplicação
    if conexao_ativa and conexao_ativa.is_connected():
        conexao_ativa.close()
        print("Log: Conexão com o BD fechada ao finalizar o app.")