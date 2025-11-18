import customtkinter as ctk
import subprocess
import sys
import mysql.connector
from mysql.connector import Error, IntegrityError
from pathlib import Path
from PIL import Image, ImageSequence
from werkzeug.security import check_password_hash, generate_password_hash
from tkinter import messagebox
import re
import socket
import hashlib
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from session_manager import SessionManager

load_dotenv()

# --- Conexão com Banco de Dados ---
def conectar_mysql(host, database, user, password):
    try:
        conexao = mysql.connector.connect(host=host, database=database, user=user, password=password)
        if conexao.is_connected():
            print("Log: Conexão ao MySQL bem-sucedida!")
            return conexao
    except Error as e:
        print(f"Log: Erro ao conectar ao MySQL: {e}")
        return None

# --- NOVA FUNÇÃO GLOBAL (NECESSÁRIA PARA O LOG) ---
def _get_hashed_ip():
    """Obtém o IP local e o criptografa (hash SHA-256)."""
    try:
        ip_address = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip_address = '127.0.0.1'
    return hashlib.sha256(ip_address.encode('utf-8')).hexdigest()

# --- Navegação entre Telas ---
def abrir_gui(nome_arquivo):
    if app:
        app.destroy()
    try:
        caminho_script = str(Path(__file__).parent / nome_arquivo)
        subprocess.Popen([sys.executable, caminho_script])
    except Exception as e:
        print(f"Erro ao tentar abrir {nome_arquivo}: {e}")

# --- Classe Principal da Aplicação ---
class App(ctk.CTk):
    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 650
    BG_COLOR = "#F5F5F5"
    HEADER_COLOR = "#0084FF"
    BUTTON_COLOR = "#0084FF"
    BUTTON_HOVER_COLOR = "#0066CC"
    BUTTON_TEXT_COLOR = "white"
    CARD_COLOR = "#FFFFFF"
    CARD_BORDER_COLOR = "#E0E0E0"
    BUTTON_DISABLED_COLOR = "#B0B0B0"
    BUTTON_DANGER_COLOR = "#D32F2F"
    BUTTON_DANGER_HOVER_COLOR = "#B71C1C"

    def __init__(self, db_connection):
        super().__init__()
       
        self.db_connection = db_connection
        self.session_manager = SessionManager()
       
        self.user_id = None
        self.user_first_name = None

        # Tenta fazer login automático via Token
        if self._tentar_login_automatico():
             print("Log: Sessão restaurada via Token Persistente.")
        else:
             print("Log: Nenhuma sessão válida encontrada.")

        self._configurar_janela()
        self._criar_fontes()
        self._criar_widgets()
        self._atualizar_estado_login()

    def _configurar_janela(self):
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
        self.large_font = ctk.CTkFont("Poppins Bold", 28)
        self.medium_font = ctk.CTkFont("Poppins Medium", 18)
        self.small_font = ctk.CTkFont("Poppins Light", 14)
        self.button_font = ctk.CTkFont("Poppins SemiBold", 18)
        self.link_font = ctk.CTkFont("Poppins Light", 12, underline=True)
        self.small_light_font = ctk.CTkFont("Poppins Light", 12)
        self.header_name_font = ctk.CTkFont("Poppins SemiBold", 16)

    def _criar_widgets(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        header_frame = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color=self.HEADER_COLOR)
        header_frame.grid(row=0, column=0, sticky="new")
        header_frame.grid_propagate(False)
        assets_path = Path(__file__).parent / "assets" / "frame1"
        try:
            user_icon_image = ctk.CTkImage(Image.open(assets_path / "user_icon.png").resize((32, 32), Image.LANCZOS), size=(40, 40))
            options_image = ctk.CTkImage(Image.open(assets_path / "options.png").resize((32, 32), Image.LANCZOS), size=(30, 30))
            calendario_image = ctk.CTkImage(Image.open(assets_path / "calendario.png").resize((32, 32), Image.LANCZOS), size=(30, 30))
            original_logo_image = Image.open(assets_path / "MyGeli.png")
            original_width, original_height = original_logo_image.size
            target_width = 280
            aspect_ratio = original_height / original_width
            target_height = int(target_width * aspect_ratio)
            resized_logo = original_logo_image.resize((target_width, target_height), Image.LANCZOS)
            logo_image = ctk.CTkImage(light_image=resized_logo, size=(target_width, target_height))
        except Exception as e:
            print(f"Erro ao carregar imagens: {e}")
            user_icon_image = None
            options_image = None
            calendario_image = None
            logo_image = None

        user_button = ctk.CTkButton(header_frame, text="", image=user_icon_image, width=45, height=45, fg_color="transparent", hover_color=self.BUTTON_HOVER_COLOR, command=self._acao_usuario)
        user_button.pack(side="left", padx=10, pady=10)
        self.user_name_label = ctk.CTkLabel(header_frame, text="", font=self.header_name_font, text_color=self.BUTTON_TEXT_COLOR)
        options_button = ctk.CTkButton(header_frame, text="", image=options_image, width=40, height=40, fg_color="transparent", hover_color=self.BUTTON_HOVER_COLOR, command=self._abrir_preferencias_com_origem)
        options_button.pack(side="right", padx=5, pady=5)
        calendario_button = ctk.CTkButton(header_frame, text="", image=calendario_image, width=40, height=40, fg_color="transparent", hover_color=self.BUTTON_HOVER_COLOR, command=lambda: self._abrir_gui_com_verificacao("gui5_planejamento.py"))
        calendario_button.pack(side="right", padx=5, pady=5)
       
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew")
        content_block_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_block_frame.pack(side="top", fill="x", pady=(50, 0))
       
        if logo_image:
             ctk.CTkLabel(content_block_frame, image=logo_image, text="").pack(pady=(0, 30))
        else:
             ctk.CTkLabel(content_block_frame, text="MyGeli", font=self.large_font).pack(pady=(0, 30))

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

    # --- MÉTODO DE LOG ADICIONADO (CORREÇÃO) ---
    def _registrar_log(self, user_id, action, status):
        """Registra uma ação na tabela 'log'."""
        if not self.db_connection or not self.db_connection.is_connected():
            return

        cursor = None
        try:
            hashed_ip = _get_hashed_ip()
            cursor = self.db_connection.cursor()
            query = "INSERT INTO log (id_user, action, status, ip_address) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (user_id, action, status, hashed_ip))
            self.db_connection.commit()
            print(f"Log: Ação '{action}' registrada para user_id {user_id}.")
        except Error as e:
            print(f"Log: ERRO ao registrar log: {e}")
            # Não faz rollback aqui para não atrapalhar a transação principal se houver
        finally:
            if cursor: cursor.close()

    def _abrir_preferencias_com_origem(self):
        if self.user_id:
            try:
                self.destroy()
                caminho_script = str(Path(__file__).parent / "gui_preferencias.py")
                # Envia "gui1.py" como argumento
                subprocess.Popen([sys.executable, caminho_script, "gui1.py"])
            except Exception as e:
                print(f"Erro ao tentar abrir gui_preferencias.py: {e}")
        else:
            messagebox.showwarning("Acesso Restrito", "Entre em uma conta para utilizar a ferramenta!")


    # --- MÉTODOS DE PERSISTÊNCIA ---
    def _create_remember_token(self):
        selector = os.urandom(16).hex()
        authenticator = os.urandom(32).hex()
        hashed_authenticator = hashlib.sha256(authenticator.encode()).hexdigest()
        return selector, authenticator, hashed_authenticator

    def _save_remember_token_db(self, user_id, selector, hashed_authenticator):
        expires_dt = datetime.now() + timedelta(days=30)
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM login_tokens WHERE user_id = %s", (user_id,))
            query = "INSERT INTO login_tokens (user_id, selector, hashed_token, expires) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (user_id, selector, hashed_authenticator, expires_dt))
            self.db_connection.commit()
            cursor.close()
            return True
        except Error as e:
            print(f"Log: Erro ao salvar token no BD: {e}")
            return False

    def _tentar_login_automatico(self):
        token_data = self.session_manager.get_token()
        if not token_data: return False

        selector = token_data.get("selector")
        authenticator = token_data.get("authenticator")
        if not selector or not authenticator: return False

        try:
            if not self.db_connection or not self.db_connection.is_connected():
                 self.db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)

            cursor = self.db_connection.cursor(dictionary=True)
            query = """
                SELECT t.token_id, t.user_id, t.hashed_token, t.expires, u.nome
                FROM login_tokens t
                JOIN usuarios u ON t.user_id = u.id
                WHERE t.selector = %s
            """
            cursor.execute(query, (selector,))
            record = cursor.fetchone()
            cursor.close()

            if not record:
                self.session_manager.clear_session()
                return False

            if record['expires'] < datetime.now():
                self.session_manager.clear_session()
                return False

            hashed_auth_check = hashlib.sha256(authenticator.encode()).hexdigest()
            if hashed_auth_check == record['hashed_token']:
                self.user_id = record['user_id']
                self.user_first_name = record['nome'].split(' ')[0]
                return True
            else:
                self.session_manager.clear_session()
                return False

        except Error as e:
            print(f"Log: Erro no login automático: {e}")
            return False

    def _abrir_gui_com_verificacao(self, nome_arquivo):
        if self.user_id:
            abrir_gui(nome_arquivo)
        else:
            messagebox.showwarning("Acesso Restrito", "Entre em uma conta para utilizar a ferramenta!")
   
    def _acao_usuario(self):
        if self.user_id:
            if hasattr(self, 'opcoes_window') and self.opcoes_window.winfo_exists():
                self.opcoes_window.focus()
                return

            self.opcoes_window = ctk.CTkToplevel(self)
            self.opcoes_window.title("Opções da Conta")
            self.opcoes_window.geometry("300x150")
            self.opcoes_window.transient(self)
            self.opcoes_window.grab_set()
            self.opcoes_window.resizable(False, False)
           
            self._centralizar_janela(self.opcoes_window, 300, 150)
            ctk.CTkLabel(self.opcoes_window, text=f"Opções para {self.user_first_name}", font=self.medium_font).pack(pady=(20, 15))
            btn_sair = ctk.CTkButton(self.opcoes_window, text="Sair da Conta",
                                     command=self._confirmar_logout,
                                     font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
            btn_sair.pack(pady=10, padx=20, fill="x")
           
        else:
            self._abrir_tela_login()

    def _centralizar_janela(self, janela, largura, altura):
        x_app = self.winfo_x()
        y_app = self.winfo_y()
        w_app = self.winfo_width()
        h_app = self.winfo_height()
        x_pos = x_app + (w_app // 2) - (largura // 2)
        y_pos = y_app + (h_app // 2) - (altura // 2)
        janela.geometry(f"{largura}x{altura}+{x_pos}+{y_pos}")

    def _confirmar_logout(self):
        self.opcoes_window.grab_release()
        resposta = messagebox.askyesno("Sair", "Tem certeza que deseja sair da sua conta?", parent=self.opcoes_window)
        if resposta:
            self._executar_logout()
        else:
            self.opcoes_window.grab_set()
            self.opcoes_window.focus()

    def _executar_logout(self):
        if self.user_id:
             self._registrar_log(self.user_id, 'Logout', 'Success')
             
             try:
                 cursor = self.db_connection.cursor()
                 cursor.execute("DELETE FROM login_tokens WHERE user_id = %s", (self.user_id,))
                 self.db_connection.commit()
                 cursor.close()
             except Error as e:
                 print(f"Log: Erro ao limpar token do BD: {e}")

        if hasattr(self, 'opcoes_window') and self.opcoes_window.winfo_exists():
            self.opcoes_window.destroy()
           
        self.session_manager.clear_session()
        self.user_id = None
        self.user_first_name = None
        self._atualizar_estado_login()

    def _confirmar_exclusao(self):
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
        if not self.user_id:
            messagebox.showerror("Erro de Sessão", "Sessão não encontrada.", parent=self); return

        if not self.db_connection or not self.db_connection.is_connected():
            messagebox.showerror("Erro de Conexão", "Erro de conexão com o banco.", parent=self)
            self.db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)
            if not self.db_connection: return

        cursor = None
        try:
            cursor = self.db_connection.cursor()
            # FKs com CASCADE cuidarão do resto, mas para segurança:
            cursor.execute("DELETE FROM produtos WHERE user_id = %s", (self.user_id,))
            cursor.execute("DELETE FROM receitas WHERE idusuario = %s", (self.user_id,))
            cursor.execute("DELETE FROM login_tokens WHERE user_id = %s", (self.user_id,))
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (self.user_id,))
            self.db_connection.commit()
           
            messagebox.showinfo("Conta Excluída", "Sua conta foi excluída permanentemente.")
            # Logout após exclusão
            self._executar_logout()

        except Error as e:
            self.db_connection.rollback()
            messagebox.showerror("Erro no Banco de Dados", f"Falha ao excluir conta:\n{e}", parent=self)
        finally:
            if cursor: cursor.close()
   
    def _abrir_tela_login(self):
        if hasattr(self, 'login_window') and self.login_window.winfo_exists():
            self.login_window.focus(); return
           
        self.login_window = ctk.CTkToplevel(self)
        self.login_window.title("Login MyGeli")
        self.login_window.transient(self)
        self.login_window.grab_set()
        self.login_window.resizable(False, False)
        self._centralizar_janela(self.login_window, 350, 350)
       
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
                      command=lambda: self._executar_login(email_entry, senha_entry, error_label)).pack(pady=(10, 5))
                     
        link_cadastro = ctk.CTkLabel(self.login_window, text="Não tem uma conta? Crie uma.", text_color="#0066CC",
                                     font=self.link_font, cursor="hand2")
        link_cadastro.pack(pady=(5, 10))
        link_cadastro.bind("<Button-1>", lambda e: self._abrir_tela_cadastro())

    def _executar_login(self, email_entry, senha_entry, error_label):
        email = email_entry.get().strip()
        senha = senha_entry.get()
        if not email or not senha:
            error_label.configure(text="Preencha todos os campos."); return
       
        if not self.db_connection or not self.db_connection.is_connected():
            error_label.configure(text="Erro de conexão."); self.db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha); return
           
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("SELECT id, nome, email, senha FROM usuarios WHERE email = %s", (email,))
            user = cursor.fetchone()
            cursor.close()
           
            if not user:
                error_label.configure(text="E-mail incorreto!")
                return
            if not check_password_hash(user['senha'], senha):
                error_label.configure(text="Senha incorreta!")
                self._registrar_log(user['id'], 'Login', 'Failure') # Log de falha
                return
           
            self.user_id = user['id']
            self.user_first_name = user['nome'].split(' ')[0]

            # Cria e Salva Tokens
            selector, authenticator, hashed_authenticator = self._create_remember_token()
            if self._save_remember_token_db(self.user_id, selector, hashed_authenticator):
                self.session_manager.save_token(selector, authenticator)
           
            self._registrar_log(self.user_id, 'Login', 'Success') # Log de sucesso

            self._atualizar_estado_login()
            self.login_window.destroy()
        except Error as e:
            error_label.configure(text=f"Erro: {e}")

    def _atualizar_estado_login(self):
        if self.user_id and self.user_first_name:
            print(f"Log: Usuário {self.user_id} ({self.user_first_name}) está logado.")
            self.user_name_label.configure(text=f"Olá, {self.user_first_name}!")
            self.user_name_label.pack(side="left", padx=(0, 10), pady=10)
            for btn in [self.btn_geli, self.btn_receitas, self.btn_estoque, self.btn_compras]:
                btn.configure(fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
        else:
            print("Log: Nenhum usuário logado.")
            self.user_name_label.configure(text="")
            self.user_name_label.pack_forget()
            for btn in [self.btn_geli, self.btn_receitas, self.btn_estoque, self.btn_compras]:
                btn.configure(fg_color=self.BUTTON_DISABLED_COLOR, hover_color=self.BUTTON_DISABLED_COLOR)

    def _abrir_tela_cadastro(self):
        if hasattr(self, 'login_window') and self.login_window.winfo_exists(): self.login_window.withdraw()
        if hasattr(self, 'register_window') and self.register_window.winfo_exists(): self.register_window.focus(); return
       
        self.register_window = ctk.CTkToplevel(self)
        self.register_window.title("Criar Conta")
        self.register_window.transient(self)
        self.register_window.grab_set()
        self.register_window.resizable(False, False)
        self._centralizar_janela(self.register_window, 400, 550)

        ctk.CTkLabel(self.register_window, text="Criar Conta", font=self.large_font).pack(pady=(20, 10))
        self.var_nome = ctk.StringVar(); self.var_telefone = ctk.StringVar(); self.var_email = ctk.StringVar(); self.var_senha = ctk.StringVar(); self.var_conf_senha = ctk.StringVar(); self.var_termos = ctk.IntVar()
       
        # Widgets de cadastro resumidos para economizar espaço visual (lógica mantida)
        for txt, var, sh in [("Nome Completo:", self.var_nome, None), ("Telefone (opcional):", self.var_telefone, None), ("E-mail:", self.var_email, None), ("Senha (mín. 6):", self.var_senha, "*"), ("Confirmar Senha:", self.var_conf_senha, "*")]:
            ctk.CTkLabel(self.register_window, text=txt, font=self.small_font, anchor="w").pack(fill="x", padx=50)
            ctk.CTkEntry(self.register_window, width=300, height=35, textvariable=var, show=sh).pack(pady=(0, 10))

        termos_frame = ctk.CTkFrame(self.register_window, fg_color="transparent"); termos_frame.pack(pady=10)
        ctk.CTkCheckBox(termos_frame, text="Li e concordo com os ", variable=self.var_termos, font=self.small_light_font, command=self._validar_campos_cadastro).pack(side="left")
        lbl_termos = ctk.CTkLabel(termos_frame, text="Termos de Uso", text_color="#0066CC", font=self.link_font, cursor="hand2")
        lbl_termos.pack(side="left"); lbl_termos.bind("<Button-1>", lambda e: self._abrir_janela_termos())
       
        self.btn_cadastrar = ctk.CTkButton(self.register_window, text="Cadastrar", width=300, height=40, font=self.button_font, state="disabled", command=self._executar_cadastro)
        self.btn_cadastrar.pack(pady=10)
        self.register_error_label = ctk.CTkLabel(self.register_window, text="", text_color="red", font=self.small_font); self.register_error_label.pack()
       
        for v in [self.var_nome, self.var_email, self.var_senha, self.var_conf_senha]: v.trace_add("write", self._validar_campos_cadastro)
        self.register_window.protocol("WM_DELETE_WINDOW", lambda: self._fechar_tela_cadastro(close_login=False))

    def _fechar_tela_cadastro(self, close_login=False):
        if hasattr(self, 'register_window') and self.register_window.winfo_exists(): self.register_window.destroy()
        if close_login:
            if hasattr(self, 'login_window') and self.login_window.winfo_exists(): self.login_window.destroy()
        else:
            if hasattr(self, 'login_window') and self.login_window.winfo_exists(): self.login_window.deiconify()

    def _validar_campos_cadastro(self, *args):
        nome = self.var_nome.get(); email = self.var_email.get(); senha = self.var_senha.get(); conf = self.var_conf_senha.get()
        valido = (len(nome)>2 and re.match(r"^[a-zA-ZÀ-ÿ\s']+$", nome) and re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email) and len(senha)>=6 and senha==conf and self.var_termos.get()==1)
        self.btn_cadastrar.configure(state="normal" if valido else "disabled")

    # --- CADASTRO CORRIGIDO (TOKEN + LOG) ---
    def _executar_cadastro(self):
        nome = self.var_nome.get().strip(); telefone = self.var_telefone.get().strip() or None; email = self.var_email.get().strip(); senha = self.var_senha.get()
        senha_hash = generate_password_hash(senha)
       
        if not self.db_connection or not self.db_connection.is_connected():
            self.db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)
       
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("INSERT INTO usuarios (nome, telefone, email, senha) VALUES (%s, %s, %s, %s)", (nome, telefone, email, senha_hash))
            new_user_id = cursor.lastrowid
            self.db_connection.commit()
            cursor.close()
           
            self.user_id = new_user_id
            self.user_first_name = nome.split(' ')[0]
           
            # Gera token automático no cadastro também
            selector, authenticator, hashed_authenticator = self._create_remember_token()
            if self._save_remember_token_db(self.user_id, selector, hashed_authenticator):
                self.session_manager.save_token(selector, authenticator)

            # Log de Registro
            self._registrar_log(self.user_id, 'Register', 'Success')

            self._atualizar_estado_login()
            messagebox.showinfo("Sucesso!", f"Bem-vindo, {self.user_first_name}! Cadastro realizado.")
            self._fechar_tela_cadastro(close_login=True)
           
        except IntegrityError as e:
            self.register_error_label.configure(text="E-mail já cadastrado." if e.errno == 1062 else f"Erro: {e}")
        except Error as e:
            self.register_error_label.configure(text=f"Erro BD: {e}")

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

if __name__ == "__main__":
    # Recupera as credenciais das variáveis de ambiente carregadas pelo load_dotenv()
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')
    db_usuario = os.getenv('DB_USER')
    db_senha = os.getenv('DB_PASS')

    # Conecta usando as variáveis
    conexao_ativa = conectar_mysql(db_host, db_name, db_usuario, db_senha)

    app = App(db_connection=conexao_ativa)
    app.mainloop()

    # Fecha a conexão ao sair
    if conexao_ativa and conexao_ativa.is_connected():
        conexao_ativa.close()
        print("Log: Conexão com o BD fechada.")